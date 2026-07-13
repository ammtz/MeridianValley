# EVENT PROTOCOL — reference card (v1.1)

Every change to the world is one **event**: a JSON **envelope** whose `type` is
a **verb** from the frozen lexicon. Invalid verbs are rejected at the door.
This one page is enough to write a valid event by hand.

## The envelope

```json
{
  "type": "spawn",          // the verb — must be in the lexicon (required)
  "from": "world",          // who emits it
  "to": "alice",            // who/what it concerns
  "story_id": "story.seed.first_problem",
  "phase": "develop",
  "mood": "focused",        // one of: flow, focused, stuck, frustrated, celebrating
  "points": {},
  "ts": 1752380000000,      // ms since epoch
  "payload": { }            // verb-specific fields (see below)
}
```

Build one in Python with `server.envelopes.envelope(type, from, to, payload)` —
it fills defaults and rejects unknown verbs and moods.

## Verbs

Three tiers. Only **world** verbs mutate the state tables; **work** and **sys**
verbs are recorded in the log but change no spatial state.

### World tier — moves the world (v1.1)

| Verb | Effect on state | Required payload | Example payload |
|---|---|---|---|
| `spawn` | agent becomes `alive` at a position | `agent_id`, `x`, `y` (opt. `name`) | `{"agent_id":"alice","name":"Alice","x":1,"y":1}` |
| `move`  | agent's position set to an absolute target | `agent_id`, `x`, `y` | `{"agent_id":"alice","x":2,"y":3}` |
| `kill`  | agent becomes `dead` (mortal history) | `agent_id` | `{"agent_id":"bob"}` |

`move` on a nonexistent or dead agent is ignored. Targets are absolute, so
applying the same `spawn`/`move`/`kill` twice leaves state unchanged.

### Work tier — orchestration (LANGUAGE v1, log-only)

| Verb | Meaning |
|---|---|
| `propose` | a story/plan enters the world |
| `assign` | work attaches to an agent |
| `develop` | work happening: speech, findings, questions, chat |
| `boost` | orchestrator gives an agent a push |
| `debug` | something went wrong, being handled |
| `review` | a gate: human judgment requested |
| `ship` | done — the move exists |
| `levelup` | growth event |

Example: `{"type":"develop","from":"alice","to":"world","payload":{"text":"scanning the district"}}`

### System tier

| Verb | Meaning |
|---|---|
| `sys` | world machinery: errors, telemetry, lifecycle |

## Write one by hand

A valid `move` event, start to finish:

```json
{"type":"move","from":"alice","to":"world","story_id":"story.seed.first_problem",
 "phase":"develop","mood":"focused","points":{},"ts":1752380000000,
 "payload":{"agent_id":"alice","x":4,"y":7}}
```

Append it to the log with `server.db.append_event(conn, env)`; the Worker
(`server.worker.pump`) applies it. That is the whole loop:
**emit → log → Worker applies → state → render.**
