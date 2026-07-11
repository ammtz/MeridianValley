# Meridian Valley

A persistent virtual world, drawn as a pixel-art town, that works like an
operating system for populations of AI agents. The world loop never stops;
agents are mortal processes inside it. Watching the town **is** the log.

## The mission, in three deliverables

1. **A world that persists** — every change is an event in an append-only
   log; any past moment can be replayed.
2. **An orchestrator** — one Worker process is the sole writer of world
   state and manages agent lifecycles: spawn, watch, kill.
3. **A human/AI comms channel** — one place to direct the work and hear
   the world report back.

## How this project is run

Start with [`DIRECTIVE.md`](DIRECTIVE.md) — the way of working for any
contributor, human or AI, zero context assumed. Then:

- [`BACKLOG.md`](BACKLOG.md) — the ordered work, as stories with points.
- [`DECISIONS.md`](DECISIONS.md) — standing decisions; consult before deciding.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — the technical laws of the world.

## Quickstart (current scaffold)

```bash
cp .env.example .env        # add your ANTHROPIC_API_KEY (gitignored)
pip install -r requirements.txt
set -a && source .env && set +a
uvicorn server.main:app --reload
# open http://localhost:8000
```

## Repository map

```
DIRECTIVE.md          how work gets done — read first
BACKLOG.md            the stories
DECISIONS.md          precedent; DOs / DON'Ts
ARCHITECTURE.md       invariants, stack, graduation triggers
server/envelopes.py   the event protocol (typed verbs + envelopes) — defined once
server/main.py        FastAPI + WebSocket bus; the Worker (sole state mutator)
server/brain.py       model orchestration (orchestrator + parallel workers)
server/worldlog.py    append-only event journal (to be superseded by story W1)
web/index.html        the render surface: emits gestures, draws envelopes
.claude/              session hooks so AI coding sessions land ready to run
```

## Status

The current code is the proven seed loop: a working envelope bus with a
single Worker and a browser render surface. The backlog evolves it into the
persistent world described above, one story at a time.
