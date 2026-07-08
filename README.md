# OVERWORLD — The Seed (real backend)

The language is the physical world. Every WebSocket message is an envelope;
the verb set in `server/envelopes.py` defines what can exist.

Binding loop, now spanning machines:
  gesture (browser) → emit → WebSocket bus → Python worker → state → envelopes → render

The Python worker (`server/main.py`) is the sole state mutator. The browser
holds no truth — it renders envelopes. The frontend speaks the exact same
envelope language the artifact version spoke: the swap-point, honored.

## Run (local — where you watch the world render)
    cp .env.example .env            # then put your real key in .env (gitignored)
    pip install -r requirements.txt
    set -a && source .env && set +a # load ANTHROPIC_API_KEY into the shell
    uvicorn server.main:app --reload
    # open http://localhost:8000

The server boots and serves the glass without a key; the seed loop
(interview → minis → ship) needs `ANTHROPIC_API_KEY` because `server/brain.py`
constructs the Anthropic client lazily on first brain call.

## Working on it (hybrid)
The live loop is a WebSocket world you watch in a browser, so **run it locally**;
use **Claude Code (web or CLI)** for edits, commits, and reasoning about the code.
GitHub `main` is the single source of truth.

- **Branches** — `main` is the proven trunk. Do each move on a feature branch
  (one branch ≈ one new word / proven loop), merge to `main` once it works
  end-to-end. Honors the n=1 discipline: prove the loop before scaling.
- **The key** — never commit it. Locally it lives in `.env` (see `.env.example`).
  For web sessions, set `ANTHROPIC_API_KEY` once at the *environment* level so
  every session inherits it: https://code.claude.com/docs/en/claude-code-on-the-web
- **Fresh web containers** — `.claude/hooks/session-start.sh` (a SessionStart
  hook) auto-installs requirements and verifies the toolchain, so a new session
  lands ready to run. Active once merged to the default branch.

## Layout
    server/envelopes.py   the language — verbs, schema, validation (defined once)
    server/brain.py       Sonnet orchestrator + parallel Haiku minis, real key server-side
    server/main.py        FastAPI + WebSocket bus; Room = worker, sole mutator
    web/index.html        dumb glass: emits gestures, renders envelopes

## What's live
- interview: orchestrator asks up to 2 real clarifying questions before splitting
- decompose → parallel minis, each finding streams back as its own envelope (stations update live)
- synth → ship, then persistent in-character chat with full context
- telemetry envelopes: calls / tokens / cost in the HUD
- raw envelope ticker bottom-left — the language, visible

NEXT MOVE: chat re-tasks a specialist live (route a chat message to a Haiku
mini, its station updates) — bidirectional control, in miniature.
