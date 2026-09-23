# FIRST WORLD — spec

**Principle (DECISIONS #10):** adopt what is proven, remake only what is
necessary, create everywhere else. Working is the goal.

Meridian Valley's first world stands on two mature MIT-licensed projects,
joined by a bridge of our own:

| Half | Project | What it gives us |
|---|---|---|
| Running | [Paperclip](https://github.com/paperclipai/paperclip) → fork `ammtz/paperclip` | Agents as employees: org chart, heartbeats, per-agent budgets, board approvals, append-only activity log |
| Watching | [Pixel Agents](https://github.com/pixel-agents-hq/pixel-agents) → fork `ammtz/pixel-agents` | Each agent as a pixel character in an office: walks, types, reads, raises a bubble when it needs the human |
| Glue | `bridge/` in this repo | Paperclip employees appear as named characters in the office |

Both foundations already run in production for their users, so the first
world works on day one and every later story upgrades a running system.
Our effort goes where nothing exists yet: the bridge, the shared log, and
the world built on top.

---

## Slices — one session each, in order

### F0 · Fork (Product Owner, 2 clicks)
Fork both repos into `ammtz` on GitHub, then add them to the Claude session.
Agents cannot fork outside `ammtz/MeridianValley` and `ammtz/Calibraton3000`.
**Done when** both forks exist and a session can push to them.

### F1 · Side by side, zero code (Builder, on the PC)
The cheapest possible world. Paperclip's `claude_local` adapter runs Claude
Code, and Pixel Agents installs Claude Code hooks that fire on *every* Claude
session on the machine. Running both may already be the whole first world.

1. Node 24.11+ (Paperclip's floor; Pixel Agents needs 20+).
2. `npx paperclipai onboard --yes` → UI at `http://localhost:3100`, embedded
   Postgres, trusted loopback mode. Create a company, hire a CEO on
   `claude_local`.
3. `npx pixel-agents` in a second terminal. Open the printed URL **with its
   `?token=`** and approve the hook install (it edits `~/.claude/settings.json`).
   Turn on **Settings → Watch All Sessions**.
4. Wake the CEO (Paperclip UI, or `POST /api/agents/:id/wakeup`).

**Done when** the CEO's run shows as a character typing in the office, and a
screenshot is committed to `docs/first-world/F1.png`.
**If it fails:** the likely cause is Paperclip starting Claude in its own
workspace folders, which Pixel Agents does not adopt. Write down exactly what
you saw, then go to F2, which does not depend on it.

### F2 · The bridge (Builder)
A small Python service, `bridge/`, stdlib plus `httpx`. It **polls
Paperclip** and **posts Claude-shaped hook events to Pixel Agents**. Neither
upstream project is changed.

**Pixel Agents side (verified 2026-09-23 against pixel-agents@latest):**
- Live servers register at `~/.pixel-agents/servers/<pid>-<port>.json` as
  `{port, pid, token, startedAt, servesSpa, protocol}`. Skip an entry whose
  `pid` is dead; that is what its own hook script does.
- Deliver with `POST http://127.0.0.1:<port>/api/hooks/claude`,
  `Authorization: Bearer <token>`, and a JSON body in Claude Code's hook
  shape: `hook_event_name`, `session_id`, `cwd`, and `tool_name`,
  `tool_input`, `tool_use_id` for tool events. Its `normalizeHookEvent` lives
  in `server/src/providers/hook/claude/claude.ts`. **Read it before writing
  the mapper.** The exact field names are its contract, not this doc's.

**Paperclip side (route names verified in @paperclipai/server; request and
response shapes NOT verified):**
- `GET /api/companies/:companyId/agents`: who works here (name, role).
- `GET /api/companies/:companyId/heartbeat-runs`: runs and their status.
- `GET /api/heartbeat-runs/:runId/events`: what a run is doing.
- `GET /api/companies/:companyId/approvals`: pending board decisions.
- A `live-events` websocket exists. Poll first (every 2 s) and switch only if
  polling proves too slow.
- Check whether loopback mode needs auth. `docs/api/` in the fork documents
  the API.

**Mapping.** Use one character per Paperclip agent, with
`session_id = "paperclip-<agentId>"`:

| Paperclip | Hook event sent |
|---|---|
| agent seen for the first time | `SessionStart` |
| run event that is a tool call start / end | `PreToolUse` / `PostToolUse` |
| approval pending for that agent | `PermissionRequest` |
| run finished | `Stop` |
| agent terminated or paused | `SessionEnd` |

Keep the mapper a pure function (`paperclip_state_before, paperclip_state_after
→ [hook_event]`) so it can be tested without either server running.

**Done when**
- `python -m bridge.demo` runs a Paperclip agent on the **process or bash
  adapter**, so no API key is needed, and it walks, types and raises a
  permission bubble in the office.
- Mapper unit tests pass offline.
- A screenshot is committed to `docs/first-world/F2.png`.

### F3 · Names on the characters (Builder, in `ammtz/pixel-agents`)
First change to a fork: the character label shows the Paperclip agent's name
and role (e.g. "Ada · CEO"). Find where the webview labels characters and let
a hook payload carry a display name. Keep the change small and upstreamable.
Offer it back as a PR to `pixel-agents-hq`.
**Done when** the office shows who is who without a click.

### F4 · Upgrade 1: one log (Builder)
Only after F2 works. Everything the bridge forwards is also appended to this
repo's SQLite `events` table as a world-tier envelope (`spawn` on
`SessionStart`, `kill` on `SessionEnd`; work events per `PROTOCOL.md`). Now
running and watching share one replayable record, which is the original
Meridian Valley idea on a base that already works.
**Done when** the replay proof rebuilds the office timeline from the log alone.

---

## Rules for the builder
- **Adopt before building.** If an upstream feature already does the job, use
  it. Remake only what blocks the world; create only what does not exist.
- **Don't patch upstream unless a slice says to.** Glue lives in `bridge/`.
  Fork changes are small, isolated commits that could go back upstream.
- **Don't send the Pixel Agents token anywhere.** It is a bearer capability,
  and the bridge reads it only from the local registry file.
- **Record what you did not do.** A slice that half-works says which half,
  on its Notion task row.

## What this supersedes
`ARCHITECTURE.md`'s stack table (PixiJS, Tiled, subprocess agents) and Epics
2–3 in `BACKLOG.md` are paused, not deleted. Paperclip replaces the
orchestrator, and Pixel Agents replaces the renderer. The binding loop and
DECISIONS #2 (Worker as sole writer) do **not** hold in F1–F3: Paperclip's
database is the writer. F4 is the point where Meridian Valley's own log comes
back into the loop.
