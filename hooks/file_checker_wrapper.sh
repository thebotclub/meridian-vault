#!/usr/bin/env bash
# Thin wrapper: sends file_checker event to hook runner daemon.
# Falls back to direct uv invocation if daemon is not running.
set -euo pipefail

SOCK="${SKILLFIELD_HOME:-$HOME/.skillfield}/hook-runner.sock"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skillfield}"
STDIN_DATA=$(cat)

if [[ -S "$SOCK" ]]; then
  PAYLOAD=$(printf '{"hook":"file_checker","stdin":%s,"env":{"CLAUDE_PLUGIN_ROOT":"%s","SKILLFIELD_HOME":"%s"}}\n' \
    "$(echo "$STDIN_DATA" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')" \
    "$PLUGIN_ROOT" \
    "${SKILLFIELD_HOME:-$HOME/.skillfield}")
  RESPONSE=$(echo "$PAYLOAD" | nc -U "$SOCK" 2>/dev/null || echo '{"exit_code":1,"stdout":"","stderr":"daemon unavailable"}')
  EXIT_CODE=$(echo "$RESPONSE" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("exit_code",1)); print(d.get("stdout",""),end=""); import sys; sys.stderr.write(d.get("stderr",""))')
  exit "$EXIT_CODE"
else
  echo "$STDIN_DATA" | uv run python "$PLUGIN_ROOT/hooks/file_checker.py"
fi
