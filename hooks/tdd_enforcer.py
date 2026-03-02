#!/usr/bin/env python3
"""TDD enforcer - reminds to use TDD when modifying implementation code.

This is a NON-BLOCKING reminder (PostToolUse hook) - edits always complete,
then a reminder is shown to encourage TDD practices when appropriate.
Returns exit code 2 to show TDD reminders to Claude.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _util import NC, YELLOW
from _audit import AuditLogger

EXCLUDED_EXTENSIONS = [
    ".md",
    ".rst",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".lock",
    ".sum",
    ".env",
    ".env.example",
    ".sql",
]

EXCLUDED_DIRS = [
    "/cdk/",
    "/infra/",
    "/infrastructure/",
    "/terraform/",
    "/pulumi/",
    "/stacks/",
    "/cloudformation/",
    "/aws/",
    "/deploy/",
    "/migrations/",
    "/alembic/",
    "/generated/",
    "/proto/",
    "/__generated__/",
    "/dist/",
    "/build/",
    "/node_modules/",
    "/.venv/",
    "/venv/",
    "/__pycache__/",
]


def should_skip(file_path: str) -> bool:
    """Check if file should be skipped based on extension or directory."""
    path = Path(file_path)

    if path.suffix in EXCLUDED_EXTENSIONS:
        return True

    if path.name in EXCLUDED_EXTENSIONS:
        return True

    for excluded_dir in EXCLUDED_DIRS:
        if excluded_dir in file_path:
            return True

    return False


def is_test_file(file_path: str) -> bool:
    """Check if file is a test file."""
    path = Path(file_path)
    name = path.name

    if name.endswith(".py"):
        stem = path.stem
        if stem.startswith("test_") or stem.endswith("_test"):
            return True

    if name.endswith((".test.ts", ".spec.ts", ".test.tsx", ".spec.tsx")):
        return True

    if name.endswith("_test.go"):
        return True

    return False


def has_related_failing_test(project_dir: str, impl_file: str) -> bool:
    """Check if there's a failing test specifically for this module.

    Looks for test files matching the implementation file name in the
    pytest lastfailed cache. Only returns True if there's a failing test
    that appears to be for the module being edited.
    """
    cache_file = Path(project_dir) / ".pytest_cache" / "v" / "cache" / "lastfailed"

    if not cache_file.exists():
        return False

    impl_path = Path(impl_file)
    module_name = impl_path.stem

    try:
        with cache_file.open() as f:
            lastfailed = json.load(f)

        if not lastfailed:
            return False

        for test_path in lastfailed:
            test_file = test_path.split("::")[0]
            test_name = Path(test_file).stem

            if test_name == f"test_{module_name}" or test_name == f"{module_name}_test":
                return True

        return False
    except (json.JSONDecodeError, OSError):
        return False


def has_typescript_test_file(impl_path: str) -> bool:
    """Check if corresponding TypeScript test file exists."""
    path = Path(impl_path)
    directory = path.parent

    if path.name.endswith(".tsx"):
        base_name = path.name[:-4]
        extensions = [".test.tsx", ".spec.tsx", ".test.ts", ".spec.ts"]
    elif path.name.endswith(".ts"):
        base_name = path.name[:-3]
        extensions = [".test.ts", ".spec.ts"]
    else:
        return False

    for ext in extensions:
        test_file = directory / f"{base_name}{ext}"
        if test_file.exists():
            return True

    return False


def has_go_test_file(impl_path: str) -> bool:
    """Check if corresponding Go test file exists."""
    path = Path(impl_path)

    if not path.name.endswith(".go"):
        return False

    base_name = path.stem
    test_file = path.parent / f"{base_name}_test.go"

    return test_file.exists()


def _is_import_line(line: str) -> bool:
    """Check if a line is part of an import statement."""
    if line.startswith(("import ", "from ")):
        return True
    if line in (")", "("):
        return True
    if re.match(r"^[A-Za-z_][A-Za-z_0-9]*,?$", line):
        return True
    return False


def _is_subsequence(shorter: list[str], longer: list[str]) -> bool:
    """Check if shorter is an ordered subsequence of longer."""
    it = iter(longer)
    return all(line in it for line in shorter)


def is_trivial_edit(tool_name: str, tool_input: dict) -> bool:
    """Check if an Edit is trivial (imports, constants, removals) and doesn't need a failing test."""
    if tool_name != "Edit":
        return False

    old_string = tool_input.get("old_string", "")
    new_string = tool_input.get("new_string", "")

    if not old_string or not new_string:
        return False

    old_lines = [line.strip() for line in old_string.strip().splitlines() if line.strip()]
    new_lines = [line.strip() for line in new_string.strip().splitlines() if line.strip()]

    if not old_lines and not new_lines:
        return False

    all_lines = old_lines + new_lines
    if all_lines and all(_is_import_line(line) for line in all_lines):
        return True

    if new_lines and len(new_lines) < len(old_lines) and _is_subsequence(new_lines, old_lines):
        return True

    added = [line for line in new_lines if line not in old_lines]
    removed = [line for line in old_lines if line not in new_lines]
    if added and not removed and all(re.match(r"^[A-Z][A-Z_0-9]*\s*=\s*", line) for line in added):
        return True

    return False


def warn(message: str, suggestion: str, affected_tests: list[str] | None = None, file_path: str = "") -> int:
    """Print a TDD reminder to stderr and return exit code 2 (non-blocking PostToolUse signal)."""
    rule_link = "https://github.com/thebotclub/tribunal-vault/blob/main/rules/workflow/tdd.md"
    print("", file=sys.stderr)
    print(f"{YELLOW}⚠ TDD Reminder: {message}{NC}", file=sys.stderr)
    print(f"{YELLOW}  What to do next: {suggestion}{NC}", file=sys.stderr)
    if affected_tests:
        print(f"{YELLOW}  Affected tests: {', '.join(affected_tests)}{NC}", file=sys.stderr)
    print(f"{YELLOW}  Rule: {rule_link}{NC}", file=sys.stderr)
    # Structured audit log
    logger = AuditLogger(hook_name="tdd_enforcer")
    detail = f"{message} | {suggestion}"
    if affected_tests:
        detail += f" | affected: {','.join(affected_tests)}"
    logger.set_outcome("warned", detail=detail)
    logger.log(file_path=file_path)
    return 2


# ---------------------------------------------------------------------------
# Test root discovery cache
# ---------------------------------------------------------------------------

_TEST_ROOTS_CACHE = Path.home() / ".tribunal" / "test-roots.json"


def _load_test_roots_cache() -> dict:
    try:
        if _TEST_ROOTS_CACHE.exists():
            return json.loads(_TEST_ROOTS_CACHE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def _save_test_roots_cache(cache: dict) -> None:
    try:
        _TEST_ROOTS_CACHE.parent.mkdir(parents=True, exist_ok=True)
        _TEST_ROOTS_CACHE.write_text(json.dumps(cache, indent=2))
    except OSError:
        pass


def _find_ts_test_roots(project_root: Path) -> list[str]:
    """Discover TypeScript test roots using tsconfig.json and vitest/jest configs."""
    roots = []

    # Read tsconfig rootDir
    tsconfig = project_root / "tsconfig.json"
    if tsconfig.exists():
        try:
            data = json.loads(tsconfig.read_text())
            root_dir = data.get("compilerOptions", {}).get("rootDir", "src")
            src_root = project_root / root_dir
            if src_root.exists():
                roots.append(str(src_root))
        except (json.JSONDecodeError, OSError):
            pass

    # Check vitest.config.ts for testMatch/include
    for vite_cfg in ["vitest.config.ts", "vitest.config.js", "vite.config.ts"]:
        cfg_path = project_root / vite_cfg
        if cfg_path.exists():
            cfg_text = cfg_path.read_text()
            # Extract include patterns
            matches = re.findall(r'include:\s*\[([^\]]+)\]', cfg_text)
            for m in matches:
                dirs = re.findall(r'"([^"]+)"|' + "'" + r'([^'"'"']+)' + "'" + r'', m)
                for d1, d2 in dirs:
                    pattern = d1 or d2
                    # Extract directory portion of glob
                    dir_part = pattern.split("*")[0].rstrip("/")
                    if dir_part:
                        roots.append(str(project_root / dir_part))
            break

    # Check jest.config.*
    for jest_cfg in list(project_root.glob("jest.config.*")):
        try:
            cfg_text = jest_cfg.read_text()
            matches = re.findall(r'testMatch:\s*\[([^\]]+)\]', cfg_text)
            for m in matches:
                dirs = [token.strip('"\' ').strip() for token in m.split(',') if token.strip().strip('"\' ')]
                for d1, d2 in dirs:
                    pattern = d1 or d2
                    dir_part = pattern.split("*")[0].lstrip("<").rstrip("/")
                    if dir_part and not dir_part.startswith("**"):
                        roots.append(str(project_root / dir_part))
        except OSError:
            pass

    # Search __tests__/ up to 3 levels up from file
    if not roots:
        roots.append(str(project_root))

    return list(dict.fromkeys(roots))  # deduplicate


def _find_go_test_roots(project_root: Path, changed_pkg_dir: Path) -> list[str]:
    """Find Go test files relevant to the changed package using go.mod module root."""
    go_mod = project_root / "go.mod"
    if not go_mod.exists():
        # Walk up to find go.mod
        for parent in changed_pkg_dir.parents:
            if (parent / "go.mod").exists():
                project_root = parent
                go_mod = parent / "go.mod"
                break

    if not go_mod.exists():
        return [str(changed_pkg_dir)]

    # Parse module name from go.mod
    module_name = ""
    for line in go_mod.read_text().splitlines():
        if line.startswith("module "):
            module_name = line.split()[1]
            break

    # Find all *_test.go in module that import or reference the changed package
    pkg_path_suffix = str(changed_pkg_dir.relative_to(project_root))
    relevant_tests = []

    try:
        for test_file in project_root.rglob("*_test.go"):
            try:
                content = test_file.read_text()
                # Check if test file imports the changed package
                if pkg_path_suffix in content or (module_name and f"{module_name}/{pkg_path_suffix}" in content):
                    relevant_tests.append(str(test_file))
            except OSError:
                pass
    except OSError:
        pass

    return relevant_tests if relevant_tests else [str(changed_pkg_dir)]


def get_ts_test_file(impl_path: str) -> str | None:
    """Find TypeScript test file using project config and __tests__ directories."""
    path = Path(impl_path).resolve()
    project_root = path

    # Find project root (git root or package.json location)
    for parent in [path] + list(path.parents):
        if (parent / "package.json").exists() or (parent / ".git").exists():
            project_root = parent
            break

    # Check cache
    cache = _load_test_roots_cache()
    cache_key = str(project_root)
    cached = cache.get(cache_key, {})
    if cached.get("ts_roots"):
        ts_roots = [Path(r) for r in cached["ts_roots"]]
    else:
        ts_roots = [Path(r) for r in _find_ts_test_roots(project_root)]
        cached["ts_roots"] = [str(r) for r in ts_roots]
        cache[cache_key] = cached
        _save_test_roots_cache(cache)

    base = path.stem
    if base.endswith(".test") or base.endswith(".spec"):
        return None  # already a test file

    suffixes = [".test.ts", ".spec.ts", ".test.tsx", ".spec.tsx"]

    # Check same directory first
    for suf in suffixes:
        candidate = path.parent / f"{base}{suf}"
        if candidate.exists():
            return str(candidate)

    # Check __tests__/ up to 3 levels up
    search_start = path.parent
    for _ in range(3):
        tests_dir = search_start / "__tests__"
        if tests_dir.is_dir():
            for suf in suffixes:
                candidate = tests_dir / f"{base}{suf}"
                if candidate.exists():
                    return str(candidate)
        if search_start.parent == search_start:
            break
        search_start = search_start.parent

    # Check discovered ts roots
    for root in ts_roots:
        for suf in suffixes:
            candidate = root / f"{base}{suf}"
            if candidate.exists():
                return str(candidate)

    return None


def get_go_test_files(impl_path: str) -> list[str]:
    """Find Go test files using go.mod module discovery with caching."""
    path = Path(impl_path).resolve()
    project_root = path.parent

    # Find go.mod
    for parent in [path.parent] + list(path.parents):
        if (parent / "go.mod").exists():
            project_root = parent
            break

    cache = _load_test_roots_cache()
    cache_key = str(project_root) + ":go"
    cached = cache.get(cache_key, {})

    pkg_dir = path.parent
    pkg_key = str(pkg_dir)

    if pkg_key in cached:
        return cached[pkg_key]

    tests = _find_go_test_roots(project_root, pkg_dir)
    cached[pkg_key] = tests
    cache[cache_key] = cached
    _save_test_roots_cache(cache)
    return tests


# ---------------------------------------------------------------------------
# Coverage-aware TDD (Item 6)
# ---------------------------------------------------------------------------

_COVERAGE_CACHE = Path.home() / ".tribunal" / "coverage-cache.json"


def _load_coverage_cache() -> dict:
    try:
        if _COVERAGE_CACHE.exists():
            return json.loads(_COVERAGE_CACHE.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def _save_coverage_cache(cache: dict) -> None:
    try:
        _COVERAGE_CACHE.parent.mkdir(parents=True, exist_ok=True)
        _COVERAGE_CACHE.write_text(json.dumps(cache, indent=2))
    except OSError:
        pass


def _is_coverage_available() -> bool:
    """Check if coverage package is available."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "coverage", "--version"],
            capture_output=True, text=True, check=False
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def run_python_coverage(module_name: str, test_file: str, source_file: str) -> int:
    """Run coverage analysis for a Python module. Returns exit code.

    Only runs when SF_TDD_COVERAGE=1. Requires 'coverage' package.
    Caches results to avoid re-running on unchanged files.
    """
    if os.environ.get("SF_TDD_COVERAGE") != "1":
        return 0

    if not _is_coverage_available():
        return 0  # graceful degradation

    test_path = Path(test_file)
    source_path = Path(source_file)

    if not test_path.exists():
        return 0

    # Check cache: skip if source file unchanged (using mtime)
    cache = _load_coverage_cache()
    mtime = source_path.stat().st_mtime if source_path.exists() else 0
    cache_key = str(source_path)
    cached = cache.get(cache_key, {})
    if cached.get("mtime") == mtime and cached.get("coverage_pct", 0) >= 80:
        return 0  # cached pass

    # Run: coverage run --source=<module> -m pytest <test_file> -q --no-header
    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "coverage", "run",
                f"--source={module_name}",
                "-m", "pytest", test_file, "-q", "--no-header",
            ],
            capture_output=True, text=True, check=False, timeout=60
        )

        if result.returncode != 0:
            # Tests failed — TDD enforcer already handles this
            return 0

        # Get coverage report
        report = subprocess.run(
            [sys.executable, "-m", "coverage", "report", "--show-missing", "--no-header"],
            capture_output=True, text=True, check=False, timeout=10
        )

        coverage_output = report.stdout
        coverage_pct = 0

        # Parse coverage percentage from report
        for line in coverage_output.splitlines():
            if module_name in line or source_path.name in line:
                parts = line.split()
                if parts:
                    pct_str = parts[-1].rstrip("%")
                    try:
                        coverage_pct = float(pct_str)
                    except ValueError:
                        pass
                break

        # Update cache
        cache[cache_key] = {"mtime": mtime, "coverage_pct": coverage_pct}
        _save_coverage_cache(cache)

        if coverage_pct < 80:
            # Find uncovered line ranges from report
            uncovered = []
            for line in coverage_output.splitlines():
                if source_path.name in line and "%" in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        uncovered_ranges = " ".join(parts[4:])
                        uncovered.append(uncovered_ranges)

            print("", file=sys.stderr)
            print(f"{YELLOW}⚠ Coverage Warning: {source_path.name} has {coverage_pct:.0f}% coverage (< 80%){NC}", file=sys.stderr)
            if uncovered:
                print(f"{YELLOW}  Uncovered lines: {', '.join(uncovered)}{NC}", file=sys.stderr)
            print(f"{YELLOW}  Run with SF_TDD_COVERAGE=1 to check coverage locally{NC}", file=sys.stderr)
            return 2

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return 0


def run_tdd_enforcer() -> int:
    """Run TDD enforcement and return exit code."""
    try:
        hook_data = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0

    tool_name = hook_data.get("tool_name", "")
    if tool_name not in ("Write", "Edit"):
        return 0

    tool_input = hook_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if not file_path:
        return 0

    if should_skip(file_path):
        return 0

    if is_test_file(file_path):
        return 0

    if is_trivial_edit(tool_name, tool_input):
        return 0

    if file_path.endswith(".py"):
        path = Path(file_path).parent
        found_failing = False

        for _ in range(10):
            if has_related_failing_test(str(path), file_path):
                found_failing = True
                break
            if path.parent == path:
                break
            path = path.parent

        if found_failing:
            return 0

        module_name = Path(file_path).stem

        # Find affected tests via dependency graph
        affected_names: list[str] = []
        try:
            from _checkers.dependency_graph import find_affected_tests

            affected = find_affected_tests(Path(file_path))
            affected_names = [t.name for t in affected]
        except Exception as exc:
            print(f"  [dep-graph] {exc}", file=sys.stderr)

        # Check coverage if SF_TDD_COVERAGE=1
        test_file_candidate = Path(file_path).parent / f"test_{module_name}.py"
        if not test_file_candidate.exists():
            for parent in Path(file_path).parents:
                candidate = parent / f"test_{module_name}.py"
                if candidate.exists():
                    test_file_candidate = candidate
                    break
        coverage_result = run_python_coverage(module_name, str(test_file_candidate), file_path)
        if coverage_result != 0:
            return coverage_result

        return warn(
            f"No failing test for '{module_name}' module",
            f"Write a failing test in test_{module_name}.py first.",
            affected_tests=affected_names if affected_names else None,
        )

    if file_path.endswith((".ts", ".tsx")):
        # Use enhanced discovery (tsconfig + vitest/jest config + __tests__ dirs)
        test_file = get_ts_test_file(file_path)
        if test_file or has_typescript_test_file(file_path):
            return 0

        base_name = Path(file_path).stem
        return warn(
            "No test file found for this module",
            f"Consider creating {base_name}.test.ts first (checked __tests__/ up 3 levels + vitest/jest config).",
        )

    if file_path.endswith(".go"):
        # Use enhanced discovery (go.mod module root + cross-package test search)
        related_tests = get_go_test_files(file_path)
        same_dir_test = Path(file_path).parent / f"{Path(file_path).stem}_test.go"
        if same_dir_test.exists() or (related_tests and any(Path(t).exists() for t in related_tests)):
            return 0

        base_name = Path(file_path).stem
        return warn(
            "No test file found",
            f"Consider creating {base_name}_test.go first.",
        )

    return 0


if __name__ == "__main__":
    sys.exit(run_tdd_enforcer())
