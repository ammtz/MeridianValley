"""M1 proof — do Claude Code hooks fire the way Paperclip runs Claude?

Runs the real `claude` binary with the exact flags Paperclip's claude_local
adapter passes (paperclip-2 `packages/adapters/claude-local/src/server/
execute.ts:885`), against a fake Anthropic API on localhost, so it needs no
API key and spends nothing. Everything lives in a throwaway HOME.

Three heartbeats for one employee, the way Paperclip schedules them:
fresh session → `--resume` of that session → fresh session.

Proves, and exits non-zero if any fails:
  1. every hook fires under `--print --output-format stream-json` (FIRST-WORLD §11)
  2. the hook process inherits PAPERCLIP_AGENT_ID / _RUN_ID / _COMPANY_ID (AD-4)
     — and PAPERCLIP_API_KEY too, so M2's enrichment must exclude it by name (§8)
  3. `--resume` keeps the session id; a fresh run gets a new one, so the
     employee — not the session — is the identity (AD-5)

With `--pixel-agents <path to a built pixel-agents-2>` it also starts that
server in the same HOME (hooks installed by its own installer, Watch All on),
and reports how many office characters the three heartbeats produced.
M2's acceptance is `--expect-characters 1`.

Run from the repo root:

    python -m scripts.m1_hooks_probe
    python -m scripts.m1_hooks_probe --pixel-agents ../pixel-agents-2
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Exactly what Paperclip passes (execute.ts:885-886, permissions.ts:12), minus
# the per-run extras (--model, --add-dir, --append-system-prompt-file, ...).
PAPERCLIP_ARGS = ["--print", "--output-format", "stream-json", "--verbose",
                  "--setting-sources", "user", "--dangerously-skip-permissions"]
HOOK_EVENTS = ["SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse",
               "Stop", "SessionEnd"]
PAPERCLIP_ENV = {"PAPERCLIP_AGENT_ID": "agent-ada", "PAPERCLIP_COMPANY_ID": "co-1",
                 "PAPERCLIP_API_KEY": "probe-secret"}  # RUN_ID is set per heartbeat


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class FakeAnthropic(BaseHTTPRequestHandler):
    """Answers a prompt with one Bash tool call, then a tool result with 'done'."""

    def log_message(self, *_):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))) or b"{}")
        if not self.path.startswith("/v1/messages") or "count_tokens" in self.path:
            return self._json({"input_tokens": 1})
        # One tool call per heartbeat prompt, counted over the whole history so a
        # resumed session (which replays earlier turns) gets exactly one more.
        blocks = [c for m in body.get("messages", []) if m.get("role") == "user"
                  for c in (m["content"] if isinstance(m["content"], list)
                            else [{"type": "text", "text": m["content"]}])]
        prompts = sum(1 for c in blocks if c.get("type") == "text" and "heartbeat" in c.get("text", ""))
        results = sum(1 for c in blocks if c.get("type") == "tool_result")
        if results >= prompts or "Bash" not in [t.get("name") for t in body.get("tools", [])]:
            block, delta, stop = ({"type": "text", "text": ""},
                                  {"type": "text_delta", "text": "done"}, "end_turn")
        else:
            args = json.dumps({"command": "echo probe", "description": "probe"})
            block, delta, stop = ({"type": "tool_use", "id": f"toolu_{time.time_ns()}",
                                   "name": "Bash", "input": {}},
                                  {"type": "input_json_delta", "partial_json": args}, "tool_use")
        msg = {"id": "msg_probe", "type": "message", "role": "assistant", "content": [],
               "model": body.get("model"), "stop_reason": None, "stop_sequence": None,
               "usage": {"input_tokens": 1, "output_tokens": 1}}
        self.send_response(200)
        self.send_header("content-type", "text/event-stream")
        self.end_headers()
        for event, data in [
            ("message_start", {"type": "message_start", "message": msg}),
            ("content_block_start", {"type": "content_block_start", "index": 0, "content_block": block}),
            ("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": delta}),
            ("content_block_stop", {"type": "content_block_stop", "index": 0}),
            ("message_delta", {"type": "message_delta", "usage": {"output_tokens": 1},
                               "delta": {"stop_reason": stop, "stop_sequence": None}}),
            ("message_stop", {"type": "message_stop"}),
        ]:
            self.wfile.write(f"event: {event}\ndata: {json.dumps(data)}\n\n".encode())

    def _json(self, obj):
        raw = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


# The logging hook: one JSON line per event, with what the hook process can see.
HOOK_SRC = """import json, os, sys
p = json.load(sys.stdin)
env = {k: v for k, v in os.environ.items() if k.startswith("PAPERCLIP_")}
with open(sys.argv[1], "a") as f:
    f.write(json.dumps({"event": p.get("hook_event_name"), "session": p.get("session_id"),
                        "source": p.get("source"), "env": env}) + "\\n")
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--pixel-agents", type=Path, help="path to a built pixel-agents-2 checkout")
    ap.add_argument("--expect-characters", type=int, help="fail unless the office shows this many")
    ap.add_argument("--keep", action="store_true", help="keep the throwaway HOME for inspection")
    opts = ap.parse_args()

    claude = shutil.which("claude")
    if not claude:
        print("claude CLI not on PATH")
        return 2

    root = Path(tempfile.mkdtemp(prefix="m1probe-"))
    home, work = root / "home", root / "work"
    (home / ".claude").mkdir(parents=True)
    work.mkdir()
    hook_log, debug_log = root / "hooks.jsonl", root / "pixel-debug.log"
    (root / "hook.py").write_text(HOOK_SRC)
    cmd = f'"{sys.executable}" "{root / "hook.py"}" "{hook_log}"'
    (home / ".claude" / "settings.json").write_text(json.dumps({"hooks": {
        e: [{"matcher": "", "hooks": [{"type": "command", "command": cmd}]}] for e in HOOK_EVENTS}}))

    api = ThreadingHTTPServer(("127.0.0.1", free_port()), FakeAnthropic)
    threading.Thread(target=api.serve_forever, daemon=True).start()
    base_env = {"HOME": str(home), "PATH": os.environ["PATH"], "ANTHROPIC_API_KEY": "sk-probe",
                "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{api.server_port}",
                "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", "IS_SANDBOX": "1"}

    office = None
    try:
        if opts.pixel_agents:
            cli = opts.pixel_agents.resolve() / "dist" / "cli.js"
            if not cli.exists():
                print(f"{cli} missing — build pixel-agents-2 first (node esbuild.js)")
                return 2
            (home / ".pixel-agents").mkdir()
            (home / ".pixel-agents" / "config.json").write_text(json.dumps({
                "standalone": {"watchAllSessions": True, "hooksInfoShown": True},
                "hooksConsent": {"claude": "granted"}, "hooksEnabled": {"claude": True}}))
            office = subprocess.Popen(
                ["node", str(cli), "--port", str(free_port())], cwd=cli.parent.parent,
                env={**base_env, "PIXEL_AGENTS_DEBUG_LOG": str(debug_log)},
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for _ in range(60):  # wait for its own installer to add its hooks
                if "claude-hook.js" in (home / ".claude" / "settings.json").read_text():
                    break
                time.sleep(0.5)
            else:
                print("pixel-agents server never installed its hooks")
                return 2
            print(f"office   pixel-agents server up, hooks installed, Watch All on")

        def heartbeat(run_id: str, resume: str | None = None) -> str:
            args = [claude, *PAPERCLIP_ARGS, *(["--resume", resume] if resume else [])]
            out = subprocess.run(args, input="heartbeat", capture_output=True, text=True, cwd=work,
                                 timeout=60, env={**base_env, **PAPERCLIP_ENV, "PAPERCLIP_RUN_ID": run_id})
            init = next(json.loads(l) for l in out.stdout.splitlines()
                        if l.startswith("{") and json.loads(l).get("subtype") == "init")
            print(f"{run_id:<8} exit={out.returncode} session={init['session_id'][:8]}"
                  f"{' (resumed)' if resume else ''}")
            time.sleep(4 if office else 0)  # let the office's scanners tick
            return init["session_id"]

        s1 = heartbeat("run-1")
        s2 = heartbeat("run-2", resume=s1)
        s3 = heartbeat("run-3")
    finally:
        api.shutdown()
        if office:
            office.terminate()
            office.wait(timeout=10)

    hooks = [json.loads(l) for l in hook_log.read_text().splitlines()]
    failures = []

    print("\n── 1. hooks fire under Paperclip's print mode ──")
    for sid, label in ((s1, "run-1 fresh"), (s2, "run-2 resumed"), (s3, "run-3 fresh")):
        seen = [h["event"] for h in hooks if h["session"] == sid and h["env"].get("PAPERCLIP_RUN_ID") == label[:5]]
        missing = [e for e in HOOK_EVENTS if e not in seen]
        print(f"  {label:<14} {len(seen)} hooks{'' if not missing else '  MISSING ' + ', '.join(missing)}")
        failures += [f"{label}: {e} did not fire" for e in missing]

    print("\n── 2. the hook process sees Paperclip's identity (AD-4) ──")
    env = hooks[0]["env"]
    for key in ("PAPERCLIP_AGENT_ID", "PAPERCLIP_COMPANY_ID", "PAPERCLIP_RUN_ID"):
        print(f"  {key:<22} {'visible' if key in env else 'MISSING'}")
        if key not in env:
            failures.append(f"{key} not visible to the hook")
    print(f"  {'PAPERCLIP_API_KEY':<22} {'visible — M2 must exclude it by name' if 'PAPERCLIP_API_KEY' in env else 'not visible'}")

    print("\n── 3. identity: the session is not the employee (AD-5) ──")
    print(f"  --resume keeps the session id:  {s2 == s1}")
    print(f"  a fresh run gets a new one:     {s3 != s1}")
    print(f"  resumed SessionStart source:    {next((h['source'] for h in hooks if h['event'] == 'SessionStart' and h['session'] == s2 and h['env'].get('PAPERCLIP_RUN_ID') == 'run-2'), None)}")
    if s2 != s1:
        failures.append("--resume did not keep the session id")
    if s3 == s1:
        failures.append("a fresh run reused the session id")

    if opts.pixel_agents:
        log = debug_log.read_text()
        arrived = len(re.findall(r"HOOKSCRIPT POST-done .*status=200", log))
        characters = sorted({int(i) for i in re.findall(r"BCAST agentStatus id=(\d+)", log)})
        print("\n── 4. the office ──")
        print(f"  hook POSTs it acknowledged:    {arrived}")
        print(f"  characters for one employee:    {len(characters)}  (ids {characters}; M2 target: 1)")
        if opts.expect_characters is not None and len(characters) != opts.expect_characters:
            failures.append(f"office shows {len(characters)} characters, expected {opts.expect_characters}")

    if opts.keep:
        print(f"\nkept: {root}")
    else:
        shutil.rmtree(root, ignore_errors=True)

    if failures:
        print("\nM1 PROBE FAILED:\n  " + "\n  ".join(failures))
        return 1
    print("\nM1 PROBE PASSED — hooks fire under Paperclip's flags and carry its identity.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
