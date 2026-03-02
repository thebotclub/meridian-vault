"""Shared AuditLogger class for structured audit logging across hooks.

Adds fields: hook_name, outcome (allowed/warned/blocked), duration_ms, detail.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path.home() / ".tribunal"
LOG_FILE = LOG_DIR / "audit.log"
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


class AuditLogger:
    """Context-manager and direct-use audit logger for hooks."""

    def __init__(self, hook_name: str) -> None:
        self.hook_name = hook_name
        self._start: float = time.monotonic()
        self._outcome: str = "allowed"
        self._detail: str = ""

    def set_outcome(self, outcome: str, detail: str = "") -> None:
        """Set outcome: 'allowed', 'warned', or 'blocked'."""
        self._outcome = outcome
        self._detail = detail

    def log(
        self,
        tool_name: str = "",
        file_path: str = "",
        extra: dict | None = None,
    ) -> None:
        """Write a structured JSONL record to the audit log."""
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        _rotate()

        duration_ms = round((time.monotonic() - self._start) * 1000, 1)
        raw = os.environ.get("CLAUDE_TOOL_INPUT", "{}")
        try:
            tool_input: dict = json.loads(raw)
        except json.JSONDecodeError:
            tool_input = {}

        record: dict = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "session_id": os.environ.get("CLAUDE_SESSION_ID", ""),
            "hook_name": self.hook_name,
            "tool_name": tool_name or os.environ.get("CLAUDE_TOOL_NAME", ""),
            "file_path": (
                file_path
                or tool_input.get("file_path")
                or tool_input.get("path")
                or ""
            ),
            "project_root": os.environ.get("CLAUDE_PROJECT_ROOT", os.getcwd()),
            "outcome": self._outcome,
            "duration_ms": duration_ms,
            "detail": self._detail,
        }
        if extra:
            record.update(extra)

        try:
            with LOG_FILE.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except OSError:
            pass  # Non-fatal: don't break hooks due to logging failure

    def __enter__(self) -> "AuditLogger":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.log()


def _rotate() -> None:
    """Rotate log file if it exceeds MAX_SIZE_BYTES."""
    if LOG_FILE.exists() and LOG_FILE.stat().st_size > MAX_SIZE_BYTES:
        rotated = LOG_FILE.with_suffix(
            f".{datetime.now(tz=timezone.utc).strftime('%Y%m%dT%H%M%S')}.log"
        )
        LOG_FILE.rename(rotated)
