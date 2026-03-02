"""Consolidated file checker — dispatches by file extension to language-specific checkers."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _checkers.go import check_go
from _checkers.python import check_python
from _checkers.secrets import check_secrets
from _checkers.typescript import TS_EXTENSIONS, check_typescript
from _util import find_git_root, get_edited_file_from_stdin
from _audit import AuditLogger




def _make_actionable(reason: str, ext: str) -> str:
    """Wrap a block reason with what was detected, what to do, and a rule link."""
    lang_hints = {
        ".py": (
            "Fix: run `ruff check --fix` and `basedpyright` locally before committing.",
            "Rule: https://github.com/thebotclub/tribunal-vault/blob/main/rules/quality/python-quality.md",
        ),
        ".ts": (
            "Fix: run `eslint --fix` and `tsc --noEmit` locally before committing.",
            "Rule: https://github.com/thebotclub/tribunal-vault/blob/main/rules/quality/typescript-quality.md",
        ),
        ".tsx": (
            "Fix: run `eslint --fix` and `tsc --noEmit` locally before committing.",
            "Rule: https://github.com/thebotclub/tribunal-vault/blob/main/rules/quality/typescript-quality.md",
        ),
        ".go": (
            "Fix: run `gofmt -w .` and `go vet ./...` locally before committing.",
            "Rule: https://github.com/thebotclub/tribunal-vault/blob/main/rules/quality/go-quality.md",
        ),
    }
    fix_hint, rule_link = lang_hints.get(ext, (
        "Fix: resolve the issue before saving.",
        "Rule: https://github.com/thebotclub/tribunal-vault/blob/main/rules/",
    ))

    lines = [
        f"BLOCKED — {reason}",
        "",
        fix_hint,
        rule_link,
    ]
    return "\n".join(lines)


def main() -> int:
    """Main entry point — dispatch by file extension."""
    import time
    _t0 = time.monotonic()

    git_root = find_git_root()
    if git_root:
        os.chdir(git_root)

    target_file = get_edited_file_from_stdin()
    if not target_file or not target_file.exists():
        return 0

    logger = AuditLogger(hook_name="file_checker")
    file_path_str = str(target_file)

    # Secret detection runs on ALL file types first
    secret_code, secret_reason = check_secrets(target_file, project_root=git_root)
    if secret_reason:
        print(json.dumps({"decision": "block", "reason": secret_reason}))
        logger.set_outcome("blocked", detail=f"secret detected: {secret_reason[:120]}")
        logger.log(file_path=file_path_str)
        return secret_code

    # Language-specific checks
    if target_file.suffix == ".py":
        exit_code, reason = check_python(target_file)
    elif target_file.suffix in TS_EXTENSIONS:
        exit_code, reason = check_typescript(target_file)
    elif target_file.suffix == ".go":
        exit_code, reason = check_go(target_file)
    else:
        return 0

    if reason:
        actionable = _make_actionable(reason, str(target_file.suffix))
        print(json.dumps({"decision": "block", "reason": actionable}))
        logger.set_outcome("blocked", detail=reason[:200] if reason else "")
    else:
        print(json.dumps({}))
        logger.set_outcome("allowed")
    logger.log(file_path=file_path_str)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
