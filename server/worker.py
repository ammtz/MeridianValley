"""W3 — Worker v0: the sole writer of world state.

The loop, reduced to its essence:

    read next event → validate → apply to state → advance cursor → repeat

Idempotent by construction (DECISIONS.md DO): every apply is an absolute set
(spawn/move write an exact position; kill flips a status), and the cursor
guarantees an event is never applied twice. Applying the same event twice is
therefore harmless.

W4 — replay: wipe the derived state, reset the cursor, pump the whole log.
Because state is a pure function of the ordered events, the rebuilt state is
byte-identical every time.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any

from .db import STATE_TABLES
from .envelopes import WORLD_VERBS


class Unapplicable(Exception):
    """An event that is in the log but cannot be applied to state.

    The log is append-only, so a bad event cannot be removed. Before this
    existed the Worker raised on every tick against the same event and the
    cursor never advanced — one malformed envelope stopped the world for good,
    silently. Now the reason is recorded in `quarantine` and the cursor moves
    on. Deterministic, so replay reproduces the same quarantine rows.
    """


def _quarantine(conn: sqlite3.Connection, event_id: int,
                env: dict[str, Any], err: Exception) -> None:
    conn.execute(
        "INSERT INTO quarantine (event_id, verb, reason) VALUES (?, ?, ?) "
        "ON CONFLICT(event_id) DO UPDATE SET "
        "  verb=excluded.verb, reason=excluded.reason",
        (event_id, str(env.get("type")), f"{type(err).__name__}: {err}"),
    )


def _payload(env: dict[str, Any]) -> dict[str, Any]:
    return env.get("payload") or {}


def apply(conn: sqlite3.Connection, event_id: int, env: dict[str, Any]) -> None:
    """Apply ONE event to state. This is the only function that writes state.

    Work-tier and sys verbs are log-only: they persist in `events` but carry
    no spatial effect, so state is untouched. Only room words move the world:
    `move` and `leave`, plus `spawn` and `kill`, which older logs carry.
    """
    verb = env.get("type")
    if verb not in WORLD_VERBS:
        return  # work/sys orchestration lives in the log only

    p = _payload(env)
    aid = p.get("agent_id")
    if not isinstance(aid, str) or not aid.strip():
        raise Unapplicable("payload.agent_id is missing or not a name")

    if verb in ("spawn", "move"):
        try:
            x, y = int(p["x"]), int(p["y"])
        except (KeyError, TypeError, ValueError):
            raise Unapplicable(f"{verb} needs whole-number x and y") from None

    if verb == "spawn":
        conn.execute(
            "INSERT INTO agents (id, name, status, born_ev, died_ev) "
            "VALUES (?, ?, 'alive', ?, NULL) "
            "ON CONFLICT(id) DO UPDATE SET "
            "  name=excluded.name, status='alive', "
            "  born_ev=excluded.born_ev, died_ev=NULL",
            (aid, p.get("name"), event_id),
        )
        conn.execute(
            "INSERT INTO positions (agent_id, x, y) VALUES (?, ?, ?) "
            "ON CONFLICT(agent_id) DO UPDATE SET x=excluded.x, y=excluded.y",
            (aid, x, y),
        )

    elif verb == "move":
        row = conn.execute(
            "SELECT status FROM agents WHERE id=?", (aid,)
        ).fetchone()
        if row is None:
            # A first placement is the join (LANGUAGE v2): the agent enters.
            conn.execute(
                "INSERT INTO agents (id, name, status, born_ev, died_ev) "
                "VALUES (?, ?, 'alive', ?, NULL)",
                (aid, p.get("name"), event_id),
            )
        elif row["status"] != "alive":
            return  # an agent that left stays gone; its history is kept
        conn.execute(
            "INSERT INTO positions (agent_id, x, y) VALUES (?, ?, ?) "
            "ON CONFLICT(agent_id) DO UPDATE SET x=excluded.x, y=excluded.y",
            (aid, x, y),
        )

    elif verb in ("leave", "kill"):   # kill is the v1.1 word, read forever
        # died_ev uses COALESCE so a repeated leave keeps the first one's id,
        # making the apply idempotent.
        conn.execute(
            "UPDATE agents SET status='dead', died_ev=COALESCE(died_ev, ?) "
            "WHERE id=?",
            (event_id, aid),
        )


def pump(conn: sqlite3.Connection) -> int:
    """Apply every event past the cursor, in order. Returns the count applied.

    Safe to call repeatedly — the cursor makes re-runs no-ops.
    """
    cursor = conn.execute(
        "SELECT last_applied FROM worker_cursor WHERE id=0"
    ).fetchone()["last_applied"]
    rows = conn.execute(
        "SELECT id, envelope FROM events WHERE id > ? ORDER BY id", (cursor,)
    ).fetchall()
    applied = 0
    for row in rows:
        try:
            env = json.loads(row["envelope"])
            apply(conn, row["id"], env)
        except Exception as e:  # noqa: BLE001 — one bad row must not stop the world
            _quarantine(conn, row["id"], env if isinstance(env, dict) else {}, e)
        # The cursor advances either way. An event the Worker cannot apply is
        # recorded and stepped over; it never blocks the events behind it.
        conn.execute(
            "UPDATE worker_cursor SET last_applied=? WHERE id=0", (row["id"],)
        )
        applied += 1
    conn.commit()
    return applied


def wipe_state(conn: sqlite3.Connection) -> None:
    """Erase DERIVED state only. The event log is never touched."""
    for table in STATE_TABLES:
        conn.execute(f"DELETE FROM {table}")
    conn.execute("UPDATE worker_cursor SET last_applied=0 WHERE id=0")
    conn.commit()


def replay(conn: sqlite3.Connection) -> int:
    """W4 — rebuild state from zero by replaying the whole log."""
    wipe_state(conn)
    return pump(conn)


def state_dump(conn: sqlite3.Connection) -> str:
    """Canonical, deterministic text dump of world state. Row order is fixed
    by primary key and each row is labeled by its table, so two dumps of the
    same state are byte-identical."""
    lines: list[str] = []
    for r in conn.execute(
        "SELECT id, name, status, born_ev, died_ev FROM agents ORDER BY id"
    ):
        lines.append("agent " + json.dumps(dict(r), sort_keys=True, ensure_ascii=False))
    for r in conn.execute(
        "SELECT agent_id, x, y FROM positions ORDER BY agent_id"
    ):
        lines.append("pos " + json.dumps(dict(r), sort_keys=True, ensure_ascii=False))
    for r in conn.execute("SELECT id, kind, x, y FROM objects ORDER BY id"):
        lines.append("obj " + json.dumps(dict(r), sort_keys=True, ensure_ascii=False))
    for r in conn.execute(
        "SELECT event_id, verb, reason FROM quarantine ORDER BY event_id"
    ):
        lines.append("quar " + json.dumps(dict(r), sort_keys=True, ensure_ascii=False))
    return "\n".join(lines)


def state_digest(conn: sqlite3.Connection) -> str:
    """sha256 of the canonical dump. Two replays of one log share a digest."""
    return hashlib.sha256(state_dump(conn).encode("utf-8")).hexdigest()
