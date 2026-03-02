"""Audit logger hook — logs tool usage to ~/.meridian/audit.log as JSONL."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


LOG_DIR = Path.home() / ".meridian"
LOG_FILE = LOG_DIR / "audit.log"
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def _rotate() -> None:
    """Rotate log file if it exceeds MAX_SIZE_BYTES."""
    if LOG_FILE.exists() and LOG_FILE.stat().st_size > MAX_SIZE_BYTES:
        rotated = LOG_FILE.with_suffix(f".{datetime.now(tz=timezone.utc).strftime('%Y%m%dT%H%M%S')}.log")
        LOG_FILE.rename(rotated)


def main() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _rotate()

    raw = os.environ.get("CLAUDE_TOOL_INPUT", "{}")
    try:
        tool_input: dict = json.loads(raw)
    except json.JSONDecodeError:
        tool_input = {}

    record = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "session_id": os.environ.get("CLAUDE_SESSION_ID", ""),
        "tool_name": os.environ.get("CLAUDE_TOOL_NAME", ""),
        "file_path": tool_input.get("file_path") or tool_input.get("path") or "",
        "project_root": os.environ.get("CLAUDE_PROJECT_ROOT", os.getcwd()),
    }

    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except OSError as exc:
        print(f"audit_logger: failed to write log: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
