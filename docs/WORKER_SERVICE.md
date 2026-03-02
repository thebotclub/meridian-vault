# Worker Service IPC Protocol

`sf/scripts/worker-service.cjs` is a long-running background process that handles memory, context, and observation events for the Tribunal plugin. It is spawned via `worker-wrapper.cjs` at session start and communicates with Claude Code hooks via CLI arguments and stdin.

## Architecture

```
Claude Code hooks
      │
      │ (bun worker-service.cjs hook claude-code <event>)
      │ stdin: JSON hook payload
      ▼
worker-wrapper.cjs   ← supervises and restarts inner process
      │
      │ (IPC via Node child_process)
      ▼
worker-service.cjs   ← event dispatcher + memory system
      │
      ▼
~/.tribunal/data/  ← local SQLite / file storage (no cloud)
```

## Event Types Accepted

The worker service is invoked as a CLI subprocess, not via a socket. The IPC between wrapper and inner service uses Node's `child_process` IPC channel (file descriptor 3 / `process.send`).

### CLI Invocation (from hooks)

```
bun worker-service.cjs hook claude-code <event_type>
```

Payload is read from **stdin** as a JSON string (Claude Code hook protocol).

| `event_type` | Trigger | Description |
|---|---|---|
| `context` | `SessionStart` | Loads memory context into the session |
| `user-message` | `SessionStart` (async) | Processes the initial user message |
| `session-init` | `UserPromptSubmit` | Initialises per-session state |
| `observation` | `PostToolUse` (all tools) | Records tool usage observations |
| `summarize` | `Stop` (async) | Summarises the completed session |

### IPC Messages (wrapper ↔ inner)

| Type | Direction | Description |
|---|---|---|
| `restart` | inner → wrapper | Requests process restart |
| `shutdown` | inner → wrapper | Requests graceful shutdown |
| `start` | system | Worker start signal |
| `stop` | system | Worker stop signal |
| `init` | system | Initialisation complete |

## Authentication / Caller Verification

The worker service **does not authenticate callers** over a network — it is invoked as a local subprocess by Claude Code hooks. Security relies on:

1. **File system permissions** — `~/.claude/tribunal/` is only accessible to the owning user.
2. `SKILLFIELD_MANAGED=true` environment variable — set by the wrapper to identify managed processes.
3. **No network listeners** — all communication is via stdin/stdout and Node IPC (no TCP/Unix sockets exposed by the service itself).

## Environment Variables

| Variable | Purpose |
|---|---|
| `SF_SESSION_ID` | Session identifier (set by launcher) |
| `SKILLFIELD_DATA_DIR` | Override data storage directory |
| `SKILLFIELD_MANAGED` | Set to `"true"` by wrapper to identify managed processes |
| `CLAUDE_PLUGIN_ROOT` | Path to the installed plugin directory |
| `SKILLFIELD_*` | Feature flags (see source for full list) |

## Input Validation

All events received via stdin are validated before processing:

- **JSON parsing** — malformed JSON is rejected with exit code 1
- **Event type allowlist** — only known event types are dispatched; unknown types are rejected
- **String length limits** — stdin payload capped at 10 MB to prevent memory exhaustion
- **Path sanitisation** — any file paths in payloads are resolved and checked against allowed directories

## Security Posture

| Property | Status |
|---|---|
| Network exposure | ❌ None — local subprocess only |
| Authentication | ✅ File system permissions |
| Input validation | ✅ JSON schema + allowlist |
| Data exfiltration | ❌ None — writes only to `~/.tribunal/` |
| Privilege escalation | ❌ Runs as the user who launched Claude Code |

## Hardening Checklist

- [x] No TCP/network listeners
- [x] Event type allowlist (unknown events rejected)
- [x] Input size limit (10 MB stdin cap)
- [x] Path traversal protection
- [x] Runs with user-level permissions only
- [ ] Formal JSON schema validation (planned)
- [ ] Signed event payloads (planned for multi-user environments)
