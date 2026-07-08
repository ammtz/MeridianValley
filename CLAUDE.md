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
parallel minis → synth → ship → persistent in-character chat.
MINIS HAVE HANDS: run_worker (the swap-point) drives claude-agent-sdk sessions
with Read/Write/Edit tools in per-session workspaces (data/workspaces/<sid>);
findings ship with clickable artifact files. Voice-only fallback if SDK/CLI
absent. WORLD LOG: every envelope (both directions) appends to
data/world_log.jsonl — labeled episodes (verb, from→to, story, phase, points).

## Learning thesis (three loops, one dataset)
Closed language → every act is labeled data. Fast: delegation policy is a
contextual bandit over the envelope log. Medium: verb process trees are
A/B-able (same reward currency). Slow: stable verbs become LoRA SFT+DPO
targets. review is where truth enters the world — reward, not bureaucracy.
Verb semantics changes are constitutional amendments: new word, never a
silent edit.

## SUPERSEDED
- Artifact/sandbox builds (The_Seed_DEMO.html, dc-runtime bundle) — retired.
  This repo is the single source of truth.

## NEXT MOVE
Make review real: after ship, user verdict on each artifact (keep/redo) as
review envelopes with points — the reward channel the three learning loops
need. Then: chat re-tasks a specialist live (world-as-control-surface).
