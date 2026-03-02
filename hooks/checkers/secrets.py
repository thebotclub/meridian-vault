"""Secret detection checker — scans file content for hardcoded secrets."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _util import NC, RED, YELLOW, is_test_file

# File extensions to skip (config, docs, locks)
SKIP_EXTENSIONS = {
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
    ".svg",
    ".png",
    ".jpg",
    ".gif",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
}

# Files to always skip
SKIP_FILENAMES = {
    ".env.example",
    ".env.sample",
    ".env.template",
    "package-lock.json",
    "yarn.lock",
    "uv.lock",
    "bun.lockb",
    "Cargo.lock",
    "go.sum",
}

# Secret detection patterns: (name, regex)
# Each regex should match the secret VALUE, not just the key name.
SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # AWS
    ("AWS Access Key", re.compile(r"(?<![A-Z0-9])AKIA[0-9A-Z]{16}(?![A-Z0-9])")),
    (
        "AWS Secret Key",
        re.compile(
            r"""(?:aws_secret_access_key|AWS_SECRET_ACCESS_KEY|secret_key)\s*[=:]\s*['"]([A-Za-z0-9/+=]{40})['"]""",
        ),
    ),
    # GitHub
    ("GitHub Token (classic)", re.compile(r"ghp_[A-Za-z0-9]{36,}")),
    ("GitHub Token (fine-grained)", re.compile(r"github_pat_[A-Za-z0-9_]{22,}")),
    ("GitHub OAuth", re.compile(r"gho_[A-Za-z0-9]{36,}")),
    ("GitHub App Token", re.compile(r"(?:ghu|ghs)_[A-Za-z0-9]{36,}")),
    # Anthropic
    ("Anthropic API Key", re.compile(r"sk-ant-api\d{2}-[A-Za-z0-9\-_]{20,}")),
    # OpenAI (negative lookahead to avoid matching Anthropic sk-ant- keys)
    ("OpenAI API Key", re.compile(r"sk-(?!ant-)(?:proj-)?[A-Za-z0-9]{20,}")),
    # Slack
    ("Slack Token", re.compile(r"xox[bpors]-[0-9a-zA-Z\-]{10,}")),
    # Private Keys
    ("Private Key", re.compile(r"-----BEGIN\s+(?:RSA\s+|EC\s+|DSA\s+|OPENSSH\s+)?PRIVATE\s+KEY-----")),
    # Database URLs with embedded credentials
    (
        "Database URL with Password",
        re.compile(r"(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp)://[^:\s]+:[^@\s]+@[^\s]+"),
    ),
    # Bearer/JWT tokens (long base64 with dots)
    (
        "Bearer/JWT Token",
        re.compile(r"""(?:Bearer|bearer)\s+eyJ[A-Za-z0-9_-]{20,}\.eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}"""),
    ),
    # Generic: variable named *_key/*_secret/*_token with a long hex/base64 value
    (
        "Generic Secret Assignment",
        re.compile(
            r"""(?:api[_-]?key|api[_-]?secret|secret[_-]?key|access[_-]?token|auth[_-]?token|private[_-]?key)"""
            r"""\s*[=:]\s*['"]([A-Za-z0-9+/=_\-]{20,})['"]""",
            re.IGNORECASE,
        ),
    ),
]

# Values that are obviously placeholders, not real secrets
PLACEHOLDER_PATTERNS = re.compile(
    r"^(your[_-]|xxx|test[_-]|fake[_-]|dummy[_-]|example[_-]|replace[_-]|changeme|TODO|FIXME|placeholder)",
    re.IGNORECASE,
)


def _is_placeholder(value: str) -> bool:
    """Check if a matched value is a placeholder rather than a real secret."""
    if not value or len(value) < 8:
        return True
    if PLACEHOLDER_PATTERNS.search(value):
        return True
    # All same character
    if len(set(value.replace("-", "").replace("_", ""))) <= 2:
        return True
    return False


def detect_secrets_in_content(content: str) -> list[dict[str, str | int]]:
    """Scan content for secret patterns.

    Returns a list of findings, each with:
    - pattern: name of the matched pattern
    - line: line number (1-based)
    - match: the matched text (truncated)
    """
    findings: list[dict[str, str | int]] = []
    lines = content.splitlines()

    for line_num, line in enumerate(lines, start=1):
        for pattern_name, regex in SECRET_PATTERNS:
            for m in regex.finditer(line):
                matched_text = m.group(0)
                # Check if the match contains a capture group (the secret value)
                value = m.group(1) if m.lastindex and m.lastindex >= 1 else matched_text
                if _is_placeholder(value):
                    continue
                findings.append(
                    {
                        "pattern": pattern_name,
                        "line": line_num,
                        "match": matched_text[:60] + "..." if len(matched_text) > 60 else matched_text,
                    }
                )

    return findings


def _is_in_secretsignore(file_path: Path, project_root: Path | None = None) -> bool:
    """Check if file is listed in .secretsignore."""
    if project_root is None:
        project_root = file_path.parent

    ignore_file = project_root / ".secretsignore"
    if not ignore_file.exists():
        return False

    try:
        patterns = ignore_file.read_text().splitlines()
        for pattern in patterns:
            pattern = pattern.strip()
            if not pattern or pattern.startswith("#"):
                continue
            if file_path.name == pattern:
                return True
            try:
                if file_path.relative_to(project_root).match(pattern):
                    return True
            except (ValueError, TypeError):
                pass
    except OSError:
        pass

    return False


def check_secrets(
    file_path: Path,
    *,
    project_root: Path | None = None,
) -> tuple[int, str]:
    """Check a file for hardcoded secrets. Returns (exit_code, reason).

    exit_code 0 = clean or skipped, 2 = secrets found (blocking).
    """
    if not file_path.exists():
        return 0, ""

    # Skip by extension
    if file_path.suffix in SKIP_EXTENSIONS:
        return 0, ""

    # Skip by filename
    if file_path.name in SKIP_FILENAMES:
        return 0, ""

    # Skip test files
    if is_test_file(file_path):
        return 0, ""

    # Skip if in .secretsignore
    if _is_in_secretsignore(file_path, project_root):
        return 0, ""

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0, ""

    findings = detect_secrets_in_content(content)

    if not findings:
        return 0, ""

    _print_secret_findings(file_path, findings)
    count = len(findings)
    plural = "secret" if count == 1 else "secrets"
    return 2, f"Secrets: {count} potential {plural} in {file_path.name}"


def _print_secret_findings(file_path: Path, findings: list[dict[str, str | int]]) -> None:
    """Print secret findings to stderr."""
    print("", file=sys.stderr)
    print(f"{RED}🔑 POTENTIAL SECRETS DETECTED in: {file_path.name}{NC}", file=sys.stderr)
    print("───────────────────────────────────────", file=sys.stderr)
    for f in findings:
        print(f"  Line {f['line']}: {f['pattern']}", file=sys.stderr)
        print(f"    {YELLOW}{f['match']}{NC}", file=sys.stderr)
    print("", file=sys.stderr)
    print(f"{RED}Remove secrets before committing. Use environment variables instead.{NC}", file=sys.stderr)
    print("  Add to .secretsignore to suppress false positives.", file=sys.stderr)
