#!/usr/bin/env python3
"""Verify manifest.json GPG signature against the pinned Tribunal Vault public key.

Usage:
    python scripts/verify_signature.py [--manifest PATH] [--sig PATH] [--pubkey PATH]

Exit codes:
    0  Signature valid
    1  Signature invalid or verification failed
    2  GPG not available
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

# Pinned public key fingerprint for the Tribunal Vault signing key.
# Update this when rotating keys (also bump the key in CI).
PINNED_FINGERPRINT: str | None = None  # Set to full 40-char fingerprint after first release

DEFAULT_MANIFEST = Path(__file__).parent.parent / "manifest.json"
DEFAULT_SIG = Path(__file__).parent.parent / "manifest.json.sig"
DEFAULT_PUBKEY = Path(__file__).parent.parent / "tribunal-vault-pubkey.asc"


def gpg_available() -> bool:
    """Return True if gpg is installed and reachable."""
    try:
        result = subprocess.run(["gpg", "--version"], capture_output=True, timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def verify(manifest: Path, sig: Path, pubkey: Path) -> bool:
    """Verify *sig* against *manifest* using *pubkey*.

    Imports the public key into a temporary GPG home directory to avoid
    polluting the user's keyring.
    """
    if not manifest.exists():
        print(f"[ERROR] Manifest not found: {manifest}", file=sys.stderr)
        return False
    if not sig.exists():
        print(f"[ERROR] Signature not found: {sig}", file=sys.stderr)
        return False
    if not pubkey.exists():
        print(f"[ERROR] Public key not found: {pubkey}", file=sys.stderr)
        return False

    with tempfile.TemporaryDirectory(prefix="tribunal-gpg-") as gpg_home:
        base_cmd = ["gpg", "--homedir", gpg_home, "--batch", "--no-tty"]

        # Import the public key
        import_result = subprocess.run(
            base_cmd + ["--import", str(pubkey)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if import_result.returncode != 0:
            print(f"[ERROR] Failed to import public key:\n{import_result.stderr}", file=sys.stderr)
            return False

        # Optionally verify against pinned fingerprint
        if PINNED_FINGERPRINT:
            list_result = subprocess.run(
                base_cmd + ["--list-keys", "--with-colons"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            fingerprints = [
                line.split(":")[9]
                for line in list_result.stdout.splitlines()
                if line.startswith("fpr")
            ]
            if PINNED_FINGERPRINT not in fingerprints:
                print(
                    f"[ERROR] Imported key fingerprint does not match pinned fingerprint.\n"
                    f"  Pinned:   {PINNED_FINGERPRINT}\n"
                    f"  Imported: {fingerprints}",
                    file=sys.stderr,
                )
                return False

        # Verify the signature
        verify_result = subprocess.run(
            base_cmd + ["--verify", str(sig), str(manifest)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if verify_result.returncode == 0:
            print("[OK] Signature valid.")
            return True
        else:
            print(f"[ERROR] Signature verification FAILED:\n{verify_result.stderr}", file=sys.stderr)
            return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Tribunal Vault manifest GPG signature.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--sig", type=Path, default=DEFAULT_SIG)
    parser.add_argument("--pubkey", type=Path, default=DEFAULT_PUBKEY)
    args = parser.parse_args()

    if not gpg_available():
        print("[ERROR] gpg is not installed. Cannot verify signature.", file=sys.stderr)
        sys.exit(2)

    if verify(args.manifest, args.sig, args.pubkey):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
