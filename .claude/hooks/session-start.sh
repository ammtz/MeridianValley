#!/bin/bash
# SessionStart hook — prepare a fresh Claude Code on the web container so the
# Overworld seed loop is runnable the moment the session lands.
#
# Runs synchronously: the session waits until deps are installed, so Claude
# never tries to launch uvicorn before the environment is ready.
set -euo pipefail

# Only act in the remote (web) environment; local dev manages its own venv.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}"

echo "[session-start] installing Python requirements..."
# --ignore-installed PyJWT sidesteps the Debian-managed PyJWT that pip cannot
# uninstall (RECORD file missing); without it the install aborts mid-way.
pip install --quiet --ignore-installed PyJWT -r requirements.txt

echo "[session-start] verifying toolchain..."
python -c "import fastapi, uvicorn, anthropic, claude_agent_sdk; print('[session-start] python deps OK')"
claude --version >/dev/null 2>&1 && echo "[session-start] claude CLI OK" || echo "[session-start] WARN: claude CLI not on PATH"

# Surface the API-key state so the loop's auth requirement is never a surprise.
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "[session-start] NOTE: ANTHROPIC_API_KEY is unset — server boots and serves the glass,"
  echo "[session-start]       but the seed loop (interview→minis→ship) will fail on auth until it is set."
fi

echo "[session-start] ready."
