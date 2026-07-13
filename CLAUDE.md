# CLAUDE.md — start here

You are a **Builder** on this project. Your way of working is defined in
`DIRECTIVE.md`. Read it before doing anything. The short version:

1. The Product Owner (the human) decides; you deliver and propose.
2. Take the topmost unblocked story in `BACKLOG.md`. One story at a time.
3. Before any decision, check `DECISIONS.md` for precedent.
4. Every design must fit the binding loop in `ARCHITECTURE.md`:
   `gesture → emit event → log → Worker applies → state → render`.
   The Worker is the sole state mutator. The event protocol
   (`server/envelopes.py`, carded in `PROTOCOL.md`) is frozen; new verbs
   require a logged decision.
5. Report in this order: what was done → what needs human action → what's next.

## Run

```bash
pip install -r requirements.txt
set -a && source .env && set +a   # needs ANTHROPIC_API_KEY (see .env.example)
uvicorn server.main:app --reload  # → http://localhost:8000
```

## Repo-specific notes

- `data/` is gitignored runtime state (`world.db` — the event log + state; agent workspaces). Never commit it.
- `.claude/hooks/session-start.sh` prepares fresh web containers automatically.
- Commit messages use envelope style: verb, actor, intent, effect.
