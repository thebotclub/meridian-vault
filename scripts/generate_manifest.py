#!/usr/bin/env python3
"""Generate SHA-256 manifest.json for vault files."""

from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

EXCLUDE_DIRS = {".git", "__pycache__", ".venv", "node_modules"}
EXCLUDE_FILES = {"manifest.json"}

def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def generate_manifest(vault_root):
    manifest = {}
    for path in sorted(vault_root.rglob("*")):
        if not path.is_file():
            continue
        parts = path.relative_to(vault_root).parts
        if any(p in EXCLUDE_DIRS for p in parts):
            continue
        if path.name in EXCLUDE_FILES:
            continue
        rel = str(path.relative_to(vault_root))
        manifest[rel] = sha256_file(path)
    return manifest

def main():
    vault_root = Path(__file__).parent.parent
    manifest = generate_manifest(vault_root)
    manifest_path = vault_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"Generated manifest.json with {len(manifest)} entries -> {manifest_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
