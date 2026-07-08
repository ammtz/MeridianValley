"""The world log. Every envelope that crosses the bus is appended here —
in and out, forever. This is not logging; it is the dataset.

The closed lexicon makes each line a labeled episode: verb, from→to,
story, phase, points, timestamp. The delegation bandit, verb process
evolution, and eventual fine-tunes all eat from this file.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parent.parent / "data"
DATA.mkdir(exist_ok=True)
LOG = DATA / "world_log.jsonl"

_lock = threading.Lock()


def log(env: dict[str, Any], direction: str, session: str) -> None:
    rec = {"logged_at": int(time.time() * 1000), "dir": direction,
           "session": session, **env}
    line = json.dumps(rec, ensure_ascii=False)
    with _lock, LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
