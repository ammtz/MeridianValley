"""W3 proof — injected events mutate state correctly.

Events are emitted through the single append path; only the Worker writes
state. Run from the repo root:

    python -m scripts.w3_apply_proof
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from server.db import append_event, init_db
from server.envelopes import envelope
from server.worker import pump


def main() -> None:
    db = Path(tempfile.mkdtemp()) / "world.db"
    conn = init_db(db)

    # A tiny history, emitted into the log (never writing state directly).
    append_event(conn, envelope("spawn", "world", "alice",
                                 {"agent_id": "alice", "name": "Alice", "x": 1, "y": 1}))
    append_event(conn, envelope("spawn", "world", "bob",
                                 {"agent_id": "bob", "name": "Bob", "x": 5, "y": 5}))
    append_event(conn, envelope("move", "alice", "world",
                                 {"agent_id": "alice", "x": 2, "y": 3}))
    append_event(conn, envelope("kill", "world", "bob", {"agent_id": "bob"}))

    assert pump(conn) == 4, "expected 4 events applied"

    alice_pos = conn.execute(
        "SELECT x, y FROM positions WHERE agent_id='alice'").fetchone()
    assert (alice_pos["x"], alice_pos["y"]) == (2, 3), dict(alice_pos)

    alice = conn.execute("SELECT status FROM agents WHERE id='alice'").fetchone()
    assert alice["status"] == "alive", dict(alice)

    bob = conn.execute("SELECT status FROM agents WHERE id='bob'").fetchone()
    assert bob["status"] == "dead", dict(bob)

    # Idempotency: a second pump applies nothing and state is unchanged.
    assert pump(conn) == 0, "cursor should make re-pump a no-op"

    print("W3 PASS — spawn/move/kill mutate state correctly; pump is idempotent")


if __name__ == "__main__":
    main()
