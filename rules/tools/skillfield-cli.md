---
id: rules/tribunal-cli
version: 1.0.0
category: tools
tags:
  - tools
deprecated: false
---

## Tribunal CLI Reference

The `tribunal` binary is at `~/.tribunal/bin/tribunal`. These are **all** available commands — do NOT call commands that aren't listed here.

### Session & Context

| Command | Purpose | Example |
|---------|---------|---------|
| `tribunal` | Start Claude with Endless Mode (primary entry point) | Just type `tribunal` or `sfc` |
| `tribunal run [args...]` | Start with optional flags | `tribunal run --skip-update-check` |
| `tribunal check-context --json` | Get context usage percentage | Returns `{"status": "OK", "percentage": 47.0}` or `{"status": "CLEAR_NEEDED", ...}` |
| `tribunal send-clear <plan.md>` | Trigger Endless Mode continuation with plan | `tribunal send-clear docs/plans/2026-02-11-foo.md` |
| `tribunal send-clear --general` | Trigger continuation without plan | Only when no active plan exists |
| `tribunal register-plan <path> <status>` | Associate plan with current session | `tribunal register-plan docs/plans/foo.md PENDING` |

### Worktree Management

| Command | Purpose | JSON Output |
|---------|---------|-------------|
| `tribunal worktree detect --json <slug>` | Check if worktree exists | `{"found": true, "path": "...", "branch": "...", "base_branch": "..."}` |
| `tribunal worktree create --json <slug>` | Create worktree AND register with session | `{"path": "...", "branch": "spec/<slug>", "base_branch": "main"}` |
| `tribunal worktree diff --json <slug>` | List changed files in worktree | JSON with file changes |
| `tribunal worktree sync --json <slug>` | Squash merge worktree to base branch | `{"success": true, "files_changed": N, "commit_hash": "..."}` |
| `tribunal worktree cleanup --json <slug>` | Remove worktree and branch | Deletes worktree directory and git branch |
| `tribunal worktree status --json` | Show active worktree info | `{"active": false}` or `{"active": true, ...}` |

**Slug** = plan filename without date prefix and `.md` (e.g., `2026-02-11-add-auth.md` → `add-auth`).

**Error handling:** `create` returns `{"success": false, "error": "dirty", "detail": "..."}` when the working tree has uncommitted changes. Use `AskUserQuestion` to let the user choose: commit, stash, or skip worktree (see spec-implement Step 2.1b).

### Access & Auth

| Command | Purpose |
|---------|---------|
| `tribunal activate <key> [--json]` | Activate access on this machine |
| `tribunal deactivate` | Deactivate access on this machine |
| `tribunal status [--json]` | Show access and session status |
| `tribunal verify [--json]` | Verify access authorization (used by hooks) |
| `tribunal trial --check [--json]` | Check access eligibility |
| `tribunal trial --start [--json]` | Start access verification |

### Skills Management

| Command | Purpose | Example |
|---------|---------|---------|
| `tribunal skills` | List all project skills (default) | `sfc skills` |
| `tribunal skills list` | List all project skills | `sfc skills list` |
| `tribunal skills show <name>` | Display a skill's content | `sfc skills show deploy-workflow` |
| `tribunal skills init` | Bootstrap .claude/ with project config | `sfc skills init` |
| `tribunal skills analyze` | AI-powered codebase analysis (headless /sync) | `sfc skills analyze` |
| `tribunal skills analyze --dry-run` | Preview analysis without running | `sfc skills analyze --dry-run` |
| `tribunal skills create <name>` | Create skill from template (kebab-case) | `sfc skills create api-client` |
| `tribunal skills doctor` | Validate skill files for issues | `sfc skills doctor` |

### Other

| Command | Purpose |
|---------|---------|
| `tribunal greet [--name NAME] [--json]` | Print welcome banner |
| `tribunal statusline` | Format status bar (reads JSON from stdin, used by Claude Code settings) |

### Commands That Do NOT Exist

Do NOT attempt these — they will fail:
- ~~`tribunal pipe`~~ — Never implemented
- ~~`tribunal update`~~ — Auto-update is built into `tribunal run`
