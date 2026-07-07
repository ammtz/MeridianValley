"""OVERWORLD — the language IS the physical world.

Every message on the bus (WebSocket) is an envelope. This file is the
single definition of the contract. The frontend renders envelopes; the
backend emits them. Nothing else crosses the wire.
"""
from __future__ import annotations

import time
from typing import Any

VERBS = {
    "propose",   # a story/plan enters the world
    "assign",    # work attaches to an agent
    "develop",   # work happening: speech, findings, questions, chat
    "boost",     # orchestrator gives an agent a push
    "debug",     # something went wrong, being handled
    "review",    # a gate: human judgment requested
    "ship",      # done — the first move exists
    "levelup",   # growth event
    "sys",       # world machinery: errors, telemetry, lifecycle
}

MOODS = {"flow", "focused", "stuck", "frustrated", "celebrating"}


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
    """Incoming envelopes from the frontend pass through here. Reject
    anything that isn't a word in the language."""
    if not isinstance(env, dict):
        raise ValueError("envelope must be an object")
    if env.get("type") not in VERBS:
        raise ValueError(f"unknown word: {env.get('type')!r}")
    env.setdefault("payload", {})
    env.setdefault("from", "user")
    env.setdefault("to", "seed")
    return env
