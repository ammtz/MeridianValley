"""The Seed's mind. Sonnet orchestrates; Haiku minis each run one narrow
job in parallel, each in its own tiny context. Server-side, real key,
no artifact tricks.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any

from pathlib import Path
from shutil import which

from anthropic import AsyncAnthropic

try:  # real hands: agent SDK drives the Claude Code CLI
    from claude_agent_sdk import ClaudeAgentOptions, query as sdk_query
    HANDS = which("claude") is not None
except ImportError:  # pragma: no cover
    HANDS = False

MODEL_ORCH = os.environ.get("OVERWORLD_MODEL_ORCH", "claude-sonnet-4-6")
MODEL_WORKER = os.environ.get("OVERWORLD_MODEL_WORKER", "claude-haiku-4-5-20251001")

_client: AsyncAnthropic | None = None


def client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic()  # reads ANTHROPIC_API_KEY
    return _client


def _json_block(raw: str) -> dict[str, Any] | None:
    s = re.sub(r"```json|```", "", raw or "", flags=re.I).strip()
    m = re.search(r"\{[\s\S]*\}", s)
    if not m:
        return None
    for candidate in (m.group(0), re.sub(r",\s*([}\]])", r"\1", m.group(0))):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


async def _ask(model: str, system: str, user_or_msgs, max_tokens: int) -> tuple[str, dict]:
    messages = user_or_msgs if isinstance(user_or_msgs, list) else [
        {"role": "user", "content": user_or_msgs}
    ]
    resp = await client().messages.create(
        model=model, max_tokens=max_tokens, system=system, messages=messages
    )
    text = "\n".join(b.text for b in resp.content if b.type == "text")
    usage = {"in": resp.usage.input_tokens, "out": resp.usage.output_tokens, "model": model}
    return text, usage


class Session:
    """One human, one seed. Holds interview context and chat history."""

    def __init__(self, workspace: Path | None = None) -> None:
        self.name: str = "???"
        self.feel: str = ""
        self.problem: str = ""
        self.clarify: list[dict[str, str]] = []   # [{"q":..., "a":...}]
        self.plan: dict[str, Any] | None = None
        self.findings: list[str] = []
        self.artifacts: list[list[str]] = []      # per-mini relative file paths
        self.chat_log: list[dict[str, str]] = []
        self.usage: list[dict] = []
        self.workspace = workspace

    # ---------- context ----------
    def interview_ctx(self) -> str:
        s = (
            f'When asked what hits them most when life piles up, they chose: "{self.feel}".\n'
            f'Their problem, in their own words:\n"""{self.problem}"""'
        )
        for c in self.clarify:
            s += f'\nYou asked: "{c["q"]}" — they answered: "{c["a"]}"'
        return s

    # ---------- phases ----------
    async def interview(self) -> str | None:
        """Return one sharp clarifying question, or None if ready."""
        if len(self.clarify) >= 2:
            return None
        sys = (
            "You are a brand-new personal helper creature interviewing your human about a "
            "problem they just shared. Decide: do you NEED one more piece of information "
            "before splitting this problem into concrete sub-tasks for specialist helpers, "
            "or do you already know enough? Bias strongly toward knowing enough — only ask "
            "if one specific detail would genuinely change the plan. Voice: warm, plain-"
            "spoken, quietly perceptive."
        )
        user = (
            self.interview_ctx()
            + '\nReturn ONLY JSON: {"ready":true} if you know enough, or '
            '{"ask":"ONE short, sharp clarifying question"} if a single detail would '
            "really change the plan."
        )
        raw, u = await _ask(MODEL_ORCH, sys, user, 200)
        self.usage.append(u)
        o = _json_block(raw)
        if o and o.get("ask") and not o.get("ready"):
            return str(o["ask"])[:220]
        return None

    async def decompose(self) -> dict[str, Any]:
        sys = (
            "You are the orchestrator of a tiny swarm of single-purpose helper agents. "
            "You read a person's real-life problem and split it into 3 or 4 narrow, "
            "independent sub-tasks, each handled by one specialist you are creating right "
            "now. For each specialist you write the EXACT, self-contained question to ask "
            "it — include only the sliver of context that specialist needs, nothing else. "
            "Voice: warm, plain-spoken, quietly perceptive. Not baby-talk, not saccharine."
        )
        user = "\n".join([
            self.interview_ctx(),
            "Return ONLY a JSON object of this exact shape:",
            '{"domain":"2-4 words naming the life area","problemName":"<=5 word title",'
            '"reflection":"1-2 sentences proving you understood THIS specific problem — '
            'name the real tension in it, warm but sharp","agents":[{"name":"one short '
            'creature-name","role":"2-3 word specialty","ask":"the exact focused '
            'question/instruction for this specialist, fully self-contained, only the '
            'context it needs"}]}',
            "Use 3 or 4 agents. Each ask must stand alone — a narrow specialist with no "
            "other context could answer it. Output only the JSON.",
        ])
        raw, u = await _ask(MODEL_ORCH, sys, user, 900)
        self.usage.append(u)
        o = _json_block(raw)
        if not o or not o.get("agents"):
            raise ValueError("decompose returned no usable plan")
        o["domain"] = str(o.get("domain", "your life"))[:40]
        o["problemName"] = str(o.get("problemName", "the first weight"))[:48]
        o["reflection"] = str(o.get("reflection", ""))
        o["agents"] = [
            {
                "name": str(a.get("name", "?"))[:12],
                "role": str(a.get("role", "helper"))[:22],
                "ask": str(a.get("ask", a.get("task", "")))[:500],
            }
            for a in o["agents"][:4]
            if a.get("ask") or a.get("task")
        ]
        if not o["agents"]:
            raise ValueError("plan had no workable agents")
        self.plan = o
        self.findings = [""] * len(o["agents"])
        self.artifacts = [[] for _ in o["agents"]]
        return o

    async def run_worker(self, i: int) -> tuple[str, list[str]]:
        """THE SWAP-POINT. Sentence-producing minis were the hollowness;
        this is where hands got attached. Returns (finding, artifact paths
        relative to this mini's workspace dir)."""
        ag = self.plan["agents"][i]
        if HANDS and self.workspace is not None:
            try:
                return await asyncio.wait_for(self._run_worker_hands(i, ag), 180)
            except Exception as e:  # hands failed — degrade to voice
                self.usage.append({"in": 0, "out": 0, "model": "sdk-error",
                                   "note": str(e)[:120]})
        return await self._run_worker_voice(i, ag)

    async def _run_worker_hands(self, i: int, ag: dict) -> tuple[str, list[str]]:
        wdir = self.workspace / f"{i}_{ag['name'].lower().replace(' ', '_')}"
        wdir.mkdir(parents=True, exist_ok=True)
        opts = ClaudeAgentOptions(
            model=MODEL_WORKER,
            cwd=str(wdir),
            allowed_tools=["Read", "Write", "Edit"],
            permission_mode="acceptEdits",
            max_turns=8,
            system_prompt=(
                f"You are {ag['name']}, a single-purpose specialist whose entire world "
                f"is: {ag['role']}. You have a working directory and file tools. "
                "Your job: don't just answer — PRODUCE. Create at least one real, "
                "useful file in the working directory (a checklist.md, a draft, a "
                "template, a plan, a script — whatever genuinely serves the task). "
                "Then reply with 1-2 concrete sentences summarizing what you made "
                "and your sharpest recommendation. No preamble, no hedging."
            ),
        )
        summary, cost = "", 0.0
        async for msg in sdk_query(prompt=ag["ask"], options=opts):
            kind = type(msg).__name__
            if kind == "AssistantMessage":
                for block in getattr(msg, "content", []):
                    if hasattr(block, "text"):
                        summary = block.text  # keep last text block
            elif kind == "ResultMessage":
                summary = getattr(msg, "result", None) or summary
                cost = getattr(msg, "total_cost_usd", 0.0) or 0.0
        self.usage.append({"in": 0, "out": 0, "model": "agent-sdk",
                           "cost_usd": cost})
        artifacts = sorted(
            str(p.relative_to(self.workspace))
            for p in wdir.rglob("*") if p.is_file()
        )
        finding = (summary or "").strip()[:400] or "(built quietly.)"
        self.findings[i] = finding
        self.artifacts[i] = artifacts
        return finding, artifacts

    async def _run_worker_voice(self, i: int, ag: dict) -> tuple[str, list[str]]:
        sys = (
            f"You are {ag['name']}, a single-purpose specialist whose entire world is: "
            f"{ag['role']}. You think about ONLY this one job. Answer in 1-2 concrete, "
            "specific, actionable sentences — no preamble, no caveats, no restating the "
            "question, no hedging. Just your sharpest contribution."
        )
        try:
            raw, u = await asyncio.wait_for(_ask(MODEL_WORKER, sys, ag["ask"], 300), 25)
            self.usage.append(u)
            finding = (raw or "").strip() or "(quiet for now.)"
        except Exception:
            finding = "(this one got stuck — i'll send it back in later.)"
        self.findings[i] = finding
        return finding, []

    async def synth(self) -> dict[str, str]:
        sys = (
            "You are the orchestrator again. Your specialists have each reported back. "
            "Weave their findings into the single first concrete move the person should "
            "make right now. Voice: warm, plain-spoken, perceptive. Concrete over comforting."
        )
        lines = [
            f"- {ag['name']} ({ag['role']}): {self.findings[i] or '(no answer)'}"
            for i, ag in enumerate(self.plan["agents"])
        ]
        user = "\n".join([
            "The person's problem:",
            f'"""{self.problem}"""',
            "What each specialist found:",
            *lines,
            "Return ONLY a JSON object of this exact shape:",
            '{"firstStep":"1-2 sentences: the very first concrete move, combining the '
            "specialists' work, specific and real\",\"closing\":\"one short, grounded "
            'sentence: you will grow to take more of this off their hands"}',
            "Output only the JSON.",
        ])
        try:
            raw, u = await asyncio.wait_for(_ask(MODEL_ORCH, sys, user, 500), 25)
            self.usage.append(u)
            o = _json_block(raw)
            if o and o.get("firstStep"):
                return {"firstStep": str(o["firstStep"]), "closing": str(o.get("closing", ""))}
        except Exception:
            pass
        lead = self.plan["agents"][0]
        return {
            "firstStep": f"we start with {lead['name']}: {self.findings[0] or 'the first small piece'}",
            "closing": "this is just the first sprout — it grows.",
        }

    async def chat(self, text: str) -> str:
        self.chat_log.append({"role": "user", "content": text})
        self.chat_log = self.chat_log[-16:]
        p = self.plan or {}
        found = " | ".join(f for f in self.findings if f) or "(still settling in)"
        sys = (
            f"You are {self.name}, a newly-hatched personal agent who just split into "
            f"mini-specialist helpers for your human. Their problem: \"{self.problem}\". "
            f"Your plan: domain \"{p.get('domain', '?')}\", titled \"{p.get('problemName', '?')}\". "
            f"Your specialists reported: {found}. Stay fully in character: warm, plain-"
            "spoken, a little playful, VERY concise (1-3 short sentences). Be concretely "
            "useful about their problem and next moves. Never break character, never "
            "mention being an AI model."
        )
        try:
            raw, u = await asyncio.wait_for(
                _ask(MODEL_ORCH, sys, list(self.chat_log), 250), 25
            )
            self.usage.append(u)
            reply = (raw or "").strip() or "…"
        except Exception:
            reply = "(i drifted off for a second — say that again?)"
        self.chat_log.append({"role": "assistant", "content": reply})
        return reply

    def cost(self) -> float:
        rates = {MODEL_ORCH: (3, 15), MODEL_WORKER: (1, 5)}  # $/M in, out
        total = 0.0
        for u in self.usage:
            if "cost_usd" in u:
                total += u["cost_usd"]
                continue
            rin, rout = rates.get(u["model"], (3, 15))
            total += (u["in"] * rin + u["out"] * rout) / 1e6
        return total
