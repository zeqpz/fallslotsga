"""agenthub - a local task hub for Claude Code agents.

Any number of Claude Code sessions connect to one hub over MCP (Streamable HTTP,
JSON responses) at http://127.0.0.1:8799/mcp, submit tasks to named agents
(~/.claude/agents/*.md or <project>/.claude/agents/*.md), and read results back.

Each agent has its own FIFO queue; tasks run strictly in submit order per agent,
with a global cap on how many agents work at once. A task can also wait for an
earlier task (`after`). Work is done by the local `claude -p --agent <name>`
CLI, which uses the user's existing login.

Safety, by construction:
  * Python standard library only. No third-party code.
  * Binds 127.0.0.1 only; rejects non-local Host/Origin headers (DNS rebinding).
  * Makes no network calls itself. The only child process is the claude CLI.
  * Never asks for, reads, stores or forwards API keys/tokens. The child gets a
    copy of this process's environment minus variables that look like secrets.
  * cwd must sit under an allowlisted root; agent names are validated against
    the agent files on disk; permission mode is fixed in config, not per call.

Run:  python agenthub.py            (config: ~/.agenthub/config.json, optional)
Add to a session:  claude mcp add --transport http --scope user agenthub http://127.0.0.1:8799/mcp
"""
from __future__ import annotations

import glob
import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOME = Path.home()
HUB_DIR = HOME / ".agenthub"
HUB_DIR.mkdir(exist_ok=True)
DB_PATH = HUB_DIR / "hub.db"
LOG_DIR = HUB_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

DEFAULT_CONFIG = {
    "host": "127.0.0.1",
    "port": 8799,
    "max_parallel": 2,              # agents working at the same time (each agent is FIFO)
    "task_timeout_s": 3600,
    "max_turns": 80,
    "permission_mode": "auto",      # classifier-checked actions; fixed here, callers cannot change it
    "allowed_roots": [str(HOME / "Documents"), str(HOME / "projects")],
    "claude_exe": "",               # empty = auto-detect
}
SECRET_ENV = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|COOKIE|SESSION)", re.I)
# The child claude must keep its own auth/config; only strip things that look like secrets
# and are not needed by the CLI. CLAUDE_* / ANTHROPIC_* are dropped too: the CLI uses its
# stored login, so a stray API key in the hub's shell can never be picked up and billed.
KEEP_ENV = {"PATH", "PATHEXT", "SYSTEMROOT", "SYSTEMDRIVE", "COMSPEC", "TEMP", "TMP", "USERPROFILE",
            "HOMEDRIVE", "HOMEPATH", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA", "PROGRAMFILES",
            "PROGRAMFILES(X86)", "WINDIR", "USERNAME", "COMPUTERNAME", "OS", "NUMBER_OF_PROCESSORS",
            "PROCESSOR_ARCHITECTURE", "LANG", "HOME", "PYTHONIOENCODING"}

AGENT_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    p = HUB_DIR / "config.json"
    if p.exists():
        cfg.update(json.loads(p.read_text(encoding="utf-8")))
    if cfg["host"] not in ("127.0.0.1", "localhost", "::1"):
        raise SystemExit("agenthub only binds to loopback")
    return cfg


CFG = load_config()


def find_claude() -> str:
    if CFG.get("claude_exe"):
        return CFG["claude_exe"]
    cands = glob.glob(os.path.join(os.environ.get("APPDATA", ""), "Claude", "claude-code", "*", "*", "claude.exe"))
    # The desktop app is an MSIX package: outside the app its AppData is virtualized here.
    cands += glob.glob(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Packages", "Claude_*", "LocalCache",
                                    "Roaming", "Claude", "claude-code", "*", "*", "claude.exe"))
    # newer app builds keep it under %LOCALAPPDATA%/Claude-Data/claude_<id>/claude-code/<ver>/<hash>/
    cands += glob.glob(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Claude-Data", "claude_*", "claude-code", "*", "*", "claude.exe"))
    cands += glob.glob(str(HOME / ".local" / "bin" / "claude*"))

    def ver(p):
        m = re.search(r"claude-code[\\/](\d+)\.(\d+)\.(\d+)", p)
        return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)

    cands.sort(key=ver, reverse=True)
    if cands:
        return cands[0]
    raise SystemExit("claude CLI not found; set claude_exe in ~/.agenthub/config.json")


def child_env() -> dict:
    env = {}
    for k, v in os.environ.items():
        ku = k.upper()
        if ku in KEEP_ENV or (not SECRET_ENV.search(ku) and not ku.startswith(("ANTHROPIC_", "CLAUDE_", "AWS_", "OPENAI", "GH_", "GITHUB_"))):
            env[k] = v
    env["PYTHONIOENCODING"] = "utf-8"
    return env


# ---------------------------------------------------------------- storage
_db_lock = threading.Lock()


def db() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c


DB = db()
DB.executescript("""
CREATE TABLE IF NOT EXISTS tasks(
  id TEXT PRIMARY KEY, seq INTEGER, agent TEXT, title TEXT, prompt TEXT, cwd TEXT,
  status TEXT, after TEXT, submitter TEXT, created REAL, started REAL, finished REAL,
  result TEXT, session_id TEXT, cost_usd REAL, exit_code INTEGER, error TEXT);
CREATE INDEX IF NOT EXISTS t_agent ON tasks(agent, status, seq);
""")
with _db_lock:
    DB.execute("UPDATE tasks SET status='failed', error='hub restarted while running', finished=? WHERE status='running'", (time.time(),))


def q(sql, args=(), one=False):
    with _db_lock:
        cur = DB.execute(sql, args)
        rows = cur.fetchall()
    rows = [dict(r) for r in rows]
    return (rows[0] if rows else None) if one else rows


# ---------------------------------------------------------------- agents
def agent_dirs(cwd: str | None):
    dirs = [HOME / ".claude" / "agents"]
    if cwd:
        p = Path(cwd).resolve()
        for d in [p, *p.parents]:
            if (d / ".claude" / "agents").is_dir():
                dirs.insert(0, d / ".claude" / "agents")
                break
    return dirs


def list_agents(cwd: str | None = None) -> list[dict]:
    seen = {}
    for d in agent_dirs(cwd):
        for f in sorted(d.glob("*.md")):
            text = f.read_text(encoding="utf-8", errors="replace")
            m = re.match(r"---\s*\n(.*?)\n---", text, re.S)
            meta = {}
            if m:
                for line in m.group(1).splitlines():
                    if ":" in line and not line.startswith(" "):
                        k, v = line.split(":", 1)
                        meta[k.strip()] = v.strip().strip('"')
            name = meta.get("name", f.stem)
            if name not in seen:
                seen[name] = {"name": name, "description": meta.get("description", "")[:300], "file": str(f)}
    return list(seen.values())


def check_cwd(cwd: str) -> str:
    p = Path(cwd).resolve()
    if not p.is_dir():
        raise ValueError(f"cwd does not exist: {cwd}")
    for root in CFG["allowed_roots"]:
        r = Path(root).resolve()
        if p == r or r in p.parents:
            return str(p)
    raise ValueError(f"cwd {p} is outside allowed_roots {CFG['allowed_roots']}")


# ---------------------------------------------------------------- dispatcher
_wake = threading.Event()
_running: dict[str, subprocess.Popen] = {}   # task id -> process
_busy_agents: set[str] = set()
_state_lock = threading.Lock()


def next_runnable():
    """Head of each agent's FIFO; runnable if its `after` dependency is finished."""
    heads = q("""SELECT * FROM tasks t WHERE status='queued' AND seq=(SELECT MIN(seq) FROM tasks u
                 WHERE u.agent=t.agent AND u.status IN ('queued')) ORDER BY seq""")
    for t in heads:
        if t["agent"] in _busy_agents:
            continue
        if t["after"]:
            dep = q("SELECT status FROM tasks WHERE id=?", (t["after"],), one=True)
            if dep and dep["status"] in ("queued", "running"):
                continue
            if dep and dep["status"] in ("failed", "cancelled"):
                q("UPDATE tasks SET status='cancelled', error=?, finished=? WHERE id=?",
                  (f"dependency {t['after']} {dep['status']}", time.time(), t["id"]))
                continue
        return t
    return None


def run_task(t: dict):
    exe = find_claude()
    argv = [exe, "-p", "--agent", t["agent"], "--output-format", "json",
            "--max-turns", str(CFG["max_turns"]), "--permission-mode", CFG["permission_mode"],
            "--no-session-persistence"]
    log = LOG_DIR / f"{t['id']}.log"
    q("UPDATE tasks SET status='running', started=? WHERE id=?", (time.time(), t["id"]))
    try:
        with open(log, "w", encoding="utf-8") as errf:
            p = subprocess.Popen(argv, cwd=t["cwd"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=errf, env=child_env(), text=True, encoding="utf-8",
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            with _state_lock:
                _running[t["id"]] = p
            try:
                out, _ = p.communicate(t["prompt"], timeout=CFG["task_timeout_s"])
            except subprocess.TimeoutExpired:
                p.kill()
                out, _ = p.communicate()
                raise TimeoutError(f"timed out after {CFG['task_timeout_s']}s")
        cur = q("SELECT status FROM tasks WHERE id=?", (t["id"],), one=True)
        if cur and cur["status"] == "cancelled":
            return
        result, sid, cost, err = out, None, None, None
        try:
            j = json.loads(out)
            result = j.get("result", out)
            sid, cost = j.get("session_id"), j.get("total_cost_usd")
            if j.get("is_error"):
                err = str(result or j.get("subtype") or "error")[:2000]
        except (json.JSONDecodeError, AttributeError):
            pass
        ok = p.returncode == 0 and not err
        if not ok and not err:
            err = log.read_text(encoding="utf-8", errors="replace")[-2000:] or f"exit {p.returncode}"
        q("""UPDATE tasks SET status=?, finished=?, result=?, session_id=?, cost_usd=?, exit_code=?, error=?
             WHERE id=?""", ("done" if ok else "failed", time.time(), result, sid, cost, p.returncode, err, t["id"]))
    except Exception as e:  # noqa: BLE001
        q("UPDATE tasks SET status='failed', finished=?, error=? WHERE id=?", (time.time(), str(e)[:2000], t["id"]))
    finally:
        with _state_lock:
            _running.pop(t["id"], None)
            _busy_agents.discard(t["agent"])
        _wake.set()


def dispatcher():
    while True:
        _wake.wait(timeout=2)
        _wake.clear()
        while True:
            with _state_lock:
                if len(_busy_agents) >= CFG["max_parallel"]:
                    break
                t = next_runnable()
                if not t:
                    break
                _busy_agents.add(t["agent"])
            threading.Thread(target=run_task, args=(t,), daemon=True).start()


# ---------------------------------------------------------------- MCP tools
def public(t: dict, full=True) -> dict:
    d = {k: t[k] for k in ("id", "agent", "title", "status", "after", "submitter", "cwd", "error", "cost_usd")}
    for k in ("created", "started", "finished"):
        d[k] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t[k])) if t[k] else None
    pos = None
    if t["status"] == "queued":
        pos = q("SELECT COUNT(*) n FROM tasks WHERE agent=? AND status='queued' AND seq<?", (t["agent"], t["seq"]), one=True)["n"]
    d["queue_position"] = pos
    if full:
        d["result"] = t["result"]
    return d


def tool_submit_task(agent: str, prompt: str, cwd: str, title: str = "", after: str = "", submitter: str = ""):
    if not AGENT_NAME.match(agent or ""):
        raise ValueError("bad agent name")
    cwd = check_cwd(cwd)
    if agent not in {a["name"] for a in list_agents(cwd)}:
        raise ValueError(f"unknown agent '{agent}'. Call list_agents.")
    if after and not q("SELECT 1 FROM tasks WHERE id=?", (after,), one=True):
        raise ValueError(f"unknown 'after' task {after}")
    if not prompt.strip():
        raise ValueError("empty prompt")
    tid = uuid.uuid4().hex[:10]
    with _db_lock:
        seq = (DB.execute("SELECT COALESCE(MAX(seq),0)+1 FROM tasks").fetchone()[0])
        DB.execute("""INSERT INTO tasks(id,seq,agent,title,prompt,cwd,status,after,submitter,created)
                      VALUES(?,?,?,?,?,?,'queued',?,?,?)""",
                   (tid, seq, agent, (title or prompt.splitlines()[0])[:120], prompt, cwd, after or None,
                    submitter[:80] or None, time.time()))
    _wake.set()
    return public(q("SELECT * FROM tasks WHERE id=?", (tid,), one=True), full=False)


def tool_get_task(id: str):
    t = q("SELECT * FROM tasks WHERE id=?", (id,), one=True)
    if not t:
        raise ValueError("no such task")
    return public(t)


def tool_wait_task(id: str, timeout_s: int = 50):
    end = time.time() + max(1, min(int(timeout_s), 55))
    while time.time() < end:
        t = q("SELECT * FROM tasks WHERE id=?", (id,), one=True)
        if not t:
            raise ValueError("no such task")
        if t["status"] in ("done", "failed", "cancelled"):
            return public(t)
        time.sleep(1)
    return public(q("SELECT * FROM tasks WHERE id=?", (id,), one=True))


def tool_list_tasks(agent: str = "", status: str = "", limit: int = 30):
    sql, args = "SELECT * FROM tasks WHERE 1=1", []
    if agent:
        sql += " AND agent=?"; args.append(agent)
    if status:
        sql += " AND status=?"; args.append(status)
    sql += " ORDER BY seq DESC LIMIT ?"; args.append(max(1, min(int(limit), 200)))
    return [public(t, full=False) for t in q(sql, args)]


def tool_cancel_task(id: str):
    t = q("SELECT * FROM tasks WHERE id=?", (id,), one=True)
    if not t:
        raise ValueError("no such task")
    if t["status"] not in ("queued", "running"):
        return public(t, full=False)
    q("UPDATE tasks SET status='cancelled', finished=? WHERE id=?", (time.time(), id))
    with _state_lock:
        p = _running.get(id)
    if p:
        p.kill()
    return public(q("SELECT * FROM tasks WHERE id=?", (id,), one=True), full=False)


def tool_list_agents(cwd: str = ""):
    return list_agents(cwd or None)


S = {"type": "string"}
TOOLS = {
    "list_agents": (tool_list_agents, "List the agents tasks can be sent to (user + project .claude/agents).",
                    {"cwd": {**S, "description": "project folder, to include its .claude/agents"}}, []),
    "submit_task": (tool_submit_task, "Queue a task for an agent. Tasks for the same agent run one at a time in submit order. "
                    "Returns the task id; poll with wait_task/get_task.",
                    {"agent": S, "prompt": {**S, "description": "complete, self-contained brief"},
                     "cwd": {**S, "description": "absolute project folder the agent works in"},
                     "title": S, "after": {**S, "description": "optional task id that must finish first"},
                     "submitter": {**S, "description": "who is asking (session name), for the log"}},
                    ["agent", "prompt", "cwd"]),
    "get_task": (tool_get_task, "Status and result of a task.", {"id": S}, ["id"]),
    "wait_task": (tool_wait_task, "Block up to timeout_s (max 55) until the task finishes; returns its status/result.",
                  {"id": S, "timeout_s": {"type": "integer"}}, ["id"]),
    "list_tasks": (tool_list_tasks, "Recent tasks, newest first, optionally filtered.",
                   {"agent": S, "status": {**S, "enum": ["queued", "running", "done", "failed", "cancelled"]},
                    "limit": {"type": "integer"}}, []),
    "cancel_task": (tool_cancel_task, "Cancel a queued task or kill a running one.", {"id": S}, ["id"]),
}
PROTOCOL = "2025-06-18"


def handle_rpc(msg: dict):
    mid, method, params = msg.get("id"), msg.get("method"), msg.get("params") or {}
    if mid is None:      # notification
        return None
    try:
        if method == "initialize":
            res = {"protocolVersion": params.get("protocolVersion", PROTOCOL),
                   "capabilities": {"tools": {"listChanged": False}},
                   "serverInfo": {"name": "agenthub", "version": "1.0.0"},
                   "instructions": "Local task hub. list_agents -> submit_task -> wait_task. "
                                   "Briefs must be self-contained; never include secrets."}
        elif method == "ping":
            res = {}
        elif method == "tools/list":
            res = {"tools": [{"name": n, "description": d,
                              "inputSchema": {"type": "object", "properties": p, "required": r}}
                             for n, (_, d, p, r) in TOOLS.items()]}
        elif method == "tools/call":
            name = params.get("name")
            if name not in TOOLS:
                return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": f"unknown tool {name}"}}
            fn, _, props, _ = TOOLS[name]
            args = {k: v for k, v in (params.get("arguments") or {}).items() if k in props}
            try:
                out = fn(**args)
                res = {"content": [{"type": "text", "text": json.dumps(out, indent=1, ensure_ascii=False)}]}
            except Exception as e:  # noqa: BLE001
                res = {"content": [{"type": "text", "text": f"error: {e}"}], "isError": True}
        else:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"method not found: {method}"}}
        return {"jsonrpc": "2.0", "id": mid, "result": res}
    except Exception as e:  # noqa: BLE001
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32603, "message": str(e)}}


LOCAL_HOSTS = {"127.0.0.1", "localhost", "[::1]"}


class Handler(BaseHTTPRequestHandler):
    server_version = "agenthub"

    def log_message(self, *a):
        pass

    def _local_ok(self) -> bool:
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
        origin = self.headers.get("Origin")
        if host not in LOCAL_HOSTS:
            return False
        if origin:
            o = re.sub(r"^https?://", "", origin).rsplit(":", 1)[0]
            if o not in LOCAL_HOSTS:
                return False
        return True

    def _send(self, code, body=b"", ctype="application/json"):
        self.send_response(code)
        if body:
            self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_POST(self):
        if not self._local_ok():
            return self._send(403, b'{"error":"forbidden"}')
        if self.path.split("?")[0] != "/mcp":
            return self._send(404)
        n = int(self.headers.get("Content-Length") or 0)
        if n > 2_000_000:
            return self._send(413)
        try:
            msg = json.loads(self.rfile.read(n) or b"null")
        except json.JSONDecodeError:
            return self._send(400, b'{"jsonrpc":"2.0","id":null,"error":{"code":-32700,"message":"parse error"}}')
        if isinstance(msg, list):
            out = [r for r in (handle_rpc(m) for m in msg) if r]
        else:
            out = handle_rpc(msg)
        if not out:
            return self._send(202)
        self._send(200, json.dumps(out).encode())

    def do_GET(self):
        if not self._local_ok():
            return self._send(403)
        if self.path.split("?")[0] == "/mcp":
            return self._send(405)          # no server-initiated stream
        if self.path.split("?")[0] == "/":
            return self._send(200, status_page().encode(), "text/html; charset=utf-8")
        self._send(404)

    def do_DELETE(self):
        self._send(405)


def status_page() -> str:
    import html
    rows = q("SELECT * FROM tasks ORDER BY seq DESC LIMIT 100")
    tr = "".join(
        f"<tr class={t['status']}><td>{t['id']}</td><td>{html.escape(t['agent'])}</td><td>{t['status']}</td>"
        f"<td>{html.escape(t['title'] or '')}</td><td>{html.escape(t['submitter'] or '')}</td>"
        f"<td>{time.strftime('%m-%d %H:%M', time.localtime(t['created']))}</td></tr>" for t in rows)
    return ("<!doctype html><meta charset=utf-8><meta http-equiv=refresh content=5><title>agenthub</title>"
            "<style>body{font:13px system-ui;margin:16px;background:#fff;color:#111}td,th{padding:4px 8px;"
            "border-bottom:1px solid #ddd;text-align:left}.running{background:#fff6d5}.failed{background:#fde2e2}"
            ".done{color:#555}@media(prefers-color-scheme:dark){body{background:#151515;color:#eee}"
            ".running{background:#3a3210}.failed{background:#3a1515}}</style>"
            f"<h3>agenthub - {len(list_agents())} agents, {len(_busy_agents)} working</h3>"
            "<table><tr><th>id<th>agent<th>status<th>title<th>from<th>created</tr>" + tr + "</table>")


def main():
    find_claude()
    threading.Thread(target=dispatcher, daemon=True).start()
    srv = ThreadingHTTPServer((CFG["host"], CFG["port"]), Handler)
    print(f"agenthub on http://{CFG['host']}:{CFG['port']}/mcp  (db {DB_PATH})", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    sys.exit(main())
