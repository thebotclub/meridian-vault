"""Shared utilities for hook scripts.

This module provides common constants, color codes, session path helpers,
and utility functions used across all hook scripts.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

_SAFE_SESSION_ID = re.compile(r"[^A-Za-z0-9_\-]")


def _sanitize_session_id(session_id: str) -> str:
    """Strip path-traversal characters from a session ID."""
    safe = _SAFE_SESSION_ID.sub("", session_id)
    return safe or "default"


RED = "\033[0;31m"
YELLOW = "\033[0;33m"
GREEN = "\033[0;32m"
CYAN = "\033[0;36m"
BLUE = "\033[0;34m"
MAGENTA = "\033[0;35m"
NC = "\033[0m"

FILE_LENGTH_WARN = 300
FILE_LENGTH_CRITICAL = 500


def _tribunal_home() -> Path:
    """Get the Tribunal home directory, respecting SKILLFIELD_HOME env var."""
    env = os.environ.get("SKILLFIELD_HOME", "").strip()
    if env:
        return Path(env)
    return Path.home() / ".tribunal"


def _sessions_base() -> Path:
    """Get base sessions directory."""
    return _tribunal_home() / "sessions"


def get_session_cache_path() -> Path:
    """Get session-scoped context cache path."""
    session_id = _sanitize_session_id(os.environ.get("SF_SESSION_ID", "").strip())
    cache_dir = _sessions_base() / session_id
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "context-cache.json"


def get_session_plan_path() -> Path:
    """Get session-scoped active plan JSON path."""
    session_id = _sanitize_session_id(os.environ.get("SF_SESSION_ID", "").strip())
    return _sessions_base() / session_id / "active_plan.json"


def find_git_root() -> Path | None:
    """Find git repository root."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except Exception:
        pass
    return None


def get_edited_file_from_stdin() -> Path | None:
    """Get the edited file path from PostToolUse hook stdin."""
    try:
        import select

        if select.select([sys.stdin], [], [], 0)[0]:
            data = json.load(sys.stdin)
            tool_input = data.get("tool_input", {})
            file_path = tool_input.get("file_path")
            if file_path:
                return Path(file_path)
    except Exception:
        pass
    return None


_TAIL_BYTES = 131072  # 128 KB — covers many tool calls without loading the full transcript


def is_waiting_for_user_input(transcript_path: str) -> bool:
    """Check if Claude's last action was asking the user a question.

    Uses a tail-read to avoid loading multi-MB transcripts that accumulate
    over long sessions. The last assistant message is always near EOF.
    """
    try:
        transcript = Path(transcript_path)
        if not transcript.exists():
            return False

        size = transcript.stat().st_size
        if size == 0:
            return False

        with transcript.open("rb") as f:
            if size > _TAIL_BYTES:
                f.seek(-_TAIL_BYTES, 2)
                f.readline()  # discard the partial first line
            raw = f.read()

        last_assistant_msg = None
        for raw_line in reversed(raw.split(b"\n")):
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                msg = json.loads(raw_line)
                if msg.get("type") == "assistant":
                    last_assistant_msg = msg
                    break
            except json.JSONDecodeError:
                continue

        if not last_assistant_msg:
            return False

        message = last_assistant_msg.get("message", {})
        if not isinstance(message, dict):
            return False

        content = message.get("content", [])
        if not isinstance(content, list):
            return False

        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                if block.get("name") == "AskUserQuestion":
                    return True

        return False
    except OSError:
        return False


def is_test_file(file_path: Path) -> bool:
    """Check if file is a test file.

    Only checks the filename and its immediate parent directory name,
    not the full absolute path (which may contain 'test' incidentally).
    """
    name = file_path.name
    parent_name = file_path.parent.name

    # Python: test_foo.py, foo_test.py, foo_spec.py
    if name.startswith("test_") or name.endswith("_test.py") or name.endswith("_spec.py"):
        return True
    # TypeScript/JavaScript: foo.test.ts, foo.spec.tsx, etc.
    if name.endswith((".test.ts", ".test.tsx", ".test.js", ".test.jsx")):
        return True
    if name.endswith((".spec.ts", ".spec.tsx", ".spec.js", ".spec.jsx")):
        return True
    if name.endswith("_test.go"):
        return True
    # Parent directory patterns
    if parent_name in ("tests", "__tests__", "test", "spec"):
        return True

    return False


def check_file_length(file_path: Path) -> bool:
    """Warn if file exceeds length thresholds.

    Returns True if warning was emitted, False otherwise.
    Uses chunked byte counting with early exit once FILE_LENGTH_CRITICAL is
    exceeded to avoid allocating a full string for large files.
    """
    try:
        line_count = 0
        with file_path.open("rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                line_count += chunk.count(b"\n")
                if line_count > FILE_LENGTH_CRITICAL:
                    break
    except Exception:
        return False

    if line_count > FILE_LENGTH_CRITICAL:
        print("", file=sys.stderr)
        print(
            f"{RED}🛑 FILE TOO LONG: {file_path.name} has {line_count} lines (limit: {FILE_LENGTH_CRITICAL}){NC}",
            file=sys.stderr,
        )
        print(f"   Split into smaller, focused modules (<{FILE_LENGTH_WARN} lines each).", file=sys.stderr)
        return True
    elif line_count > FILE_LENGTH_WARN:
        print("", file=sys.stderr)
        print(
            f"{YELLOW}⚠️  FILE GROWING LONG: {file_path.name} has {line_count} lines (warn: {FILE_LENGTH_WARN}){NC}",
            file=sys.stderr,
        )
        print("   Consider splitting before it grows further.", file=sys.stderr)
        return True
    return False
