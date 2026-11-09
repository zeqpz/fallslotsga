"""hubctl - tiny command-line client for agenthub (stdlib only, talks to 127.0.0.1 only).

  python hubctl.py agents
  python hubctl.py submit <agent> <cwd> "<prompt>" [--after ID] [--title T]
  python hubctl.py wait <id>
  python hubctl.py get <id>
  python hubctl.py list [agent] [status]
  python hubctl.py cancel <id>
"""
import json
import sys
import urllib.request

URL = "http://127.0.0.1:8799/mcp"
_id = 0


def rpc(method, params=None):
    global _id
    _id += 1
    body = json.dumps({"jsonrpc": "2.0", "id": _id, "method": method, "params": params or {}}).encode()
    req = urllib.request.Request(URL, body, {"Content-Type": "application/json",
                                             "Accept": "application/json, text/event-stream"})
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=70) as r:
        out = json.loads(r.read())
    if "error" in out:
        raise SystemExit(out["error"])
    return out["result"]


def call(tool, **args):
    res = rpc("tools/call", {"name": tool, "arguments": args})
    text = res["content"][0]["text"]
    if res.get("isError"):
        raise SystemExit(text)
    return json.loads(text)


def main(a):
    rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "hubctl", "version": "1"}})
    cmd = a[0] if a else "list"
    if cmd == "agents":
        out = call("list_agents", cwd=a[1] if len(a) > 1 else "")
    elif cmd == "submit":
        kw = {}
        rest = a[4:]
        for i in range(0, len(rest) - 1, 2):
            kw[rest[i].lstrip("-")] = rest[i + 1]
        out = call("submit_task", agent=a[1], cwd=a[2], prompt=a[3], submitter="hubctl", **kw)
    elif cmd == "wait":
        while True:
            out = call("wait_task", id=a[1], timeout_s=55)
            if out["status"] not in ("queued", "running"):
                break
    elif cmd == "get":
        out = call("get_task", id=a[1])
    elif cmd == "cancel":
        out = call("cancel_task", id=a[1])
    else:
        out = call("list_tasks", agent=a[1] if len(a) > 1 else "", status=a[2] if len(a) > 2 else "")
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
