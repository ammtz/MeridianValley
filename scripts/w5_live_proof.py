"""W5 proof — one envelope, end to end over the live WebSocket.

Sends real gestures across the bus, then shows (1) they landed as rows in the
SQLite `events` log and (2) the Worker mutated state from that log — with no
direct state write anywhere but the Worker.

    python -m scripts.w5_live_proof
"""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path

# Isolate: point the world at a throwaway DB before importing the app.
os.environ["OVERWORLD_DB"] = str(Path(tempfile.mkdtemp()) / "world.db")

from starlette.testclient import TestClient  # noqa: E402

from server.envelopes import envelope  # noqa: E402
from server.main import app  # noqa: E402


def main() -> None:
    db_path = os.environ["OVERWORLD_DB"]

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.receive_text()  # drain the seed's greeting
            ws.send_text(json.dumps(envelope(
                "spawn", "user", "world",
                {"agent_id": "scout", "name": "Scout", "x": 3, "y": 4})))
            ws.receive_text()  # server ack ("spawn heard")
            ws.send_text(json.dumps(envelope(
                "move", "user", "world", {"agent_id": "scout", "x": 7, "y": 2})))
            ws.receive_text()  # server ack ("move heard")
            time.sleep(0.5)    # let the world tick (the heartbeat applies the log)

        insp = sqlite3.connect(db_path)
        insp.row_factory = sqlite3.Row
        verbs = [r["verb"] for r in insp.execute("SELECT verb FROM events ORDER BY id")]
        agent = insp.execute(
            "SELECT id, status FROM agents WHERE id='scout'").fetchone()
        pos = insp.execute(
            "SELECT x, y FROM positions WHERE agent_id='scout'").fetchone()

    print("events log verbs :", verbs)
    print("agent row        :", dict(agent) if agent else None)
    print("position row     :", dict(pos) if pos else None)

    assert "spawn" in verbs and "move" in verbs, "gestures did not reach the log"
    assert agent and agent["status"] == "alive", "spawn did not mutate state"
    assert pos and (pos["x"], pos["y"]) == (7, 2), "move did not mutate state"

    print("\nW5 PASS — envelope → live bus → events log → Worker → state, end to end")


if __name__ == "__main__":
    main()
