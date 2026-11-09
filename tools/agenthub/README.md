# agenthub

A local task hub so any Claude Code session on this machine can hand work to named specialist agents. Each agent has its own queue; its tasks run one at a time in the order they were submitted.

```
session A ─┐                         ┌─ slot-frontend-perf   (FIFO)
session B ─┼─ MCP http://127.0.0.1:8799/mcp ─ agenthub ─┼─ slot-animator        (FIFO)
hubctl.py ─┘        (SQLite ~/.agenthub/hub.db)          └─ ... up to max_parallel agents at once
                                                             each task = `claude -p --agent <name>` in its cwd
```

## Why it is safe to run
- **Python standard library only.** No third-party packages and nothing to auto-update.
- **Loopback only.** Binds 127.0.0.1. Requests with a non-local `Host` or `Origin` get 403, which blocks DNS-rebinding from web pages.
- **Makes no network calls.** The only child process is the official `claude` CLI.
- **Never handles secrets.** Workers use the CLI's own login (`claude auth login`, once). The hub strips secret-looking environment variables (`*KEY*`, `*TOKEN*`, `*SECRET*`, `ANTHROPIC_*`, `CLAUDE_*`, `GH_*`, `AWS_*`...) from workers.
- **Callers can't widen what workers do.** The permission mode is fixed in config, `cwd` must be under `allowed_roots`, and agent names must match agent files on disk.
- **Agents carry their own ground rules.** Every agent in `~/.claude/agents/` tells it to:
  - never ask for or forward secrets;
  - make no outbound calls beyond public docs;
  - not commit, push or publish unless told.

Run `Grep "urllib|requests|socket|https?://" tools/agenthub` at any time to re-audit the code.

## Run
```
tools\agenthub\start_hub.cmd
```
Status page: http://127.0.0.1:8799/ (refreshes every 5 s). Logs: `~/.agenthub/logs/<task>.log`.

Register it once for all sessions (already done):
```
claude mcp add --transport http --scope user agenthub http://127.0.0.1:8799/mcp
```

## Use from a session
MCP tools: `list_agents`, `submit_task(agent, prompt, cwd, title?, after?, submitter?)`, `wait_task(id)`, `get_task(id)`, `list_tasks`, `cancel_task`. Use `after` to chain an ordered pipeline; if the dependency fails or is cancelled, the dependent task is cancelled too.

CLI:
```
python tools\agenthub\hubctl.py agents
python tools\agenthub\hubctl.py submit slot-frontend-perf C:\Users\CooperHinkel\Documents\fallslotsga "Profile the spin start ..."
python tools\agenthub\hubctl.py wait <id>
```

## Config (`~/.agenthub/config.json`, all optional)
```json
{ "max_parallel": 2, "permission_mode": "auto", "task_timeout_s": 3600, "max_turns": 80,
  "allowed_roots": ["C:\\Users\\CooperHinkel\\Documents", "C:\\Users\\CooperHinkel\\projects"] }
```
Modes:
- `auto` (default): Claude Code's safety classifier checks every action, so workers can run shell commands while risky ones are blocked.
- `acceptEdits`: edits files only; shell commands that need approval are denied.
- `bypassPermissions`: no checks at all. Not recommended.

## Agents (in `~/.claude/agents/`)
- `slot-frontend-perf`: profiling and lag fixes with measured A/B results
- `slot-animator`: Spine, rigs, GSAP, FX and the review quality bar
- `slot-asset-optimizer`: atlases, KTX2/WebP, audio, bundle size
- `stake-rgs-engineer`: wire format, bets, resume, replay, social mode
- `stake-math-engineer`: math-sdk, optimiser, compliance
- `stake-approval-reviewer`: read-only pre-submission audit
- `slot-frontend-researcher`: read-only, sourced answers

Their knowledge lives in the skills in `~/.claude/skills/`: `slot-frontend-performance`, `slot-animation-pipeline`, `slot-frontend-stack`, `slot-tools-and-resources`, `stake-rgs-integration`, `stake-math-workflow`, `stake-approval-checklist`, `agenthub`. The research behind them is in `research/`.
