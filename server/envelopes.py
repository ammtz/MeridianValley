"""OVERWORLD — the language IS the physical world.

Every message on the bus (WebSocket) is an envelope. This file is the
single definition of the contract. The frontend renders envelopes; the
backend emits them. Nothing else crosses the wire.
"""
from __future__ import annotations

import time
from typing import Any

# The lexicon, in tiers. Adding a verb is a versioned, logged decision
# (see DECISIONS.md). Everything on the bus is one of these words.

# Work tier — orchestration of stories and agents (LANGUAGE v1).
WORK_VERBS = {
    "propose",   # a story/plan enters the world
    "assign",    # work attaches to an agent
    "develop",   # work happening: speech, findings, questions, chat
    "boost",     # orchestrator gives an agent a push
    "debug",     # something went wrong, being handled
    "review",    # a gate: human judgment requested
    "ship",      # done — the first move exists
    "levelup",   # growth event
}

# World tier — physical events with spatial effect (amendment v1.1).
# These are the only verbs that move the world's state tables.
WORLD_VERBS = {
    "spawn",     # an agent enters the world at a position
    "move",      # an agent changes position (absolute target)
    "kill",      # an agent leaves the world; it becomes mortal history
}

# System tier — world machinery: errors, telemetry, lifecycle.
SYS_VERBS = {"sys"}

VERBS = WORK_VERBS | WORLD_VERBS | SYS_VERBS

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
    phase: str = "develop",
    mood: str = "focused",
    points: dict[str, int] | None = None,
) -> dict[str, Any]:
    if type_ not in VERBS:
        raise ValueError(f"unknown word: {type_!r} — not in the language")
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
    """The door. Every envelope from outside passes through here before it is
    appended to the log. Reject anything that is not a word in the language,
    and — for the world verbs — anything the Worker could not later apply.

    Raises ValueError with a plain reason; the caller turns that into a `sys`
    envelope so a refusal is itself recorded. Silence is never the signal.
    """
    if not isinstance(env, dict):
        raise ValueError("envelope must be an object")

    verb = env.get("type")
    if verb not in VERBS:
        raise ValueError(f"unknown word: {verb!r}")

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
