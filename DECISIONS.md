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
