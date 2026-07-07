# OVERWORLD — MERIDIAN VALLEY (ctx) — 2026-07-07

## Founding principle (inviolable)
The language IS the physical world. Message vocabulary = world physics.
Rendering and behavior derive from the language, never the reverse.
Every feature is either a new word or it doesn't exist.

## Invariants
- Binding loop (ONLY path): gesture → emit → bus (WebSocket) → worker → state → render
- Python worker (server/main.py Room) is the SOLE state mutator; browser holds no truth
- Envelope schema defined ONCE in server/envelopes.py; bus rejects unknown verbs
- Verb lexicon v0: propose, assign, develop, boost, debug, review, ship, levelup, sys
- Moods derive from telemetry only, never set cosmetically
- Transport is a swap-point: frontend must never know what's behind the socket
- Emergent geography: layout renders live dependency state, never hardcoded as truth
- Three-second legibility: world state readable at a glance
- n=1 before scaling; no authoring-layer creep before the loop is proven

## Layout
- server/envelopes.py — the language (verbs, schema, validation)
- server/brain.py — Sonnet orchestrator + parallel Haiku minis (key server-side)
- server/main.py — FastAPI + WS bus; Room = worker
- web/index.html — dumb glass: emits gestures, renders envelopes

## Run
export ANTHROPIC_API_KEY=... && pip install -r requirements.txt
uvicorn server.main:app --reload  →  http://localhost:8000

## State
Seed loop live end-to-end: interview (≤2 real clarifying Qs) → decompose →
parallel minis (findings stream as individual envelopes) → synth → ship →
persistent in-character chat. Telemetry (calls/tokens/cost) rides sys envelopes.

## SUPERSEDED
- Artifact/sandbox builds (The_Seed_DEMO.html, dc-runtime bundle) — retired.
  This repo is the single source of truth.

## NEXT MOVE
Chat re-tasks a specialist live: route a chat message to run_worker(i) with
new instructions; station updates via the existing develop envelope path.
First proof of world-as-control-surface.
