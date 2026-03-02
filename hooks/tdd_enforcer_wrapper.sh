#!/usr/bin/env bash
# Thin wrapper: sends tdd_enforcer event to hook runner daemon.
set -euo pipefail

SOCK="${SKILLFIELD_HOME:-$HOME/.tribunal}/hook-runner.sock"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/tribunal}"
STDIN_DATA=$(cat)

if [[ -S "$SOCK" ]]; then
  PAYLOAD=$(printf '{"hook":"tdd_enforcer","stdin":%s,"env":{"CLAUDE_PLUGIN_ROOT":"%s","SKILLFIELD_HOME":"%s"}}\n' \
    "$(echo "$STDIN_DATA" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')" \
    "$PLUGIN_ROOT" \
    "${SKILLFIELD_HOME:-$HOME/.tribunal}")
  RESPONSE=$(echo "$PAYLOAD" | nc -U "$SOCK" 2>/dev/null || echo '{"exit_code":1}')
  EXIT_CODE=$(echo "$RESPONSE" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("exit_code",1))')
  exit "$EXIT_CODE"
else
  echo "$STDIN_DATA" | uv run python "$PLUGIN_ROOT/hooks/tdd_enforcer.py"
fi
