---
id: rules/delegate
version: 1.0.0
category: tools
tags:
  - tools
deprecated: false
---

## Sub-Agent Delegation via claude-code

Tribunal can delegate heavy file operations to a Claude Code sub-agent via the `claude-code` MCP server. This keeps your main session's context clean and avoids unnecessary compactions.

### When to Delegate

Use `mcp-cli claude-code/claude_code` for:

- **Bulk file edits** — Editing 5+ files with the same pattern (e.g., "add error handling to all route handlers")
- **Shell commands** — Build, install, git operations that don't need conversational context
- **Bulk reads for analysis** — Reading many files to summarize or find patterns
- **TDD GREEN phase** — After writing the failing test (RED), delegate the implementation to the sub-agent. You wrote the test, you know what it needs. Let the sub-agent make it pass.
- **Repetitive refactors** — Rename across files, update imports, migrate API patterns
- **Git operations** — Stage, commit, push, tag workflows

### When NOT to Delegate

Keep in main session:

- **Planning & architecture** — Needs full context and user conversation
- **TDD RED phase** — Writing the failing test requires understanding requirements
- **Verification** — Reviewing sub-agent output, running final checks
- **User interaction** — Anything requiring clarification or decisions
- **Debugging** — Needs iterative context; delegation loses the thread
- **First exploration** — When you don't yet understand the codebase

### Safety Rules

1. **No nesting** — The sub-agent MUST NOT call `claude_code` itself. One level of delegation only.
2. **No concurrent edits** — Do NOT edit files while a sub-agent task is running. Wait for it to complete, then verify.
3. **Verify after delegation** — Always review sub-agent output. Run tests. Check the diff. Trust but verify.
4. **Atomic tasks** — Give the sub-agent a clear, self-contained task. Don't delegate vague or multi-phase work.
5. **Fallback** — If the sub-agent fails or produces bad output, do the task yourself in the main session.
6. **Rate limit** — Maximum **5 delegated tasks per session**. If you have reached this limit, complete remaining work directly in the main session without spawning further sub-agents. The counter resets on session start. This limit exists to prevent runaway delegation chains and unbounded token spend.

### How to Delegate

```bash
# Simple file operation
mcp-cli claude-code/claude_code '{"prompt": "Add input validation to all POST route handlers in src/api/", "workFolder": "/path/to/project"}'

# TDD green phase
mcp-cli claude-code/claude_code '{"prompt": "Make the failing test in tests/test_auth.py::test_login_with_expired_token pass. The test expects a 401 response with error message. See the test file for exact expectations.", "workFolder": "/path/to/project"}'

# Bulk refactor
mcp-cli claude-code/claude_code '{"prompt": "Replace all console.log calls with the logger utility from src/utils/logger.ts across all files in src/", "workFolder": "/path/to/project"}'
```

### Context Savings

Each delegated task runs in an isolated Claude Code session. The file contents, edits, and intermediate steps never enter your main session's context. For a 10-file refactor, this can save 20-50k tokens of context space.

### Prerequisites

- Claude Code installed and authenticated (`claude auth login`)
- `--dangerously-skip-permissions` accepted once (`claude --dangerously-skip-permissions`)
- `claude-code` entry in `mcp_servers.json` (auto-provisioned by Tribunal)
