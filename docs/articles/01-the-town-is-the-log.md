# The Town Is the Log

### Building Meridian Valley, a pixel-art world where AI agents live, work, and die in public

*[author · pending Product Owner approval] · draft 1 · September 2026*

<!-- HERO IMAGE: screenshot or GIF of the office with agents at their desks.
     Lands with milestone M1 (docs/first-world/M1.png). No image, no publish. -->

---

I run a lot of AI agents. At some point I noticed I couldn't tell you what any of
them was doing.

They were working. Tokens were being spent, files were changing, and somewhere a
terminal was scrolling. But "what is my system doing right now?" had no answer
you could *look at*. There were only logs: walls of JSON that you grep after
something breaks.

So I asked a different question. **What if the log was a place?**

Not a dashboard or a trace viewer. A town. Agents are the people in it. When one
starts a task, you see it walk to a desk. When it's stuck, a bubble appears over
its head. When it's killed, it vanishes and the town keeps going. You'd learn what
the system is doing the same way you learn what a busy street is doing, by
watching it.

That town is **Meridian Valley**.

## Three deliverables, nothing else

The project has one rule about scope: anything that doesn't serve one of these
three things is out.

1. **A world that persists.** Every change is an event in an append-only log. You
   can replay any past moment.
2. **An orchestrator.** One process is the only writer of world state. It spawns
   agents, watches them, and kills them. Agents are mortal. The world isn't.
3. **A human/AI comms channel.** One place where I direct the work and the world
   reports back.

The pixel art is the fun part, but it isn't the product. It's what lets you see
the product.

## The laws of physics

Before writing any rendering code, I wrote down the invariants. They're the parts
I'd defend in a design review. Everything else is negotiable.

- **Append-only event log.** The log is never edited or truncated. Replaying it
  from zero must rebuild the exact world.
- **One writer.** Agents and humans don't change the world. They *ask* for
  changes by emitting events. A single Worker applies those events one at a time,
  in order.
- **A frozen vocabulary.** Events use a small set of typed verbs. Anything
  outside that set is rejected at the door, before it can touch state.
- **Mortal agents, immortal world.** Killing an agent must never disturb the
  world loop or the render.
- **A fixed heartbeat.** The world ticks at a steady rate, so progress is
  observable and runs can be compared.
- **Render is a pure function of state.** The renderer draws. It never writes and
  never decides.

All six collapse into one loop, and every feature in the system has to be an
instance of it:

```
gesture → emit event → log → Worker applies → state → render
```

If a design doesn't fit that loop, the design is wrong. That sentence has saved
me more time than any library.

## Language is the physical world

The first commit message reads: *"The language is the physical world. Worker is
sole mutator."* That was the idea I most wanted to test.

In Meridian Valley, the protocol isn't a transport detail. It's the laws of
nature. There are three tiers of verbs:

| Tier | Verbs | What they do |
|---|---|---|
| **World** | `spawn`, `move`, `kill` | The only verbs that change space. They're how agents enter, move, and leave. |
| **Work** | `propose`, `assign`, `develop`, `boost`, `debug`, `review`, `ship`, `levelup` | The story of the work. Recorded, but nothing moves. |
| **System** | `sys` | The world's machinery: errors, telemetry, lifecycle. |

An event is a small JSON envelope:

```json
{
  "type": "spawn",
  "from": "world",
  "to": "alice",
  "mood": "focused",
  "payload": { "agent_id": "alice", "name": "Alice", "x": 1, "y": 1 }
}
```

Moods are a closed set too: `flow`, `focused`, `stuck`, `frustrated`,
`celebrating`. It's a small detail, but it means "how is the agent doing?" is
something you can query, not something you guess from reading prose.

`move` targets are absolute, so applying the same event twice changes nothing.
That property (idempotency) is what makes the next part possible.

## Proving the world persists

Epic 1 was all plumbing, and I think it was worth it: a SQLite table for the log,
a few state tables, and a single-threaded Python Worker that reads the next
event, validates it, applies it, and repeats.

Then came the replay proof. Wipe the state, replay the full log from event zero,
and dump the result. Do it twice and compare. The dumps have to match
**byte for byte**, both times.

They do. It's the least visual milestone in the project, and the one I trust
most. Once replay is deterministic, "what happened at 3:14pm?" stops being a
forensic exercise. You scrub back to it.

## A project that runs on its own protocol

Most of Meridian Valley is built by AI coding agents, and the project is run the
way the world is.

There's a `DIRECTIVE.md` that any contributor, human or AI, can follow with zero
context. The roles are strict. **I'm the Product Owner: I decide. The agents are
Builders: they deliver and propose, but they never decide.** Work comes in
stories with Fibonacci points and a Definition of Done, with a work-in-progress
limit of one.

Decisions go in a `DECISIONS.md` ledger. Builders are told to argue from it "the
way a lawyer argues from case law": follow precedent when it exists, extrapolate
when it doesn't, and escalate anything irreversible.

Even the git history speaks the protocol. Commit messages are envelopes (verb,
actor, intent, effect):

```
W4: builder proves replay — identical state rebuilt from the log
pivot: product owner adopts Paperclip + Pixel Agents as the first world
reframe: builder states the first-world principle — adopt, remake only what's necessary, create everywhere else
```

Read the log and you get the story of the project, told by the same grammar the
town uses.

## The pivot: adopt, remake, create

Here's the part I didn't plan.

With the persistence layer proven, the backlog said the next step was to build the
renderer, the agent runtime, and the orchestrator. That's weeks of work, and when
I looked around, two open-source projects had already built most of it, very
well:

- **[Paperclip](https://github.com/paperclipai/paperclip)** runs *companies* of
  AI agents, with org charts, issues, budgets, board approvals, a heartbeat
  scheduler, and an append-only activity log.
- **[Pixel Agents](https://github.com/pixel-agents-hq/pixel-agents)** turns
  Claude Code sessions into animated characters in a pixel-art office, with a
  clean event runtime and a typed wire protocol.

One is a system of record with no body. The other is a body with no system of
record. Put together, they're most of Meridian Valley's first world.

So I logged Decision #10, and it's the principle the project runs on now:

> **Adopt what is proven. Remake only what is necessary. Create everywhere else.**

Both projects are forked. Paperclip is the system of record and carries **zero
changes**. Pixel Agents is the projection, a view with no business state of its
own. The new code is a thin bridge between them, and it speaks Pixel Agents' own
event types, so its runtime, protocol, and UI stay untouched:

```
Paperclip (the company)  ──live events──►  Pixel Agents (the office)
       ▲                                          ▲
       └──── approve from the office ◄────────────┤
                                                  │
              Claude Code agent ── hook events ───┘
```

Three channels, one owner each:

- **A: what an agent is doing right now** (tool calls, turns, permission
  prompts). This flows from the agent's own hooks and already exists.
- **B: who the agent is and what the company is doing** (runs, status,
  approvals, budgets). This is new: a stream source that subscribes to Paperclip.
- **C: the human acting from the office.** Click the bubble over an agent that's
  waiting on the board, and approve its request right there.

The mapping that made it click: Pixel Agents already had a *team* model (lead,
teammates, names), and Paperclip already had an *org chart*. A company becomes a
team, the CEO becomes the lead, and `reportsTo` becomes the line to the lead. No
protocol change needed.

I didn't throw away the laws. Paperclip's activity log is append-only, so the
first world keeps the invariant. It just keeps it with someone else's code. My
own SQLite log isn't deleted either. It's **frozen**, waiting for the first thing
the office produces that Paperclip doesn't record: positions, gestures, the
physical life of the town. When that shows up, the log comes back.

The lesson I keep relearning: **your principles are the asset, not your code.**
The six laws took an afternoon to write, and they survived a complete change of
stack. Most of the code didn't need to.

## Where it stands

I'd rather be honest than impressive, so here's the actual state:

| Milestone | What it proves | Status |
|---|---|---|
| **M0** | Forks in place | ✅ done |
| **M1** | A Paperclip agent's run animates in the office, with zero new code | next |
| **M2** | One character per *employee*, stable across heartbeats | planned |
| **M3** | The office shows company state: running, waiting on the board, out of budget | planned |
| **M4** | Approve a board request by clicking the bubble | planned |

After M4, the adopting is over and the creating starts. These are the parts that
don't exist anywhere yet:

- **An office laid out from the org chart.** Departments become rooms, and a
  manager's desk sits near their reports.
- **Budgets drawn in the room.** You see spend per character, and a budget
  incident is visible without opening a dashboard.
- **A replayable office.** Drag a slider and watch last Tuesday happen again.

## Why bother

Multi-agent systems are getting bigger faster than our ability to see inside
them. We give agents budgets, bosses, and deadlines, and then we supervise them
through text files.

I think the interface for a population of agents looks less like a log viewer and
more like a place. A place you can glance at, where "something's wrong" looks
like a character stuck in a hallway, not a stack trace on line 40,000.

Meridian Valley is my attempt at that place. It's early, it's open, and it's
being built in public, mostly by the agents it will eventually house.

**Follow along:** [github.com/ammtz/MeridianValley](https://github.com/ammtz/MeridianValley)

---

*Meridian Valley is MIT-licensed. It builds on
[Paperclip](https://github.com/paperclipai/paperclip) and
[Pixel Agents](https://github.com/pixel-agents-hq/pixel-agents), both MIT. Thanks
to their authors for building the foundations this world stands on.*
