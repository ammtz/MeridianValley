# The Wall and the Eye — what an agent may see

| | |
|---|---|
| **Status** | Design note · draft · 2026-09-23 |
| **Sits beside** | [`FIRST-WORLD.md`](FIRST-WORLD.md) |
| **Foundations** | `ammtz/paperclip-2` @ `f557599` · `ammtz/Graft-2` @ `f06070d` (v0.19.0) |

Same marks as the First World spec. **[v]** is verified against the fork source
at the commits above, with a file reference. Unmarked is a design choice.
**[?]** is an open fact.

---

## 1. The question

Can Graft be the gate — can an agent be kept from data simply by not putting
it in the agent's Graft map?

**Half.** Graft is a good **eye** and a bad **wall**.

## 2. Why the eye is real

What an agent is shown first decides most of what it does. A Graft map scoped
to one agent is memory selection: less noise, fewer tokens, the right function
found first. That is worth having for every agent in the office.

## 3. Why the eye is not a wall

Not showing a file does not stop an agent from reaching it. A Claude agent
keeps file reading, search and a shell. When its context is missing something,
exploring is exactly what it does, and it can open anything its operating
system user can read. A gate made of omission is security by hiding, and
agents are good at finding hidden things.

## 4. The design: wall first, eye drawn over it

The wall sits **below** the agent. Graft then draws the same line a second
time, so the two can never disagree.

1. **What exists on disk.** Each agent gets a workspace holding only what it
   may see: its own checkout, or a sparse checkout of the repo. Nothing else
   is mounted.
2. **A sandbox around the run.** Paperclip's `claude_local` adapter already
   builds one. It takes a `filesystemScope`, a `networkScope` and a
   `networkAllowlist`, and scopes the run to its workspace plus the Claude
   config, the prompt bundle and the MCP config
   **[v]** `packages/adapters/claude-local/src/server/execute.ts:570–592`.
3. **Encryption at rest** for anything sensitive. A key is handed only to an
   agent entitled to it, so a file the agent can open is still unreadable
   without its key.
4. **Build Graft inside the walled workspace.** Graft can only map what is
   there, so the eye can never show more than the wall allows.

The sandbox is the wall. Graft is the eye. Both are drawn over the same
boundary, and the wall is the one that holds.

## 5. The catch: the wall is Linux only

Paperclip's sandbox is `bwrap` (bubblewrap). On any other platform it refuses
to run: "Local process filesystem and network scopes are currently supported
only on Linux." **[v]** `packages/adapter-utils/src/local-process-sandbox.ts:347–349`.

The First World runs on Andres's Windows PC. There, step 2 does not exist, and
an agent's only wall is its Windows user account. Options, none chosen:

- Run Paperclip inside **WSL2**, where `bwrap` works. **[?]** untested: whether
  `claude_local`, the embedded Postgres and Pixel Agents' hooks all survive it.
- Run agents on a Linux host or container and keep only the office on the PC.
- Give each agent its own **Windows user account** with folder permissions.
  Coarse, but real, and it needs no Linux.

## 6. Open facts

| [?] | Settled by |
|---|---|
| Paperclip + `claude_local` + Pixel Agents hooks work under WSL2 | a WSL smoke run, M1 repeated |
| Graft builds and answers correctly on a sparse checkout | a Graft pilot run on one |
| Which data in the First World is sensitive enough for step 3 | Andres |

## 7. Not in scope

Graft's hosted Trail Brain uploads repo history off the machine. It is not
adopted, and it would cross every wall above.
