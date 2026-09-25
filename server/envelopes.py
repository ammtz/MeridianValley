"""OVERWORLD — the language IS the physical world.

Every message on the bus (WebSocket) is an envelope. This file is the
single definition of the contract. The frontend renders envelopes; the
backend emits them. Nothing else crosses the wire.
"""
from __future__ import annotations

import time
from typing import Any

# The language, v2: seven words (DECISIONS #14, proposed).
#
# Two sets, moving in opposite directions:
#   SAY  — what may be emitted today. It can shrink at an amendment.
#   READ — what the log can be read with. It only ever grows, because the log
#          is append-only and every word once written must still replay.
# Adding or removing a word is a versioned, logged decision (DECISIONS.md).

# Room tier — the only words that move the world's state tables.
ROOM_VERBS = {
    "move",      # place an agent; a first placement is the join
    "leave",     # an agent leaves the world, with a handoff; mortal history
}

# Work tier — log-only, no spatial effect.
WORK_VERBS = {
    "ask",       # a request; may name what it waits on
    "report",    # how it is going: speech, findings, failure (payload.tool)
    "judge",     # a verdict: yes, no, or send it back — a person's call
    "deliver",   # the finished thing is handed over
}

# Machinery — the room's own voice: refusals, telemetry, lifecycle.
SYS_VERBS = {"sys"}

SAY = ROOM_VERBS | WORK_VERBS | SYS_VERBS

# Words from LANGUAGE v1 / amendment v1.1. Never said again; always readable.
# Each maps to the word that replaced it.
RETIRED = {
    "spawn": "move",       # a first placement
    "kill": "leave",
    "propose": "report",   # report, tool "plan"
    "assign": "ask",
    "develop": "report",
    "boost": "judge",      # a well-done is a yes
    "debug": "report",     # report, tool "debug"
    "review": "judge",
    "ship": "deliver",
    "levelup": "report",   # report, tool "levelup"
}

READ = SAY | set(RETIRED)

# Words the Worker applies to state — every room word ever written.
WORLD_VERBS = ROOM_VERBS | {"spawn", "kill"}

MOODS = {"flow", "focused", "stuck", "frustrated", "celebrating"}

# World verbs carry spatial payloads. The door checks these fields before an
# envelope may reach the log — ARCHITECTURE invariant #3: invalid events are
# rejected at the door, cheaply, before they can touch state. Without this the
# verb was checked and the payload was not, so a malformed `spawn` reached the
# append-only log and the Worker could never apply it.
WORLD_PAYLOAD: dict[str, tuple[str, ...]] = {
    "spawn": ("agent_id", "x", "y"),
    "move": ("agent_id", "x", "y"),
    "kill": ("agent_id",),
}


def envelope(
    type_: str,
    from_: str,
    to: str,
    payload: dict[str, Any] | None = None,
    *,
    story_id: str = "story.seed.first_problem",
    phase: str = "develop",   # a phase, not a verb
    mood: str = "focused",
    points: dict[str, int] | None = None,
) -> dict[str, Any]:
    if type_ not in SAY:
        raise ValueError(_refusal(type_))
    if mood not in MOODS:
        raise ValueError(f"unknown mood: {mood!r}")
    return {
        "type": type_,
        "from": from_,
        "to": to,
        "story_id": story_id,
        "phase": phase,
        "mood": mood,
        "points": points or {},
        "ts": int(time.time() * 1000),
        "payload": payload or {},
    }


def validate(env: dict[str, Any]) -> dict[str, Any]:
    """Incoming envelopes from the frontend pass through here. Reject
    anything that isn't a word the language speaks today."""
    if not isinstance(env, dict):
        raise ValueError("envelope must be an object")
    if env.get("type") not in SAY:
        raise ValueError(_refusal(env.get("type")))
    env.setdefault("payload", {})
    env.setdefault("from", "user")
    env.setdefault("to", "seed")
    env.setdefault("mood", "focused")

    if not isinstance(env["payload"], dict):
        raise ValueError("payload must be an object")

    # The mood enum was enforced on the way out (envelope()) and not on the way
    # in — two definition points for one rule. One door now, both directions.
    if env["mood"] not in MOODS:
        raise ValueError(f"unknown mood: {env['mood']!r}")

    required = WORLD_PAYLOAD.get(verb)
    if required is None:
        return env  # work/sys verbs are log-only; no spatial contract to check

    payload = env["payload"]
    for field in required:
        if field not in payload:
            raise ValueError(f"{verb!r} requires payload.{field}")

    aid = payload["agent_id"]
    if not isinstance(aid, str) or not aid.strip():
        raise ValueError(f"{verb!r} payload.agent_id must be a non-empty string")

    for axis in ("x", "y"):
        if axis in required:
            try:
                payload[axis] = int(payload[axis])
            except (TypeError, ValueError):
                raise ValueError(
                    f"{verb!r} payload.{axis} must be a whole number"
                ) from None

    return env


def _refusal(word: Any) -> str:
    if word in RETIRED:
        return f"retired word: {word!r} — say {RETIRED[word]!r}"
    return f"unknown word: {word!r} — not in the language"
