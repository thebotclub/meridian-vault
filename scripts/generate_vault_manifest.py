#!/usr/bin/env python3
"""Generate vault.json manifest at vault root for programmatic asset discovery.

Produces vault.json with:
{
  "version": "1.0",
  "generated_at": "<ISO timestamp>",
  "assets": {
    "rules": [...],
    "agents": [...],
    "hooks": [...],
    "scripts": [...],
    "templates": [...]
  }
}
"""

from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ASSET_DIRS = ["rules", "agents", "hooks", "scripts", "templates"]
EXCLUDE_DIRS = {".git", "__pycache__", ".venv"}


def collect_assets(vault_root: Path) -> dict:
    """Collect asset files organised by category directory."""
    assets: dict[str, list[dict]] = {}

    for category in ASSET_DIRS:
        cat_dir = vault_root / category
        if not cat_dir.is_dir():
            continue
        entries = []
        for path in sorted(cat_dir.rglob("*")):
            if not path.is_file():
                continue
            if any(p in EXCLUDE_DIRS for p in path.parts):
                continue
            rel = str(path.relative_to(vault_root))
            entries.append({
                "path": rel,
                "name": path.stem,
                "ext": path.suffix,
            })
        if entries:
            assets[category] = entries

    return assets


def main() -> int:
    vault_root = Path(__file__).parent.parent
    assets = collect_assets(vault_root)

    manifest = {
        "version": "1.0",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "assets": assets,
    }

    out = vault_root / "vault.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n")
    total = sum(len(v) for v in assets.values())
    print(f"Generated vault.json with {total} assets across {len(assets)} categories -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
