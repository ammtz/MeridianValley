# DECISIONS

Standing decisions. Consult before deciding anything; extrapolate from precedent like case law. New entries require Product Owner sign-off.

| # | Date | Decision | Rationale |
|---|---|---|---|
| 1 | 2026-07-11 | The event protocol (typed verbs + enforced envelopes) is frozen at v1. New verbs are a versioned, logged decision. | Validation, replay, cost control |
| 2 | 2026-07-11 | The Worker is the sole writer of world state. No exceptions, ever. | Auditability and deterministic replay |
| 3 | 2026-07-11 | MVP stack is locked as defined in `ARCHITECTURE.md`. Upgrades happen only at the graduation triggers listed there. | Simplicity; no premature infrastructure |
| 4 | 2026-07-11 | Art style: "Modern Workplace" — top-down 3/4 view, 16×16 purchased tilesets, maps authored in Tiled. True isometric deferred to a possible re-skin. | Cheapest render path; render is a pure function of state, so the style can change later |
| 5 | 2026-07-11 | Repository markdown is the canonical documentation. External tools are dashboards only. | One source of truth every contributor and agent can read |
| 6 | 2026-07-11 | Process: agile stories with Fibonacci points, one-week sprints, WIP limit of 1. | Limited contributor time; plan on velocity, not optimism |
| 7 | 2026-07-11 | All real-world integrations removed from scope (icebox). | Focus on the mission's three deliverables only |
| 8 | 2026-07-13 | Protocol amendment v1.1 **ratified** (via PR #2 merge): world-tier verbs `spawn`, `move`, `kill` join the frozen lexicon. Agents enter, move, and leave space through these three words only. | Epics 1–3 need world-physics events distinct from the work-orchestration verbs; keeps validation/replay guarantees while giving the Worker something to apply to `agents`/`positions` |
| 9 | 2026-07-13 | For the Epic 1 delivery, the WIP-limit-of-1 was overridden once: all four W-stories were built and shipped as a single batch (PR #2) at Product Owner request. A deliberate one-time exception, not a change to Decision #6. | The Product Owner chose to review the epic as one pile; the default remains WIP = 1 |
| 10 | 2026-09-23 | **First world: adopt, remake only what's necessary, create everywhere else.** Paperclip (system of record) and Pixel Agents (projection) are forked as foundations; the integration is a stream source inside the Pixel Agents fork. Spec: `docs/FIRST-WORLD.md` (AD-1…AD-7). Pauses the `ARCHITECTURE.md` stack table and Epics 2–3; this repo's event log is frozen until the office emits state Paperclip does not record. | Working is the goal. Proven foundations give a running world immediately; our effort goes where nothing exists yet |
| 14 | 2026-09-25 | **Proposed, awaiting Product Owner sign-off.** LANGUAGE v2: seven words — `move`, `leave` (room), `ask`, `report`, `judge`, `deliver` (work), `sys`. The ten older words are refused at emission and kept readable forever, so any existing log replays unchanged. A first `move` is the join. Amends #1 and #8. Spec: `PROTOCOL.md`. Proof: `scripts/seven_words_proof.py`. | Product Owner ruled the seven on 2026-09-18 and asked on 2026-09-25 for the code to match. Seven acts, no two words for the same act. The say set can shrink; the read set only grows, because the log is append-only |

## DOs
- Delete before adding.
- Ship the smallest working increment.
- Put every external dependency behind a mock-to-live seam (build against a fake, swap in the real thing later).
- Make the Worker idempotent: applying the same event twice must be harmless.

## DON'Ts
- Don't add infrastructure before its graduation trigger fires.
- Don't touch the event protocol casually.
- Don't let anything except the Worker write state — not scripts, not tests, not "just this once."
- Don't start a second story while one is in progress.
