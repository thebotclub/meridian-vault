#!/usr/bin/env python3
"""Persistent hook runner daemon for Tribunal.

Listens on a Unix socket (~/.tribunal/hook-runner.sock) and dispatches
hook events to pre-loaded hook modules. Eliminates uv cold-start overhead
by keeping hook modules resident in memory.

Protocol (newline-delimited JSON over Unix socket):
  Request:  {"hook": "file_checker", "stdin": "<json string>", "env": {...}}
  Response: {"exit_code": 0, "stdout": "...", "stderr": "..."}

Usage:
  # Start daemon
  python hook_runner.py --start

  # Stop daemon
  python hook_runner.py --stop

  # Run in foreground (for debugging)
  python hook_runner.py --foreground
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import socket
import sys
import threading
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [hook-runner] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

SOCKET_PATH = Path.home() / ".tribunal" / "hook-runner.sock"
PID_FILE = Path.home() / ".tribunal" / "hook-runner.pid"

# Hooks that support daemon execution (have a run(stdin_data, env) -> (rc, out, err) interface)
SUPPORTED_HOOKS = ["file_checker", "tdd_enforcer", "context_monitor"]

_hook_modules: dict = {}
_shutdown_event = threading.Event()


def _load_hook_modules(plugin_dir: Path) -> None:
    """Import hook modules once at startup."""
    hooks_dir = plugin_dir / "hooks"
    if not hooks_dir.is_dir():
        log.warning("Hooks directory not found: %s", hooks_dir)
        return

    sys.path.insert(0, str(plugin_dir))
    for hook_name in SUPPORTED_HOOKS:
        hook_file = hooks_dir / f"{hook_name}.py"
        if not hook_file.is_file():
            continue
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(hook_name, hook_file)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore[attr-defined]
                _hook_modules[hook_name] = mod
                log.info("Loaded hook module: %s", hook_name)
        except Exception as exc:
            log.error("Failed to load hook %s: %s", hook_name, exc)


def _dispatch(request: dict) -> dict:
    """Dispatch a hook request and return the response dict."""
    hook_name = request.get("hook", "")
    stdin_data = request.get("stdin", "")
    env_override = request.get("env", {})

    if hook_name not in _hook_modules:
        return {"exit_code": 1, "stdout": "", "stderr": f"Hook not loaded: {hook_name}"}

    mod = _hook_modules[hook_name]
    if not hasattr(mod, "run"):
        return {"exit_code": 1, "stdout": "", "stderr": f"Hook {hook_name} has no run() function"}

    # Merge env
    old_env = os.environ.copy()
    os.environ.update({str(k): str(v) for k, v in env_override.items()})

    import io
    old_stdin = sys.stdin
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdin = io.StringIO(stdin_data)
    captured_out = io.StringIO()
    captured_err = io.StringIO()
    sys.stdout = captured_out
    sys.stderr = captured_err

    exit_code = 0
    try:
        result = mod.run(stdin_data, env_override)
        if isinstance(result, int):
            exit_code = result
    except SystemExit as e:
        exit_code = int(e.code) if e.code is not None else 0
    except Exception as exc:
        exit_code = 1
        captured_err.write(f"Hook error: {exc}\n")
    finally:
        sys.stdin = old_stdin
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        os.environ.clear()
        os.environ.update(old_env)

    return {
        "exit_code": exit_code,
        "stdout": captured_out.getvalue(),
        "stderr": captured_err.getvalue(),
    }


def _handle_client(conn: socket.socket) -> None:
    """Handle a single client connection."""
    try:
        data = b""
        while True:
            chunk = conn.recv(65536)
            if not chunk:
                break
            data += chunk
            if b"\n" in data:
                break

        line = data.split(b"\n")[0].strip()
        if not line:
            return
        request = json.loads(line.decode("utf-8"))
        response = _dispatch(request)
        conn.sendall((json.dumps(response) + "\n").encode("utf-8"))
    except Exception as exc:
        log.error("Client handler error: %s", exc)
        try:
            conn.sendall((json.dumps({"exit_code": 1, "stdout": "", "stderr": str(exc)}) + "\n").encode("utf-8"))
        except Exception:
            pass
    finally:
        conn.close()


def _run_server() -> None:
    """Run the Unix socket server."""
    SOCKET_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SOCKET_PATH.exists():
        SOCKET_PATH.unlink()

    plugin_dir = Path(os.environ.get("CLAUDE_PLUGIN_DIR", Path.home() / ".claude" / "tribunal"))
    _load_hook_modules(plugin_dir)

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as srv:
        srv.bind(str(SOCKET_PATH))
        SOCKET_PATH.chmod(0o600)
        srv.listen(16)
        srv.settimeout(1.0)
        log.info("Hook runner listening on %s", SOCKET_PATH)

        while not _shutdown_event.is_set():
            try:
                conn, _ = srv.accept()
                t = threading.Thread(target=_handle_client, args=(conn,), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except Exception as exc:
                if not _shutdown_event.is_set():
                    log.error("Accept error: %s", exc)

    if SOCKET_PATH.exists():
        SOCKET_PATH.unlink()
    if PID_FILE.exists():
        PID_FILE.unlink()
    log.info("Hook runner stopped.")


def start_daemon() -> None:
    """Fork and start the hook runner daemon."""
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, 0)
            log.info("Hook runner already running (pid %d)", pid)
            return
        except (ProcessLookupError, ValueError):
            PID_FILE.unlink(missing_ok=True)

    pid = os.fork()
    if pid > 0:
        # Parent: write PID and return
        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(pid))
        return

    # Child: detach and run server
    os.setsid()
    _run_server()
    sys.exit(0)


def stop_daemon() -> None:
    """Stop the hook runner daemon."""
    if not PID_FILE.exists():
        log.info("Hook runner not running.")
        return
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        log.info("Sent SIGTERM to hook runner (pid %d)", pid)
    except (ProcessLookupError, ValueError):
        log.info("Hook runner process not found.")
    PID_FILE.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Tribunal hook runner daemon")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--start", action="store_true", help="Start daemon")
    group.add_argument("--stop", action="store_true", help="Stop daemon")
    group.add_argument("--foreground", action="store_true", help="Run in foreground")
    args = parser.parse_args()

    if args.start:
        start_daemon()
    elif args.stop:
        stop_daemon()
    elif args.foreground:
        signal.signal(signal.SIGTERM, lambda *_: _shutdown_event.set())
        _run_server()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
