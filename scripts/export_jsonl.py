"""Read-only export: the event log (SQLite `events`) → JSONL, one envelope per
line. Replaces the retired dual-write to `data/world_log.jsonl`; the log now
lives in the database, and this projects it back out for datasets or analysis.

Never writes state or the log — a pure reader.

    python -m scripts.export_jsonl [out_path]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from server.db import DB_PATH, connect


def export(out: Path) -> int:
    conn = connect(DB_PATH)
    n = 0
    with out.open("w", encoding="utf-8") as f:
        for row in conn.execute("SELECT id, envelope FROM events ORDER BY id"):
            env = json.loads(row["envelope"])
            f.write(json.dumps({"id": row["id"], **env}, ensure_ascii=False) + "\n")
            n += 1
    return n


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DB_PATH.parent / "world_log.jsonl"
    count = export(out)
    print(f"exported {count} events → {out}")
