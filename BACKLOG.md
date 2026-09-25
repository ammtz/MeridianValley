# BACKLOG

Ordered product backlog. Topmost unblocked story wins. See `DIRECTIVE.md` for how to work it.

## Now
**Epic 0 — First World** (DECISIONS #10, spec `docs/FIRST-WORLD.md`) supersedes Epics 2–3 until it works. Topmost unblocked story: **M1**.

| ID | Story | Owner | Definition of Done |
|---|---|---|---|
| M0 | Fork Paperclip + Pixel Agents | H | ✅ `ammtz/paperclip-2`, `ammtz/pixel-agents-2` |
| M1 | Zero-code smoke run | B (PC) | A Paperclip agent's run animates in the office; open facts on hooks settled |
| M2 | Identity: hook enrichment + session alias | B | One character per employee across heartbeats |
| M3 | `PaperclipSource`: org, run state, approval bubbles | B | Keyless agent spawns labelled, types, bubbles, with hooks off |
| M4 | Approve from the office | B | Bubble click approves; Paperclip activity log records it |

*Previous "Now" (Epic 2 · V1 next) is paused, not deleted.*

*Also in review, from before Epic 0:* W6 (Epic 1.6) delivered and in review — the door now validates payloads and the Worker quarantines what it cannot apply. W5 (Epic 1.5) delivered and in review — the live bus now persists to the single event log and the Worker consumes it on a heartbeat, closing the two-sources-of-truth gap.

## Epic 1 — The World Persists — ✅ shipped (PR #2, 2026-07-13)
*Delivered on protocol amendment v1.1 (`spawn`/`move`/`kill`, DECISIONS #8). Proofs: `python -m scripts.w3_apply_proof` · `python -m scripts.w4_replay_proof`.*
| ID | Story | Pts | Owner | Definition of Done | Done |
|---|---|---|---|---|---|
| W1 | Database schema: `events` log + minimal state tables (`agents`, `positions`, `objects`) | 2 | B | Schema file runs clean and creates the database | ✅ |
| W2 | Event protocol reference card: every verb, its envelope, one example each, on one page | 2 | B | A reader with no context can write a valid event by hand | ✅ |
| W3 | Worker v0: read next event → validate → apply to state → repeat; idempotent | 3 | B | Injected test events mutate state correctly | ✅ |
| W4 | Replay proof: wipe state, re-run the full log, reach identical final state | 2 | H+B | Byte-identical state dump, twice in a row | ✅ |

## Epic 2 — The World Is Visible
| ID | Story | Pts | Owner | Definition of Done |
|---|---|---|---|---|
| V1 | First map built in the map editor (one district, ~20×20 tiles), exported as JSON | 2 | H | Map JSON in `/assets`, loads without errors |
| V2 | Web server + WebSocket: full state snapshot on connect, live deltas after | 3 | B | Browser receives snapshot plus one pushed delta |
| V3 | Renderer: draw map and agent sprites from state; animate movement events | 3 | B | A hand-injected MOVE event walks a sprite across the screen |
| V4 | First-pixels milestone: full end-to-end run | 1 | H | Screenshot committed to the repo |

## Epic 3 — The Orchestrator
| ID | Story | Pts | Owner | Definition of Done |
|---|---|---|---|---|
| O1 | Agent charter template: identity → CAN/CANNOT → one goal → loop | 1 | B | Product Owner approves the template |
| O2 | Agent v0: subprocess reads its charter, calls the model API, emits valid events | 3 | H+B | Agent acts on screen unprompted |
| O3 | Worker handles SPAWN/KILL events by starting/stopping agent subprocesses | 3 | B | Agents are born and killed via events only |
| O4 | Mortality proof: kill an agent mid-action; world loop and render unaffected | 2 | H | Video recorded and linked in the repo |

## Epic 4 — The Comms Channel
| ID | Story | Pts | Owner | Definition of Done |
|---|---|---|---|---|
| H1 | Command console in the UI: typed human directive becomes a valid event | 3 | B | A typed command visibly changes the world |
| H2 | World-to-human reporting: designated events surface as readable messages | 2 | B | A report is received without reading the database |
| H3 | Replay scrubber: timeline slider re-renders any past moment from the log | 3 | B | Drag the slider, watch history replay |

## Epic 1.5 — One Source of Truth — delivered, in review
*Proof: `python -m scripts.w5_live_proof` (W3/W4 still pass unchanged). Awaiting Product Owner acceptance.*
| ID | Story | Pts | Owner | Definition of Done | Done |
|---|---|---|---|---|---|
| W5 | Live bus writes to the log: `main.py` appends every envelope to the `events` table and runs the Worker; retire `worldlog.py` (jsonl) | 3 | B | A gesture over the live bus lands as an event row and mutates state through the Worker | 🟡 |

Closed the two-sources-of-truth gap: the WebSocket bus no longer journals to `data/world_log.jsonl` (retired). Every envelope now enters the SQLite `events` log; the Worker applies it on a fixed heartbeat. JSONL remains available on demand via `scripts/export_jsonl.py`.

## Epic 1.6 — The Door Holds — delivered, in review
*Defect fix, raised by a review of this repo against the MERO canon on 2026-09-18. Proof: `python -m scripts.w6_door_proof` (W3/W4/W5 pass unchanged).*
| ID | Story | Pts | Owner | Definition of Done | Done |
|---|---|---|---|---|---|
| W6 | The door validates world-verb payloads and the mood enum; the Worker quarantines an unapplicable event instead of wedging the cursor on it | 2 | B | A malformed `spawn` is refused at the door; one forced into the log is quarantined with a reason and the events behind it still apply; replay reproduces the quarantine | 🟡 |

Two defects, one root cause: the protocol was enforced in one direction only. `envelope()` rejected unknown moods on the way out; `validate()` — the inbound path from the browser — checked the verb and nothing else, so `mood: "banana"` and a `spawn` with no `agent_id` both reached the append-only log. The Worker then raised on that event every tick, and because the cursor advanced only *after* a successful apply, it never advanced: every event behind the bad one was logged and never applied. `main.py` caught the exception and logged a warning, so the world stopped silently. The door now checks verb, mood and the world-verb payload; `quarantine` is a derived state table, so replay rebuilds it identically and the state digest covers it.

## Icebox — out of scope until the Product Owner pulls them in
External messaging bridges · real-world data integrations · multi-district economy · world authoring/templating tools · local model routing · publications.
