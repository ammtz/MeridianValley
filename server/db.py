"""W1 — the world's persistence: one SQLite file, an append-only event log
plus the derived state tables. Running this module creates the database.

    python -m server.db init [path]

Laws honored (see ARCHITECTURE.md):
- `events` is append-only; its rowid is the world's single total order.
- state tables (`agents`, `positions`, `objects`) are DERIVED — they can be
  wiped and rebuilt by replaying `events` (see server/worker.py). They are
  never the source of truth; the log is.
- appending to the log is the "emit" path any agent or human may use; it does
  NOT touch state. Only the Worker mutates state (the one-writer invariant).
- one SQLite file = one source of truth, matching one-writer physically.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parent.parent / "data"
# The one SQLite file. Overridable via OVERWORLD_DB so proofs and tests can
# isolate (a mock-to-live seam) without touching the real world.
DB_PATH = Path(os.environ.get("OVERWORLD_DB", DATA / "world.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,  -- total order of the world
    verb     TEXT    NOT NULL,
    envelope TEXT    NOT NULL,                    -- full JSON envelope, verbatim
    ts       INTEGER NOT NULL                     -- ms since epoch, from the envelope
);

CREATE TABLE IF NOT EXISTS agents (
    id      TEXT PRIMARY KEY,     -- agent identity
    name    TEXT,
    status  TEXT NOT NULL,        -- 'alive' | 'dead'
    born_ev INTEGER,              -- event id that spawned it
    died_ev INTEGER               -- event id that killed it (NULL while alive)
);

CREATE TABLE IF NOT EXISTS positions (
    agent_id TEXT PRIMARY KEY,    -- exactly one position per agent
    x        INTEGER NOT NULL,
    y        INTEGER NOT NULL
);

-- Reserved for non-agent world entities (props, resources). No verb writes it
-- yet; the table exists so the schema is whole (BACKLOG W1).
CREATE TABLE IF NOT EXISTS objects (
    id   TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    x    INTEGER NOT NULL,
    y    INTEGER NOT NULL
);

-- The Worker's cursor: the highest event id already applied to state. Lets the
-- single writer resume without re-applying, and makes replay simply "reset to
-- 0, wipe derived tables, pump."
CREATE TABLE IF NOT EXISTS worker_cursor (
    id           INTEGER PRIMARY KEY CHECK (id = 0),  -- single-row table
    last_applied INTEGER NOT NULL
);
"""

# Derived tables, in the order a state dump reads them. The log is NOT here —
# it is never wiped.
STATE_TABLES = ("agents", "positions", "objects")


def connect(path: Path | str = DB_PATH) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: Path | str = DB_PATH) -> sqlite3.Connection:
    """Create the database and return an open connection. Idempotent."""
    conn = connect(path)
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT OR IGNORE INTO worker_cursor (id, last_applied) VALUES (0, 0)"
    )
    conn.commit()
    return conn


def append_event(conn: sqlite3.Connection, env: dict[str, Any]) -> int:
    """The single append path into the log. Returns the new event id.

    This is the "emit" — it records intent. It deliberately does NOT touch
    state; that is the Worker's sole job (server/worker.py).
    """
    cur = conn.execute(
        "INSERT INTO events (verb, envelope, ts) VALUES (?, ?, ?)",
        (
            env["type"],
            json.dumps(env, ensure_ascii=False, sort_keys=True),
            int(env.get("ts", 0)),
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "init"
    target = Path(sys.argv[2]) if len(sys.argv) > 2 else DB_PATH
    if cmd != "init":
        print(f"unknown command: {cmd!r} (try: init)")
        sys.exit(1)
    conn = init_db(target)
    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
    ]
    print(f"created {target}")
    print("tables:", ", ".join(tables))
