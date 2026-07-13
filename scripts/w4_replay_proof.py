"""W4 proof — wipe state, replay the whole log, reach identical state twice.

Run from the repo root:

    python -m scripts.w4_replay_proof
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from server.db import append_event, init_db
from server.envelopes import envelope
from server.worker import pump, replay, state_digest, state_dump


def main() -> None:
    db = Path(tempfile.mkdtemp()) / "world.db"
    conn = init_db(db)

    for e in [
        envelope("spawn", "world", "alice",
                 {"agent_id": "alice", "name": "Alice", "x": 1, "y": 1}),
        envelope("spawn", "world", "bob",
                 {"agent_id": "bob", "name": "Bob", "x": 5, "y": 5}),
        envelope("move", "alice", "world", {"agent_id": "alice", "x": 2, "y": 3}),
        envelope("move", "bob", "world", {"agent_id": "bob", "x": 9, "y": 0}),
        envelope("kill", "world", "bob", {"agent_id": "bob"}),
    ]:
        append_event(conn, e)

    pump(conn)
    live = state_digest(conn)

    replay(conn)
    first = state_digest(conn)
    replay(conn)
    second = state_digest(conn)

    print("live    :", live)
    print("replay 1:", first)
    print("replay 2:", second)
    assert live == first == second, "state is not reproducible from the log"

    print("\n--- canonical state dump ---")
    print(state_dump(conn))
    print("\nW4 PASS — byte-identical state across replays:", first)


if __name__ == "__main__":
    main()
