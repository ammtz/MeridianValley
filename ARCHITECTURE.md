# ARCHITECTURE

The technical laws of the world. These constrain every story in `BACKLOG.md`.

## Invariants (non-negotiable)

1. **Append-only event log.** Every change to the world is an event written to the log. The log is never edited or truncated. Replaying the log from zero must reproduce the exact world state.
2. **One writer.** A single Worker process is the only thing that mutates world state. Agents and humans *request* changes by emitting events; the Worker applies them one at a time, in order.
3. **Typed protocol.** All events use a frozen vocabulary of typed verbs with enforced envelopes (v1.1). Invalid events are rejected at the door, cheaply, before they can touch state.
4. **Mortal agents, immortal world.** Agents are separate processes the Worker can spawn and kill. Killing any agent must never affect the world loop or the render.
5. **Fixed heartbeat.** The world ticks at a fixed cadence. Rhythm makes progress observable and results comparable.
6. **Render is a pure function of state.** The renderer reads state and draws it. It never writes, never decides.

## Stack

| Layer | Choice | Why |
|---|---|---|
| Event log | SQLite table `events(id, verb, envelope, ts)` | Append-only, ordered by rowid, durable, replay is one SELECT, zero services to operate |
| World state | SQLite, same file, separate tables | Single source of truth; single-writer database matches the one-writer invariant physically |
| Worker | One Python process, single-threaded loop | One event at a time — the invariant enforced by construction |
| Render | PixiJS in the browser; WebSocket via FastAPI | Snapshot on connect, live deltas after; proven pattern for tile worlds |
| Agents | Plain OS subprocesses | Mortality = kill the PID; simplest possible lifecycle |
| Models | Hosted LLM API | No local GPU requirement for the MVP |
| Maps & art | Tiled editor + purchased 16×16 tilesets | Maps as JSON the renderer loads; art is bought, not drawn |

*Implemented so far (Epic 1): the event log, state tables, and the Worker live in `server/db.py` and `server/worker.py`; the verb protocol is carded in `PROTOCOL.md`. Render and agents are still ahead.*

## Graduation triggers — upgrade only when these fire

| From → To | Trigger |
|---|---|
| SQLite event log → dedicated stream (e.g., Redis Streams) | Sustained load beyond roughly hundreds of events/second, or multiple machines writing |
| Subprocesses → containers | An agent executes code the team did not write |
| SQLite state → client-server database (e.g., Postgres) | Something other than the Worker legitimately needs direct database access |
| Hosted API → local model routing | Model spend becomes material relative to the project's budget |

## Binding loop

```
human/agent gesture → emit event → event log → Worker validates & applies → state → render
```

Everything in the system is one instance of this loop. If a proposed design doesn't fit it, the design is wrong.
