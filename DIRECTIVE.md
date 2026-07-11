# DIRECTIVE

Read this first. It defines how work gets done in this project. It applies to every contributor, human or AI, with zero prior context assumed.

## Mission

Build three things:

1. **A virtual world that persists.** A world loop that never stops. Every change is an event in an append-only log; any past moment can be replayed.
2. **An orchestrator.** One process that is the sole writer of world state and manages agent lifecycles. Agents are mortal; the world is not.
3. **A human/AI comms channel.** One place where the human directs the work and the world reports back.

Anything not serving these three is out of scope.

## Chain of command

- **Product Owner (the human user):** owns the backlog, priorities, and acceptance. Final authority on everything.
- **Builder (AI instance or developer):** executes stories, delivers complete runnable artifacts, proposes but never decides.

A story is Done only when the Product Owner has seen it work.

## Way of working

- Unit of work = **story**: ID, one-line description, points, owner tag, Definition of Done (DoD).
- Points (Fibonacci): 1 trivial · 2 small · 3 one solid session · 5 large · 8 must be split before starting.
- Owner tags: `[H]` human-only (keys, money, machines, accounts) · `[B]` builder delivers fully · `[H+B]` builder drafts, human executes.
- One-week sprints. **Work-in-progress limit = 1 story.**
- Every working session ends with a commit or a logged decision. No exceptions.
- Commit messages use envelope style: verb, actor, intent, effect.

## Executing a task — the decision tree

1. Story already in progress? → Finish it. WIP = 1.
2. No story in progress? → Take the topmost unblocked story in `BACKLOG.md` for the current sprint.
3. Story is 8 points or its DoD is unclear? → Split or clarify with the Product Owner before starting.
4. Facing a decision mid-story? → Check `DECISIONS.md` first. Precedent exists → follow it, or extrapolate from it the way a lawyer argues from case law. No precedent → take the smallest reversible option; if the choice is irreversible or costly, escalate to the Product Owner.
5. Blocked on a human action? → Flag it explicitly, then prepare the next story's draft. Never idle; never improvise around the block.
6. DoD met? → Demo to the Product Owner. Accepted → commit and log. Rejected → back to in-progress with notes.

## Communication

- The builder always reports in this order: **what was done → what needs human action → what's next.**
- Plain language. Jargon is defined at first use.
- Silence is failure. If nothing shipped, say so and say why.

## Tie-breaker principles

- **KISS.** Prefer deleting to adding.
- **Risk rule.** If the worst outcome is survivable and the best is worth it, proceed.
- **Time > money.** Spend small money to save hours, never the reverse.
- **Scope is sacred.** Never expand it unilaterally; propose to the Product Owner.

## Repository map

- `BACKLOG.md` — the ordered product backlog.
- `DECISIONS.md` — standing decisions and DOs/DON'Ts. Consult before deciding anything.
- `ARCHITECTURE.md` — the technical laws of the world: stack, invariants, and their rationale.
