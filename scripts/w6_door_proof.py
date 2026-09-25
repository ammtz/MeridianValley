"""W6 proof — the door holds, and one bad event cannot stop the world.

Two defects this proves are gone:

1. The door checked the verb and never the payload, so a malformed `spawn`
   was appended to the append-only log. It could never be removed.
2. The Worker raised on that event every tick and the cursor never advanced,
   so every event behind it was logged and never applied — the world stopped,
   silently, and `main.py` logged a warning forever.

Run from the repo root:

    python -m scripts.w6_door_proof
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from server.db import append_event, init_db
from server.envelopes import envelope, validate
from server.worker import pump, replay, state_digest

# Envelopes that must never reach the log, and why.
REFUSED = [
    ({"type": "levelupp", "payload": {}}, "not a word in the language"),
    ({"type": "spawn", "payload": {"x": 1, "y": 1}}, "spawn with no agent_id"),
    ({"type": "move", "payload": {"agent_id": "a", "x": "over there", "y": 1}},
     "x is not a number"),
    ({"type": "kill", "payload": {"agent_id": "   "}}, "agent_id is blank"),
    ({"type": "develop", "mood": "banana"}, "mood is not in the enum"),
]


def main() -> None:
    db = Path(tempfile.mkdtemp()) / "world.db"
    conn = init_db(db)

    print("── the door ──")
    for env, why in REFUSED:
        try:
            validate(dict(env))
        except ValueError as e:
            print(f"  refused  {why:<28} → {e}")
        else:  # pragma: no cover - the proof fails loudly if the door opens
            raise SystemExit(f"DOOR OPEN: {why} was accepted")

    good = validate({"type": "spawn", "from": "world", "to": "alice",
                     "payload": {"agent_id": "alice", "x": "3", "y": 4}})
    assert good["payload"] == {"agent_id": "alice", "x": 3, "y": 4}
    print("  accepted a valid spawn; x coerced to a whole number")
    print(f"  events in the log after {len(REFUSED)} refusals:",
          conn.execute("SELECT COUNT(*) FROM events").fetchone()[0])

    print("\n── the Worker does not wedge ──")
    # Force a poisoned row straight into the log, bypassing the door, to prove
    # the Worker survives one that predates the fix (or arrives another way).
    conn.execute(
        "INSERT INTO events (verb, envelope, ts) VALUES (?, ?, ?)",
        ("spawn", json.dumps({"type": "spawn", "payload": {}}), 0),
    )
    conn.commit()
    for e in [
        envelope("spawn", "world", "alice",
                 {"agent_id": "alice", "name": "Alice", "x": 1, "y": 1}),
        envelope("move", "alice", "world", {"agent_id": "alice", "x": 2, "y": 3}),
    ]:
        append_event(conn, e)

    applied = pump(conn)
    cursor = conn.execute(
        "SELECT last_applied FROM worker_cursor WHERE id=0"
    ).fetchone()["last_applied"]
    quarantined = [dict(r) for r in conn.execute("SELECT * FROM quarantine")]
    alice = conn.execute(
        "SELECT x, y FROM positions WHERE agent_id='alice'"
    ).fetchone()

    print(f"  stepped over {applied} events; cursor at {cursor}")
    for q in quarantined:
        print(f"  quarantined event {q['event_id']} ({q['verb']}): {q['reason']}")
    print(f"  alice, who was logged behind the bad event: {dict(alice)}")
    assert dict(alice) == {"x": 2, "y": 3}, "events behind a bad one must still apply"
    assert len(quarantined) == 1

    print("\n── replay still reproduces everything ──")
    first = state_digest(conn)
    replay(conn)
    second = state_digest(conn)
    replay(conn)
    third = state_digest(conn)
    print("  live   :", first)
    print("  replay :", second)
    print("  again  :", third)
    assert first == second == third, "quarantine must rebuild identically"

    print("\nW6 PROOF PASSED — the door holds, the world keeps moving.")


if __name__ == "__main__":
    main()
