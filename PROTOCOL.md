# EVENT PROTOCOL — reference card (v2, seven words)

Every change to the world is one **event**: a JSON **envelope** whose `type` is
a **verb** from the language. A word the language does not speak today is
rejected at the door, and the refusal names the word that replaced it.
This one page is enough to write a valid event by hand.

The lexicon is defined once in `server/envelopes.py`; changing it is a logged
decision in `DECISIONS.md` (this card is at v2, DECISIONS #14, proposed).

## The envelope

```json
{
  "type": "move",           // the verb — must be in the lexicon (required)
  "from": "world",          // who emits it
  "to": "alice",            // who/what it concerns
  "story_id": "story.seed.first_problem",
  "phase": "develop",       // a phase, not a verb
  "mood": "focused",        // one of: flow, focused, stuck, frustrated, celebrating
  "points": {},
  "ts": 1752380000000,      // ms since epoch
  "payload": { }            // verb-specific fields (see below)
}
```

Build one in Python with `server.envelopes.envelope(type, from, to, payload)` —
it fills defaults and rejects unknown or retired verbs and moods.

## Verbs

Seven words. Only **room** words mutate the state tables; **work** and **sys**
words are recorded in the log but change no spatial state.

### Room — moves the world

| Verb | Effect on state | Required payload | Example payload |
|---|---|---|---|
| `move`  | a first placement is the join: the agent becomes `alive` there. After that, its position is set to an absolute target | `agent_id`, `x`, `y` (opt. `name` on the first) | `{"agent_id":"alice","name":"Alice","x":1,"y":1}` |
| `leave` | agent becomes `dead` (mortal history) | `agent_id` | `{"agent_id":"bob"}` |

`move` on an agent that left is ignored. Targets are absolute, so applying the
same `move`/`leave` twice leaves state unchanged.

### Work — log-only

| Verb | Meaning |
|---|---|
| `ask` | a request; may name what it waits on |
| `report` | how it is going: speech, findings, failure. `payload.tool` names the kind: `plan`, `levelup`, `debug` |
| `judge` | a verdict: yes, no, or send it back — a person's call |
| `deliver` | the finished thing is handed over |

Example: `{"type":"report","from":"alice","to":"world","payload":{"text":"scanning the district"}}`

### Machinery

| Verb | Meaning |
|---|---|
| `sys` | the room's own voice: refusals, telemetry, lifecycle |

### Retired words — never said, always read

The log is append-only, so a word once written must replay forever. What may
be **said** can shrink; what can be **read** only grows. These ten are refused
at emission and still applied on replay:

| Retired | Say instead |
|---|---|
| `spawn` | `move` (a first placement) |
| `kill` | `leave` |
| `propose` | `report`, tool `plan` |
| `assign` | `ask` |
| `develop` | `report` |
| `boost` | `judge` (a yes) |
| `debug` | `report`, tool `debug` |
| `review` | `judge` |
| `ship` | `deliver` |
| `levelup` | `report`, tool `levelup` |

Proof: `python -m scripts.seven_words_proof` — every retired word is refused,
and a log in the old words reaches the same state as the same history in the
seven.

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
