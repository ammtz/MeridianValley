# First World — System Architecture

| | |
|---|---|
| **Status** | Approved for build · v2 · 2026-09-23 |
| **Principle** | Adopt what is proven. Remake only what is necessary. Create everywhere else. (DECISIONS #10) |
| **Foundations** | `ammtz/paperclip-2` @ `f557599` · `ammtz/pixel-agents-2` @ `3537e14` (v1.4.1) |
| **Supersedes** | v1 of this document (the Python polling bridge) |

Every claim marked **[v]** was verified against the fork source at the commits
above, with a file reference. Anything unmarked is a design choice. Anything
marked **[?]** is an open fact the named milestone must settle before building
on it.

---

## 1. Goal

A **working world on day one**: a company of AI agents that do real work, which a
person can watch and direct from a pixel office.

| # | Goal | Measured by |
|---|---|---|
| G1 | Paperclip agents appear and animate in the office | M1 acceptance |
| G2 | One character per *employee*, labelled with name and role, and stable across heartbeats | M2 acceptance |
| G3 | The office shows the company's state: who is running, who waits on the board, who is out of budget | M3 acceptance |
| G4 | The human can act from the office: approve or reject a board request by clicking the bubble | M4 acceptance |

**Non-goals for this epic:** multi-machine deployment; non-local Paperclip
modes; changing Paperclip's core; our own renderer, orchestrator, or event
store.

---

## 2. System context

```
                    ┌──────────────────────── the human ────────────────────────┐
                    │ board decisions (Paperclip UI)          watches + clicks  │
                    ▼                                           (office, M4)    ▼
┌───────────────────────────────────────┐          ┌─────────────────────────────────────┐
│ PAPERCLIP  (ammtz/paperclip-2)        │          │ PIXEL AGENTS  (ammtz/pixel-agents-2)│
│ system of record                      │          │ projection — holds no business state│
│                                       │          │                                     │
│  org chart · issues · approvals ·     │  (B) WS  │  ┌───────────────────────────────┐  │
│  budgets · heartbeat scheduler        │─────────►│  │ PaperclipSource   ◄── NEW     │  │
│  Postgres + append-only activity log  │  live    │  └──────────────┬────────────────┘  │
│                                       │  events  │                 │ AgentEvent        │
│  heartbeat ─► claude_local adapter    │          │  ┌──────────────▼────────────────┐  │
│                 │ spawns `claude`     │  (C) REST│  │ AgentRuntime · SessionRouter  │  │
│                 │ env: PAPERCLIP_*    │◄─────────│  │ AgentStateStore (unchanged)   │  │
└─────────────────┼─────────────────────┘ approve  │  └──────────────┬────────────────┘  │
                  ▼                        (M4)    │                 │ WS / postMessage  │
        ┌──────────────────┐   (A) hook POST       │           webview office            │
        │ Claude Code proc │──────────────────────►│  /api/hooks/claude  (existing)      │
        │ + claude-hook.js │  + paperclip identity └─────────────────────────────────────┘
        └──────────────────┘    (enriched, M2)
```

**Three channels, and one owner each:**

| Ch. | Carries | Direction | Existing or new |
|---|---|---|---|
| **A** | *What an agent is doing right now* (tool calls, turns, permission prompts) | Claude Code → Pixel Agents | Existing hook path. M2 adds identity. |
| **B** | *Who the agent is and what the company is doing* (runs, status, approvals, budgets) | Paperclip → Pixel Agents (pull) | New `PaperclipSource` in the Pixel Agents fork |
| **C** | *The human acting from the office* | Pixel Agents → Paperclip REST | New, M4 |

---

## 3. Architecture decisions

**AD-1 · Paperclip is the system of record. Pixel Agents is a stateless projection.**
Paperclip already has an append-only, immutable activity log of every mutation,
including approve and reject decisions (`docs/api/activity.md`) **[v]**. We do not
run a second event store for the first world. This repo's SQLite log
(`server/`) is frozen, not deleted. It returns only if we need to replay
something Paperclip does not record (§10).

**AD-2 · Pull, not push, across the Paperclip boundary.**
A Paperclip plugin cannot reach Pixel Agents: plugin `http.fetch` rejects
loopback and private IPs (`server/src/services/plugin-host-services.ts:103–128`)
**[v]**, and Pixel Agents listens on 127.0.0.1. Pixel Agents therefore
subscribes to Paperclip's live-event socket
`ws://<host>:3100/api/companies/:companyId/events/ws`
(`server/src/realtime/live-events-ws.ts:92–93`) **[v]**. In `local_trusted`
mode the socket needs no token (`:139–141`) **[v]**. This also keeps the
Paperclip fork free of changes.

**AD-3 · The integration lives inside the Pixel Agents fork, in TypeScript.**
Pixel Agents already expects this extension. Its provider file carries a
`TODO(provider type taxonomy): … StreamProvider` for exactly this case
(`core/src/provider.ts:150`) **[v]**. `PaperclipSource` normalizes into the
existing `AgentEvent` union, so `AgentRuntime`, `AgentStateStore`, the wire
protocol and the webview stay untouched. v1's Python bridge is dropped: it
would have remade, in another language and outside the runtime, the event
normalization Pixel Agents already has.

**AD-4 · Identity is the Paperclip `agentId`, carried in through the environment.**
`claude_local` spawns Claude with `PAPERCLIP_AGENT_ID`, `PAPERCLIP_COMPANY_ID`
and `PAPERCLIP_RUN_ID` set (`packages/adapters/claude-local/src/server/execute.ts:218–219`;
`packages/adapter-utils/src/server-utils.ts:3108–3122`) **[v]**. The Pixel
Agents hook script is a child of that Claude process, so it inherits those
variables. The M2 change: the hook script copies them into the payload it
posts. That joins channel A to channel B with no guessing on working
directory or session id.

**AD-5 · One character per employee, not per session.**
Each heartbeat can start or resume a different Claude session, so a Claude
`session_id` is not a stable identity. `SessionRouter` gains an alias: any
session whose payload carries `paperclip.agentId = X` routes to agent X's
character. The first such session creates the character. Later ones attach
to it.

**AD-6 · Reuse the team model for the org chart. No protocol change.**
Pixel Agents already ships `agentTeamInfo {teamName, agentName, isTeamLead,
leadAgentId}` (`core/asyncapi.yaml:402–420`) **[v]**. That maps directly onto
Paperclip's `companies` and `agents.{name, role, title, reportsTo}`
(`packages/db/src/schema/agents.ts:22–27`) **[v]**:

| Paperclip | → | Pixel Agents |
|---|---|---|
| company name | → | `teamName` |
| `agent.name` · `agent.title ?? agent.role` | → | `agentName` (e.g. "Ada · CEO") |
| agent with no `reportsTo` | → | `isTeamLead` |
| `reportsTo` | → | `leadAgentId` (the manager's character) |

One webview line changes: the overlay shows `LEAD` instead of the name for
leads (`webview-ui/src/office/components/ToolOverlay.tsx:205`) **[v]**. Show
the name there too.

**AD-7 · Fork hygiene.**
`paperclip-2` carries **no changes** and tracks upstream. `pixel-agents-2`
keeps its changes on `meridian/*` branches, each one small, tested, and written
to be offered upstream. This repo holds the product: architecture, runbook,
config, and the world we build on top.

---

## 4. Contracts

### 4.1 Channel A — Pixel Agents hook ingress (existing) **[v]**
- `POST http://127.0.0.1:<port>/api/hooks/claude`, `Authorization: Bearer <token>`.
- Live servers register in `~/.pixel-agents/servers/<pid>-<port>.json` as
  `{port, pid, token, startedAt, servesSpa, protocol}`.
- The body is Claude Code's hook JSON, normalized by `normalizeHookEvent` in
  `server/src/providers/hook/claude/claude.ts:132–244`.
- **M2 addition.** When `PAPERCLIP_AGENT_ID` is set, the hook script adds
  `"paperclip": {"agentId", "companyId", "runId"}`. It adds nothing otherwise,
  so the change is inert for users who do not run Paperclip.

### 4.2 Channel B — Paperclip live events **[v]** (payload fields **[?] M3**)
Socket: `/api/companies/:companyId/events/ws`. These event types are used:

| Live event | Payload (seen in `server/src/services/heartbeat.ts`) | Use |
|---|---|---|
| `heartbeat.run.queued` / `heartbeat.run.status` | run id, agent id, status | Run lifecycle |
| `heartbeat.run.event` | `runId, agentId, issueId, seq, eventType, stream, level, message` | Activity for non-Claude adapters |
| `agent.status` | `agentId, status, lastHeartbeatAt, outcome` | Paused, terminated, error |
| `activity.logged` | actor, action, entity, details | Approvals, budget incidents, hires |

On connect, and again on any `agent.*` activity, the source snapshots the org
chart with `GET /api/companies/:companyId/agents`. Pending approvals come from
`GET /api/companies/:companyId/approvals`.

### 4.3 Channel C — acting from the office (M4)
The route that resolves an approval **[?] M4** is under
`server/src/routes/approvals.ts` in the Paperclip fork. Only a *privileged*
Pixel Agents client may call it: the standalone client must hold the `?token=`
capability, exactly as for hook installs today. The decision lands in
Paperclip's activity log with the board user as actor. No second record is
needed (AD-1).

---

## 5. Component: `PaperclipSource`

**Location:** `pixel-agents-2/server/src/providers/stream/paperclip/`
(`source.ts`, `mapper.ts`, `client.ts`, and a test for each).

**Configuration:** in `~/.pixel-agents/config.json`, add
`paperclip: { url: "http://localhost:3100", companyIds: [] }`. An empty list
means every company the socket may see. The source is off unless `url` is
set.

**Lifecycle:** start with the runtime and dispose with it. Keep one socket per
company. Reconnect with the same backoff `WebSocketTransport` uses
(250 ms → 4 s cap). After every reconnect, re-snapshot over REST before
applying events, so state that was missed while disconnected is recovered.

**Idempotency:** delivery is at least once. Key run activity on
`(runId, seq)`, keep a last-seen `seq` per run, and drop anything at or below
it.

**Mapper:** a pure function `(orgSnapshot, liveEvent) → AgentEvent[] + teamInfo[]`,
unit-tested without either server:

| Paperclip | AgentEvent / message |
|---|---|
| agent in snapshot, not yet on screen | `sessionStart` keyed `paperclip:<agentId>`, plus `agentTeamInfo` |
| run status → running | `toolStart` "Working on \<issue title\>" (only when channel A is silent for that agent) |
| run status → succeeded / failed / cancelled | `turnEnd` |
| approval pending for agent | `permissionRequest` |
| approval decided | clear the bubble (`toolEnd` on the synthetic tool) |
| `agent.status` paused | `turnEnd`, idle |
| `agent.status` terminated | `sessionEnd` |

**Precedence rule:** channel A is the authority on *activity*, and channel B is
the authority on *identity and company state*. When A is flowing for an agent,
B's synthetic run activity is suppressed. This reuses the runtime's existing
`hookDelivered` flag.

---

## 6. Key sequences

**An employee works (M2, `claude_local`)**
1. The scheduler wakes Ada, CEO. Paperclip publishes `heartbeat.run.status: running`.
2. `PaperclipSource` ensures Ada's character exists and is labelled.
3. `claude_local` spawns Claude with `PAPERCLIP_AGENT_ID` set.
4. Claude fires `PreToolUse`. The hook posts it with `paperclip.agentId`.
   `SessionRouter` aliases it to Ada, and Ada types.
5. The run finishes. Claude fires `Stop` (channel A) and Paperclip publishes
   `run.status: succeeded` (channel B). Both resolve to `turnEnd`, and the
   duplicate is harmless.

**The board is needed (M3 → M4)**
1. Ada requests a hire. Paperclip logs `approval.created`. Ada shows the amber bubble.
2. M3: the human approves in the Paperclip UI. `approval.decided` clears the bubble.
3. M4: the human clicks the bubble in the office and chooses Approve. A
   privileged `POST` goes to Paperclip, and the same `approval.decided` clears
   the bubble.

---

## 7. Failure modes

| Failure | Behaviour |
|---|---|
| Paperclip down | The office keeps every character that is already on screen, idle. The source retries with backoff. A status chip in Settings reads "Paperclip: reconnecting". |
| Pixel Agents down | Paperclip is unaffected, because nothing in Paperclip depends on the office. Hook POSTs fail silently, which is the upstream behaviour. |
| Hooks not installed | Channel B alone still gives characters, labels, run state and approvals, at coarser activity. |
| Duplicate or out-of-order events | The `(runId, seq)` guard handles run events. Everything else is state-convergent, because the REST snapshot wins. |
| Non-Claude adapter | Channel B only: the character types while its run is `running`. |

## 8. Security

- The office trusts only loopback Paperclip in `local_trusted` mode. Any other
  mode requires an agent API key in config. That is out of scope for this epic.
- Channel C mutates business state, so it is gated on the existing privileged
  token. An unprivileged viewer can watch but cannot decide.
- The hook enrichment forwards identifiers only, never secrets.
  `PAPERCLIP_API_KEY` is explicitly excluded.

## 9. Runbook (the target of M1)

```bash
# Node 24.11+ (Paperclip's floor)
npx paperclipai onboard --yes        # http://localhost:3100, embedded Postgres, local_trusted
npx pixel-agents                     # open the printed URL WITH ?token=, approve hooks,
                                     # Settings → Watch All Sessions (needed until M2)
# Paperclip UI: create a company, hire a CEO on claude_local, assign an issue, wake it.
```

M3 onward replaces `npx pixel-agents` with a build from `pixel-agents-2` on
branch `meridian/main`.

---

## 10. Milestones

Each milestone fits in one session and ships only with its acceptance met.

| M | Deliverable | Where | Acceptance |
|---|---|---|---|
| **M0** | Forks | GitHub | ✅ done: `paperclip-2`, `pixel-agents-2` |
| **M1** | Zero-code smoke: run §9 as is | PC | The CEO's run animates in the office. Screenshot at `docs/first-world/M1.png`. **Settles [?]**: do hooks fire under `claude --print`, and does Watch All adopt Paperclip's workspace cwd? |
| **M2** | Identity: hook enrichment + `SessionRouter` alias | `pixel-agents-2` | Three heartbeats by one agent give **one** character. Unit tests for the alias. Existing e2e stays green. |
| **M3** | `PaperclipSource` + labels + approval bubbles | `pixel-agents-2` | With hooks **off**, a `process`-adapter agent (keyless) spawns labelled, types while running, and bubbles on a pending approval. Mapper tests pass offline. |
| **M4** | Approve from the office | `pixel-agents-2` | A bubble click approves. The Paperclip activity log shows the decision with the board as actor. An unprivileged client cannot do it. |

**After M4, create.** These are the upgrades only Meridian Valley supplies:
- Layout from the org chart: departments become office Areas, and a
  manager's desk sits near their reports.
- Budgets drawn in the room: spend shown per character, and a budget
  incident visible without opening a dashboard.
- A replayable office, which needs the positions and gestures the office
  itself emits. This is the point where this repo's own log (AD-1) comes back.

## 11. Open facts (owned by milestone)

| [?] | Settled in |
|---|---|
| Hooks fire under `claude --print --output-format stream-json` as Paperclip invokes it (`execute.ts:885–887`) | M1 |
| Watch All adopts sessions whose cwd is a Paperclip workspace | M1 (moot after M2) |
| Exact payload shapes for `heartbeat.run.status` and approval `activity.logged` | M3 |
| Approval decision route and body | M4 |
