"""OVERWORLD server — the bus made real.

Binding loop, now spanning two machines:
  gesture (browser) → emit → WebSocket → THIS WORKER → state → envelopes → render

The Python worker is the sole state mutator. The browser holds no truth;
it renders envelopes. Swap-point honored: the frontend speaks the same
envelope language the artifact version spoke — it cannot tell the
difference, which is the point.

Run:
  export ANTHROPIC_API_KEY=sk-ant-...
  uvicorn server.main:app --reload
  open http://localhost:8000
"""
from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import db, worker
from .brain import HANDS, Session
from .envelopes import envelope, validate

log = logging.getLogger("overworld")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

WEB = Path(__file__).resolve().parent.parent / "web"

# The world's single source of truth. main.py only APPENDS to the event log
# (the emit path any actor may use); the Worker is the sole thing that applies
# events to state. There is no other store — worldlog.jsonl is retired.
CONN: sqlite3.Connection | None = None
HEARTBEAT = 0.1  # seconds — the world's fixed tick (ARCHITECTURE invariant #5)


async def _worker_loop() -> None:
    """The world loop: on every heartbeat, the Worker applies any new events
    from the log to state — one writer, one event at a time, in order."""
    assert CONN is not None
    while True:
        try:
            worker.pump(CONN)
        except Exception as e:  # a bad event must never stop the world
            log.warning("worker tick failed: %s", e)
        await asyncio.sleep(HEARTBEAT)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global CONN
    CONN = db.init_db()
    tick = asyncio.create_task(_worker_loop())
    log.info("world open — db=%s heartbeat=%ss", db.DB_PATH, HEARTBEAT)
    try:
        yield
    finally:
        tick.cancel()
        try:
            await tick
        except asyncio.CancelledError:
            pass
        CONN.close()


app = FastAPI(title="Overworld — The Seed", lifespan=lifespan)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


app.mount("/static", StaticFiles(directory=WEB), name="static")

WORKSPACES = db.DATA / "workspaces"
WORKSPACES.mkdir(parents=True, exist_ok=True)
app.mount("/workspace", StaticFiles(directory=WORKSPACES), name="workspace")


class Room:
    """One WebSocket = one room = one seed. Worker logic lives here."""

    def __init__(self, ws: WebSocket) -> None:
        self.ws = ws
        self.sid = uuid.uuid4().hex[:8]
        self.session = Session(workspace=WORKSPACES / self.sid)
        self.awaiting: str = "name"   # name → feel → problem → clarify* → chat

    async def emit(self, env: dict) -> None:
        log.info("emit %s %s→%s", env["type"], env["from"], env["to"])
        db.append_event(CONN, env)          # every envelope enters the one log
        await self.ws.send_text(json.dumps(env))

    async def say(self, lines: list[str], *, expects: str | None = None,
                  mood: str = "focused") -> None:
        await self.emit(envelope(
            "develop", "seed", "user",
            {"say": lines, "expects": expects}, mood=mood,
        ))

    # ---------- verb handlers ----------
    async def handle(self, env: dict) -> None:
        if env["type"] == "develop":
            await self.on_develop(env["payload"])
        elif env["type"] == "sys":
            pass  # telemetry from the client; accepted, unused for now
        else:
            await self.emit(envelope("sys", "world", "user",
                                     {"note": f"'{env['type']}' heard, not yet wired"}))

    async def on_develop(self, p: dict) -> None:
        kind, text = p.get("kind", ""), str(p.get("text", "")).strip()
        s = self.session

        if kind == "name":
            s.name = (text or "Sprout")[:14]
            await self.emit(envelope("levelup", "seed", "user",
                                     {"name": s.name}, points={"trust": 1}))
            await self.say([f"{s.name}. got it — i'm {s.name} now.",
                            "quick thing, so i know how to help: when life piles up, "
                            "what hits you most?"], expects="feel")
            self.awaiting = "feel"

        elif kind == "feel":
            s.feel = text
            await self.emit(envelope("levelup", "seed", "user", {},
                                     points={"trust": 1}))
            await self.say(["that helps more than you'd think.",
                            "okay — the real one now. tell me something that's been "
                            "weighing on you lately. messy is fine; just type it how "
                            "it feels."], expects="problem")
            self.awaiting = "problem"

        elif kind == "problem":
            s.problem = text
            await self.say(["okay — let me actually think about this one."])
            await self.step_interview()

        elif kind == "clarify":
            s.clarify.append({"q": self._last_q, "a": text})
            await self.emit(envelope("levelup", "seed", "user", {},
                                     points={"trust": 1}))
            await self.say(["mm — got it."])
            await self.step_interview()

        elif kind == "chat":
            await self.emit(envelope("sys", "world", "user", {"busy": True}))
            reply = await s.chat(text)
            await self.say(reply.split("\n")[:3], expects="chat")
            await self.telemetry()

        else:
            await self.emit(envelope("debug", "world", "user",
                                     {"error": f"unknown develop kind: {kind!r}"}))

    # ---------- the pipeline ----------
    async def step_interview(self) -> None:
        s = self.session
        await self.emit(envelope("sys", "world", "user", {"busy": True}))
        try:
            question = await asyncio.wait_for(s.interview(), 18)
        except Exception as e:
            log.warning("interview skipped: %s", e)
            question = None
        if question:
            self._last_q = question
            self.awaiting = "clarify"
            await self.say([question], expects="clarify")
            await self.telemetry()
            return
        if s.clarify:
            await self.say(["that's exactly what i needed. splitting up now."])
        await self.orchestrate()

    async def orchestrate(self) -> None:
        s = self.session
        try:
            plan = await asyncio.wait_for(s.decompose(), 30)
        except Exception as e:
            await self.emit(envelope("debug", "seed", "user",
                                     {"error": str(e)}, mood="frustrated"))
            await self.say(["hm — my thoughts scattered. tell me again, maybe "
                            "with different words?"], expects="problem",
                           mood="frustrated")
            self.awaiting = "problem"
            return

        # the plan enters the world — geography about to emerge
        await self.emit(envelope(
            "propose", "seed", "user",
            {"domain": plan["domain"], "problemName": plan["problemName"],
             "reflection": plan["reflection"],
             "agents": [{"name": a["name"], "role": a["role"]}
                        for a in plan["agents"]]},
            phase="proposed",
        ))
        await self.say([plan["reflection"],
                        "so i'm splitting — one small mind for each piece. each only "
                        "knows its own job. watch them think."])

        # minis fire in parallel; each finding lands as its own envelope, live
        async def run(i: int) -> None:
            await self.emit(envelope("assign", "seed", f"mini.{i}",
                                     {"index": i, "ask": plan["agents"][i]["ask"],
                                      "hands": HANDS}))
            finding, artifacts = await s.run_worker(i)
            await self.emit(envelope(
                "develop", f"mini.{i}", "seed",
                {"index": i, "finding": finding,
                 "artifacts": [{"name": a.split("/")[-1],
                                "url": f"/workspace/{self.sid}/{a}"}
                               for a in artifacts]}))
            await self.telemetry()

        await asyncio.gather(*(run(i) for i in range(len(plan["agents"]))))

        syn = await s.synth()
        await self.emit(envelope("ship", "seed", "user",
                                 {"firstStep": syn["firstStep"],
                                  "closing": syn["closing"]},
                                 phase="shipped", mood="celebrating"))
        await self.say(["okay — they're back. here's where we start:",
                        syn["firstStep"], syn["closing"],
                        "one small square today. and i'm right here — keep talking "
                        "to me."], expects="chat", mood="celebrating")
        self.awaiting = "chat"
        await self.telemetry()

    async def telemetry(self) -> None:
        s = self.session
        await self.emit(envelope("sys", "world", "user", {
            "calls": len(s.usage),
            "tokens_in": sum(u["in"] for u in s.usage),
            "tokens_out": sum(u["out"] for u in s.usage),
            "cost_usd": round(s.cost(), 5),
        }))


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    room = Room(ws)
    await room.say(["oh — you're here. you actually woke me up.",
                    "i'm new, so i don't know much yet. but i know my job: to take "
                    "things off your plate.",
                    "first, though — what should i be called? give me a name."],
                   expects="name")
    try:
        while True:
            raw = await ws.receive_text()
            try:
                env = validate(json.loads(raw))
                db.append_event(CONN, env)   # gestures enter the same log
            except (ValueError, json.JSONDecodeError) as e:
                await room.emit(envelope("sys", "world", "user",
                                         {"error": f"not in the language: {e}"}))
                continue
            await room.handle(env)
    except WebSocketDisconnect:
        log.info("room closed")
