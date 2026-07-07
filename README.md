# OVERWORLD — The Seed (real backend)

The language is the physical world. Every WebSocket message is an envelope;
the verb set in `server/envelopes.py` defines what can exist.

Binding loop, now spanning machines:
  gesture (browser) → emit → WebSocket bus → Python worker → state → envelopes → render

The Python worker (`server/main.py`) is the sole state mutator. The browser
holds no truth — it renders envelopes. The frontend speaks the exact same
envelope language the artifact version spoke: the swap-point, honored.

## Run
    export ANTHROPIC_API_KEY=sk-ant-...
    pip install -r requirements.txt
    uvicorn server.main:app --reload
    # open http://localhost:8000

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
