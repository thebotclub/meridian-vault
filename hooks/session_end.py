#!/usr/bin/env python3
"""SessionEnd hook - stops worker only when no other sessions are active.

Skips worker stop during endless mode handoffs (continuation file present)
or when an active spec plan is in progress (PENDING/COMPLETE status).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _util import _sessions_base


def _get_active_session_count() -> int:
    """Count active sessions by checking for session directories with activity markers."""
    sessions_dir = _sessions_base()
    if not sessions_dir.is_dir():
        return 0
    count = 0
    for entry in sessions_dir.iterdir():
        if not entry.is_dir():
            continue
        has_plan = (entry / "active_plan.json").exists()
        has_continuation = (entry / "continuation.md").exists()
        if has_plan or has_continuation:
            count += 1
    return count


def _is_session_handing_off() -> bool:
    """Check if this session is doing an endless mode handoff.

    Returns True if a continuation file exists or an active spec plan
    has PENDING/COMPLETE status (meaning the workflow will resume).
    """
    session_id = os.environ.get("SF_SESSION_ID", "").strip() or "default"
    session_dir = _sessions_base() / session_id

    if (session_dir / "continuation.md").exists():
        return True

    plan_file = session_dir / "active_plan.json"
    if plan_file.exists():
        try:
            data = json.loads(plan_file.read_text())
            status = data.get("status", "").upper()
            if status in ("PENDING", "COMPLETE"):
                return True
        except (json.JSONDecodeError, OSError):
            pass

    return False


def main() -> int:
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if not plugin_root:
        return 1

    count = _get_active_session_count()
    if count > 1:
        return 0

    if _is_session_handing_off():
        return 0

    # Extract reusable skills from this session's observations
    _run_skill_extraction(plugin_root)

    stop_script = Path(plugin_root) / "scripts" / "worker-service.cjs"
    result = subprocess.run(
        ["bun", str(stop_script), "stop"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())


# ---------------------------------------------------------------------------
# Skill extraction (Sprint 3 feature)
# ---------------------------------------------------------------------------

def _score_observation(obs: dict) -> float:
    """Score an observation for novelty and reusability (0.0–1.0)."""
    score = 0.0
    text = json.dumps(obs).lower()

    # Novelty/reusability signals
    signals = {
        0.25: ["workaround", "undocumented", "quirk", "gotcha", "edge case"],
        0.20: ["pattern", "approach", "technique", "strategy", "architecture"],
        0.15: ["performance", "optimis", "cache", "latency", "throughput"],
        0.15: ["debug", "root cause", "traced", "discovered", "realised"],
        0.10: ["api", "endpoint", "integration", "sdk", "client"],
        0.10: ["security", "auth", "token", "permission", "vulnerability"],
    }
    for weight, keywords in signals.items():
        if any(kw in text for kw in keywords):
            score += weight

    # Cap at 1.0
    return min(score, 1.0)


def _slugify(title: str) -> str:
    import re
    title = re.sub(r"[^\w\s-]", "", title.lower())
    return re.sub(r"[\s_-]+", "-", title).strip("-")[:60]


def _extract_skills_from_observations(plugin_root: str) -> int:
    """Extract high-value observations as reusable skills. Returns count extracted."""
    import datetime

    skills_dir = Path.home() / ".skillfield" / "extracted-skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    # Try to load observations from worker service observation store
    obs_file = Path(plugin_root) / "data" / "observations.json"
    if not obs_file.exists():
        # Try session-scoped observations
        session_id = os.environ.get("SF_SESSION_ID", "default")
        obs_file = Path(plugin_root) / "data" / "sessions" / session_id / "observations.json"

    if not obs_file.exists():
        return 0

    try:
        observations = json.loads(obs_file.read_text())
    except (json.JSONDecodeError, OSError):
        return 0

    if isinstance(observations, dict):
        observations = observations.get("observations", [])

    today = datetime.date.today().isoformat()
    session_id = os.environ.get("SF_SESSION_ID", "unknown")
    extracted = 0

    for obs in observations:
        score = _score_observation(obs)
        if score <= 0.7:
            continue

        title = obs.get("title") or obs.get("summary") or "untitled-observation"
        slug = _slugify(title)
        out_file = skills_dir / f"{today}-{slug}.md"

        if out_file.exists():
            continue  # already extracted

        narrative = obs.get("narrative") or obs.get("content") or json.dumps(obs, indent=2)
        facts = obs.get("facts", [])
        facts_md = "\n".join(f"- {f}" for f in facts) if facts else ""

        content = f"""---
title: {json.dumps(title)}
source-session: {session_id}
date: {today}
auto-extracted: true
score: {score:.2f}
---

# {title}

{obs.get('subtitle', '')}

{narrative}

{('## Key Facts\n\n' + facts_md) if facts_md else ''}
""".strip() + "\n"

        out_file.write_text(content)
        extracted += 1

    return extracted


def _run_skill_extraction(plugin_root: str) -> None:
    """Run skill extraction and print summary."""
    try:
        count = _extract_skills_from_observations(plugin_root)
        if count > 0:
            print(f"[session_end] Extracted {count} reusable skill{'s' if count != 1 else ''} from this session")
    except Exception as e:
        # Non-fatal — skill extraction is best-effort
        pass
