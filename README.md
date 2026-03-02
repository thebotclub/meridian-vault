# 🏛️ Meridian Vault

**The shared library of AI coding skills, rules, agents, hooks, and MCP configs for [Meridian](https://github.com/skill-field/skillfield-code).**

Every skill you create, every rule you refine, every workflow you perfect — it lives here. Pull what you need, push what you build. The vault grows with every developer who uses it.

---


## Requirements

- **Node.js** (v18+) or **Bun** — required for the worker service hooks
- **Python** 3.12 — required for hook scripts
- **uv** — Python package runner used by hooks

## What's Inside

| Category | Count | Description |
|----------|-------|-------------|
| **Rules** | 35 | Coding standards, workflow enforcement, language-specific rules, tool integrations |
| **Commands** | 7 | Slash commands (`/spec`, `/sync`, `/learn`, `/vault`, etc.) |
| **Agents** | 4 | Verification sub-agents (plan-verifier, plan-challenger, reviewers) |
| **Hooks** | 9 | Quality automation (TDD enforcer, context monitor, file checker, etc.) |
| **Modes** | 30 | Localized coding modes (30 languages) |
| **MCP Configs** | 2 | Pre-configured MCP server definitions |
| **Skills** | 1 | Reusable skill packages |

---

## Structure

```
vault/
├── rules/                    # AI coding rules
│   ├── workflow/             # Development workflow rules
│   │   ├── tdd-enforcement.md
│   │   ├── context-continuation.md
│   │   ├── workflow-enforcement.md
│   │   ├── verification-before-completion.md
│   │   └── ...
│   ├── quality/              # Code quality rules
│   │   ├── coding-standards.md
│   │   ├── commit.mdc
│   │   ├── bug-fix.mdc
│   │   └── ...
│   ├── language/             # Language-specific rules
│   │   ├── python-rules.md
│   │   ├── typescript-rules.md
│   │   └── golang-rules.md
│   ├── tools/                # Tool integration rules
│   │   ├── gh-cli.md
│   │   ├── vexor-search.md
│   │   └── ...
│   └── standards/            # Conditional coding standards
│       ├── standards-api.md
│       ├── standards-css.md
│       └── ...
├── commands/                 # Slash commands
│   ├── spec.md               # /spec — spec-driven development
│   ├── sync.md               # /sync — codebase analysis
│   ├── learn.md              # /learn — extract skills from sessions
│   └── vault.md              # /vault — manage this vault
├── agents/                   # Verification sub-agents
│   ├── plan-verifier.md
│   ├── plan-challenger.md
│   ├── spec-reviewer-compliance.md
│   └── spec-reviewer-quality.md
├── hooks/                    # Quality automation hooks
│   ├── tdd_enforcer.py
│   ├── context_monitor.py
│   ├── file_checker.py
│   ├── tool_redirect.py
│   ├── spec_stop_guard.py
│   ├── hooks.json            # Hook registration
│   └── checkers/             # Language-specific checkers
│       ├── python.py
│       ├── typescript.py
│       ├── go.py
│       └── secrets.py
├── modes/                    # Localized coding modes
│   ├── code.json             # Default (English)
│   ├── code--ja.json         # Japanese
│   ├── code--de.json         # German
│   └── ... (30 languages)
├── mcp/                      # MCP server configurations
│   └── mcp_servers.json
└── skills/                   # Reusable skill packages
    └── update-refs/
        └── SKILL.md
```

---

## Usage

### Pull skills from the vault

```bash
# Configure vault (first time)
meridian init --type git --repo-url https://github.com/thebotclub/meridian-vault.git
# Note: `sx` is a companion CLI — install via `pip install skillfield-sx`

# Install all vault assets to your project
meridian install --repair --target .

# Or from within Meridian
> /vault
> Pull
```

### Push new skills to the vault

When you create a new skill, rule, or command that others could use:

```bash
# From within Meridian
> /vault
> Push

# Or via CLI
meridian add .claude/skills/my-skill --yes --type skill --name "my-skill"
```

### Browse the vault

```bash
# List everything
meridian vault list

# Show details for a specific asset
meridian vault show <asset-name>

# Or from within Meridian
> /vault
> Browse
```

---

## Contributing

Every developer using Meridian can contribute to the vault:

1. **Create a skill** — Use `/learn` during a session to extract reusable knowledge
2. **Push to vault** — Use `/vault` → Push to share with the community
3. **Quality matters** — Skills should be well-documented, tested, and genuinely useful

### What makes a good vault contribution?

- ✅ Solves a real, recurring problem
- ✅ Well-documented with clear examples
- ✅ Works across different project structures
- ✅ Doesn't duplicate existing vault assets
- ❌ Project-specific rules (keep those local)
- ❌ Secrets or credentials (obviously)

---

## Categories Explained

### Rules
Rules are instructions that Claude follows during coding sessions. They're activated automatically based on context:
- **Workflow rules** — How to develop (TDD, verification, handoff)
- **Quality rules** — Code standards, commit messages, reviews
- **Language rules** — Python/TypeScript/Go specific patterns
- **Tools rules** — How to use MCP servers, CLI tools, search
- **Standards** — Conditional standards activated by file type (.css, .tsx, etc.)

### Commands
Slash commands that extend Claude Code with structured workflows. `/spec` for planning, `/sync` for codebase analysis, `/learn` for knowledge extraction.

### Agents
Sub-agent definitions for verification. These run independently to validate plans and review code from different perspectives.

### Hooks
Python scripts that fire automatically on file edits, context changes, and session events. The quality backbone of Meridian.

### Modes
Localized system prompts for coding in 30+ languages. The coding instructions stay in English (code is code), but communication adapts to the developer's language.

---

<div align="center">

**The vault grows with every developer who uses Meridian.**

</div>
