"""Seven Words proof — LANGUAGE v2: the say set shrinks, the read set grows.

Shows three things, offline:
  1. every retired word is refused at emission and at the door, with the word
     that replaced it named in the refusal;
  2. a log written in the old words still replays, and reaches the same state
     as the same history said in the seven;
  3. a first `move` is the join, and a `move` after `leave` changes nothing.

    python -m scripts.seven_words_proof
"""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

from server.db import append_event, init_db
from server.envelopes import READ, RETIRED, SAY, envelope, validate
from server.worker import pump, replay, state_dump


def raw(verb: str, payload: dict) -> dict:
    """An envelope as an older log wrote it — built by hand, because the
    emitter no longer speaks these words."""
    return {"type": verb, "from": "world", "to": "world",
            "story_id": "story.seed.first_problem", "phase": "develop",
            "mood": "focused", "points": {}, "ts": int(time.time() * 1000),
            "payload": payload}


def world(events: list[dict]) -> str:
    conn = init_db(Path(tempfile.mkdtemp()) / "world.db")
    for e in events:
        append_event(conn, e)
    pump(conn)
    live = state_dump(conn)
    replay(conn)
    assert state_dump(conn) == live, "replay diverged from the live pump"
    return live


def main() -> None:
    assert len(SAY) == 7, sorted(SAY)
    assert SAY <= READ and set(RETIRED) <= READ

    # 1. refused, with the replacement named
    for old, new in RETIRED.items():
        for attempt in (lambda: envelope(old, "world", "user"),
                        lambda: validate({"type": old})):
            try:
                attempt()
            except ValueError as e:
                assert repr(new) in str(e), str(e)
            else:
                raise AssertionError(f"{old!r} was not refused")

    # 2. the old words replay to the same world as the seven
    old_log = [
        raw("spawn", {"agent_id": "alice", "name": "Alice", "x": 1, "y": 1}),
        raw("spawn", {"agent_id": "bob", "name": "Bob", "x": 5, "y": 5}),
        raw("develop", {"say": ["log-only; no effect on state"]}),
        raw("move", {"agent_id": "alice", "x": 2, "y": 3}),
        raw("kill", {"agent_id": "bob"}),
    ]
    new_log = [
        envelope("move", "world", "alice",
                 {"agent_id": "alice", "name": "Alice", "x": 1, "y": 1}),
        envelope("move", "world", "bob",
                 {"agent_id": "bob", "name": "Bob", "x": 5, "y": 5}),
        envelope("report", "seed", "user", {"say": ["log-only"]}),
        envelope("move", "alice", "world", {"agent_id": "alice", "x": 2, "y": 3}),
        envelope("leave", "world", "bob", {"agent_id": "bob"}),
    ]
    old, new = world(old_log), world(new_log)
    assert old == new, f"old words and seven words disagree:\n{old}\n---\n{new}"

    # 3. join on first move; nothing after leave
    after = world(new_log + [
        envelope("move", "world", "bob", {"agent_id": "bob", "x": 0, "y": 0})])
    assert after == new, "a move after leave changed the world"

    print(new)
    print(f"\nSEVEN WORDS PASS — say {len(SAY)}, read {len(READ)}; "
          f"{len(RETIRED)} retired words refused; old log replays to the same state")


if __name__ == "__main__":
    main()
