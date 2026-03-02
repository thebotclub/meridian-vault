"""Audit logger hook — logs tool usage to ~/.tribunal/audit.log as JSONL.

Now uses the shared AuditLogger class from _audit.py for structured logging
with fields: hook_name, outcome, duration_ms, detail.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _audit import AuditLogger


def main() -> None:
    raw = os.environ.get("CLAUDE_TOOL_INPUT", "{}")
    try:
        tool_input: dict = json.loads(raw)
    except json.JSONDecodeError:
        tool_input = {}

    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
    file_path = tool_input.get("file_path") or tool_input.get("path") or ""

    logger = AuditLogger(hook_name="audit_logger")
    logger.set_outcome("allowed")
    logger.log(tool_name=tool_name, file_path=file_path)


if __name__ == "__main__":
    main()
