#!/usr/bin/env python3
"""Spec drift detector — warns when edited files diverge from active plan.

PostToolUse hook for Write|Edit. Every 5 edits during spec-implement,
compares git diff --name-only against active_plan.json expected_files.
Warns on unexpected files (non-blocking, exit code 2).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _util import YELLOW, NC, _sessions_base, get_session_plan_path

DRIFT_COUNTER_FILENAME = "spec-drift-counter"
CHECK_EVERY = 5  # check after every N edits


def _get_counter_path() -> Path:
    session_id = os.environ.get("SF_SESSION_ID", "").strip() or "default"
    d = _sessions_base() / session_id
    d.mkdir(parents=True, exist_ok=True)
    return d / DRIFT_COUNTER_FILENAME


def _increment_counter() -> int:
    """Increment and return the edit counter."""
    p = _get_counter_path()
    try:
        count = int(p.read_text().strip()) if p.exists() else 0
    except (ValueError, OSError):
        count = 0
    count += 1
    try:
        p.write_text(str(count))
    except OSError:
        pass
    return count


def _get_expected_files(plan_path: Path) -> list[str]:
    """Read expected_files from active_plan.json or parse plan Markdown."""
    # Try session-scoped active_plan.json first
    plan_json = get_session_plan_path()
    if plan_json.exists():
        try:
            data = json.loads(plan_json.read_text())
            files = data.get("expected_files", [])
            if files:
                return [str(f) for f in files]
        except (json.JSONDecodeError, OSError):
            pass

    # Fallback: parse ## Files section from plan Markdown
    if not plan_path.exists():
        return []
    try:
        content = plan_path.read_text()
        files = []
        in_files_section = False
        for line in content.splitlines():
            if line.strip().lower().startswith("## files") or line.strip().lower().startswith("### files"):
                in_files_section = True
                continue
            if in_files_section:
                if line.startswith("#"):
                    break
                stripped = line.strip().lstrip("-").lstrip("*").strip()
                if stripped.startswith("`") and stripped.endswith("`"):
                    stripped = stripped[1:-1]
                if stripped and ("/" in stripped or "." in stripped):
                    files.append(stripped)
        return files
    except OSError:
        return []


def _get_git_changed_files(project_root: str) -> list[str]:
    """Get files changed since the last commit (staged + unstaged)."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, timeout=10, cwd=project_root
        )
        files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
        # Also include staged changes
        result2 = subprocess.run(
            ["git", "diff", "--name-only", "--cached"],
            capture_output=True, text=True, timeout=10, cwd=project_root
        )
        files += [f.strip() for f in result2.stdout.splitlines() if f.strip()]
        return list(dict.fromkeys(files))  # deduplicate preserving order
    except (subprocess.TimeoutExpired, OSError, subprocess.SubprocessError):
        return []


def main() -> int:
    """Check for spec drift every CHECK_EVERY edits."""
    try:
        hook_data = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0

    tool_name = hook_data.get("tool_name", "")
    if tool_name not in ("Write", "Edit", "MultiEdit"):
        return 0

    count = _increment_counter()
    if count % CHECK_EVERY != 0:
        return 0

    # Find active plan
    plan_json = get_session_plan_path()
    if not plan_json.exists():
        return 0
    try:
        data = json.loads(plan_json.read_text())
        plan_path_str = data.get("plan_path", "")
    except (json.JSONDecodeError, OSError):
        return 0
    if not plan_path_str:
        return 0

    plan_path = Path(plan_path_str)
    if not plan_path.is_absolute():
        project_root = os.environ.get("CLAUDE_PROJECT_ROOT", str(Path.cwd()))
        plan_path = Path(project_root) / plan_path

    expected_files = _get_expected_files(plan_path)
    if not expected_files:
        return 0

    project_root = os.environ.get("CLAUDE_PROJECT_ROOT", str(Path.cwd()))
    changed_files = _get_git_changed_files(project_root)

    # Warn on unexpected changed files
    unexpected = [f for f in changed_files if f not in expected_files]
    if not unexpected:
        return 0

    rule_link = "https://github.com/thebotclub/meridian-vault/blob/main/rules/workflow/spec-workflow.md"
    print("", file=sys.stderr)
    print(f"{YELLOW}⚠ Spec Drift Detected (after {count} edits){NC}", file=sys.stderr)
    print(f"{YELLOW}  The following changed files are NOT in the active plan:{NC}", file=sys.stderr)
    for f in unexpected[:10]:
        print(f"{YELLOW}    - {f}{NC}", file=sys.stderr)
    if len(unexpected) > 10:
        print(f"{YELLOW}    ... and {len(unexpected) - 10} more{NC}", file=sys.stderr)
    print(f"{YELLOW}  Expected files in plan: {len(expected_files)}{NC}", file=sys.stderr)
    print(f"{YELLOW}  Rule: {rule_link}{NC}", file=sys.stderr)
    print("", file=sys.stderr)

    return 2  # Non-blocking warning


if __name__ == "__main__":
    sys.exit(main())
