#!/usr/bin/env python3
"""SessionStart hook - codebase-aware rule injection.

Analyses the project codebase to detect framework, language mix, test framework,
and ORM/DB patterns. Injects targeted rules into the session context by appending
to CLAUDE.md or .claude/rules/ for the session.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------

def _find_project_root(start: Path) -> Path:
    """Walk up from start to find project root (git root or cwd)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(start),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except FileNotFoundError:
        pass
    return start


def _file_exists_any(root: Path, patterns: list[str]) -> bool:
    for pattern in patterns:
        if list(root.glob(pattern)):
            return True
    return False


def _read_json_safe(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def detect_frameworks(root: Path) -> list[str]:
    """Return list of detected framework identifiers."""
    frameworks = []
    pkg_json = root / "package.json"
    pyproject = root / "pyproject.toml"
    requirements = root / "requirements.txt"
    go_mod = root / "go.mod"

    # --- JS/TS frameworks ---
    if pkg_json.exists():
        data = _read_json_safe(pkg_json)
        all_deps = {
            **data.get("dependencies", {}),
            **data.get("devDependencies", {}),
        }
        # Next.js before React to be more specific
        if "next" in all_deps:
            frameworks.append("nextjs")
        elif "react" in all_deps or "react-dom" in all_deps:
            frameworks.append("react")
        if "vue" in all_deps or "@vue/core" in all_deps:
            frameworks.append("vue")
        if "express" in all_deps:
            frameworks.append("express")
        if "@angular/core" in all_deps:
            frameworks.append("angular")

    # --- Python frameworks ---
    py_text = ""
    if pyproject.exists():
        py_text = pyproject.read_text()
    if requirements.exists():
        py_text += requirements.read_text()

    if re.search(r"fastapi", py_text, re.I):
        frameworks.append("fastapi")
    if re.search(r"django", py_text, re.I):
        frameworks.append("django")
    if re.search(r"flask", py_text, re.I):
        frameworks.append("flask")

    # --- Go ---
    if go_mod.exists():
        frameworks.append("go")

    return frameworks


def detect_test_framework(root: Path) -> list[str]:
    """Detect test frameworks in use."""
    frameworks = []
    pkg_json = root / "package.json"

    if pkg_json.exists():
        data = _read_json_safe(pkg_json)
        all_deps = {
            **data.get("dependencies", {}),
            **data.get("devDependencies", {}),
        }
        if "vitest" in all_deps:
            frameworks.append("vitest")
        if "jest" in all_deps or "@jest/core" in all_deps:
            frameworks.append("jest")
        if "@playwright/test" in all_deps:
            frameworks.append("playwright")

    py_text = ""
    for f in [root / "pyproject.toml", root / "requirements.txt", root / "requirements-dev.txt"]:
        if f.exists():
            py_text += f.read_text()
    if re.search(r"pytest", py_text, re.I):
        frameworks.append("pytest")

    if list(root.glob("**/*_test.go")):
        frameworks.append("go test")

    return frameworks


def detect_orm_db(root: Path) -> list[str]:
    """Detect ORM/DB patterns."""
    patterns = []
    py_text = ""
    for f in [root / "pyproject.toml", root / "requirements.txt"]:
        if f.exists():
            py_text += f.read_text()

    if re.search(r"sqlalchemy", py_text, re.I):
        patterns.append("sqlalchemy")
    if re.search(r"alembic", py_text, re.I):
        patterns.append("alembic")
    if re.search(r"prisma", py_text, re.I) or _file_exists_any(root, ["**/schema.prisma"]):
        patterns.append("prisma")
    if re.search(r"typeorm", py_text, re.I) or _file_exists_any(root, ["**/*.entity.ts"]):
        patterns.append("typeorm")
    if root.glob("**/migrations/*.sql") or _file_exists_any(root, ["**/migrations/"]):
        patterns.append("sql-migrations")

    return patterns


# ---------------------------------------------------------------------------
# Rule injection
# ---------------------------------------------------------------------------

def _get_rules_dir(plugin_root: Path) -> Path:
    return plugin_root / "rules" / "standards"


def _inject_rule_file(rule_file: Path, target: Path) -> bool:
    """Append rule file content to target (CLAUDE.md or .claude/rules/*.md)."""
    if not rule_file.exists():
        return False
    content = rule_file.read_text()
    if target.suffix == ".md" and target.exists():
        existing = target.read_text()
        if rule_file.stem in existing:
            return False  # already injected
        target.write_text(existing.rstrip() + "\n\n---\n\n" + content + "\n")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    return True


def inject_rules(plugin_root: Path, project_root: Path, frameworks: list[str]) -> list[str]:
    """Inject framework-specific rules. Returns list of injected rule names."""
    rules_dir = _get_rules_dir(plugin_root)
    injected = []

    # Framework → rule file mapping
    framework_rules = {
        "react": "standards-react.md",
        "nextjs": "standards-nextjs.md",
        "fastapi": "standards-fastapi.md",
        "django": "standards-api.md",  # reuse api standards for Django
        "flask": "standards-api.md",
    }

    # Try .claude/rules/ first, fall back to CLAUDE.md
    claude_rules_dir = project_root / ".claude" / "rules"
    claude_md = project_root / "CLAUDE.md"

    for fw in frameworks:
        rule_filename = framework_rules.get(fw)
        if not rule_filename:
            continue
        rule_file = rules_dir / rule_filename
        if not rule_file.exists():
            continue

        if claude_rules_dir.parent.exists() or claude_rules_dir.exists():
            target = claude_rules_dir / f"tribunal-{fw}.md"
        elif claude_md.exists():
            target = claude_md
        else:
            # Create CLAUDE.md
            target = claude_md

        if _inject_rule_file(rule_file, target):
            injected.append(fw)

    return injected


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    plugin_root_str = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if not plugin_root_str:
        return 0  # silent skip if not in Tribunal context

    plugin_root = Path(plugin_root_str)
    cwd = Path(os.environ.get("PWD", os.getcwd()))
    project_root = _find_project_root(cwd)

    frameworks = detect_frameworks(project_root)

    if not frameworks:
        return 0  # nothing to inject

    injected = inject_rules(plugin_root, project_root, frameworks)

    if injected:
        # Output to stdout so Tribunal/Claude can see what was injected
        print(f"[rule_injector] Detected: {', '.join(frameworks)} | Injected rules for: {', '.join(injected)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
