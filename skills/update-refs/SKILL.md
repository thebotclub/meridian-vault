---
name: update-refs
description: Update naming and documentation references across the Tribunal codebase. Use when renaming features, updating descriptions, changing terminology, or ensuring consistency after modifying commands, skills, or workflows. Triggers on "update references", "rename X to Y across codebase", "sync documentation", or "update all mentions of X".
version: 1.2.0
---

# Update References

Ensure naming and documentation consistency across all codebase locations.

## Checklist

When updating terminology, feature names, descriptions, or counts, check ALL locations:

### 1. User-Facing Messages

| Location | What to Check |
|----------|---------------|
| `launcher/banner.py` | Welcome banner text, feature descriptions |
| `launcher/cli.py` | Pilot CLI help text and messages |
| `installer/cli.py` | Installer CLI help text, prompts |
| `installer/steps/finalize.py` | Post-install instructions |
| `installer/ui.py` | UI banner and status messages |

### 2. Documentation

| Location | What to Check |
|----------|---------------|
| `README.md` | Feature descriptions, usage examples, Before & After table |
| `docs/Tribunal - Internal Guide.md` | Internal documentation and guides |
| `CHANGELOG.md` | Version history and release notes |

### 3. Package & Install

| Location | What to Check |
|----------|---------------|
| `pyproject.toml` | Package name, description, metadata |
| `install.sh` | Shell installer script messages |
| `launcher/__init__.py` | Package docstring |

### 4. Tribunal Plugin (sf/ directory)

| Location | What to Check |
|----------|---------------|
| `sf/commands/*.md` | Command descriptions (`spec`, `sync`, `vault`, `learn`, plus internal phases) |
| `sf/rules/*.md` | Standard rules content |
| `sf/hooks/hooks.json` | Hook configuration and event triggers |
| `sf/hooks/*.py` | Hook script messages and logic |
| `sf/agents/*.md` | Sub-agent definitions (plan-verifier, plan-challenger, spec-reviewer-*) |
| `sf/settings.json` | LSP server configuration |
| `sf/modes/*.json` | Language mode definitions |

### 5. Project-Level Claude Config

| Location | What to Check |
|----------|---------------|
| `.claude/rules/*.md` | Project-specific rules (git-commits.md, project.md) |
| `.claude/skills/*/SKILL.md` | Project-specific skills (lsp-cleaner, pr-review, update-refs) |

## No Hardcoded Counts

**Do NOT add specific counts (e.g., "22 rules", "7 hooks", "14 skills") to user-facing text.**

The project deliberately avoids quantity-focused messaging. Use qualitative descriptions instead:

| ❌ Don't | ✅ Do |
|----------|-------|
| "22 rules loaded every session" | "Production-tested rules loaded every session" |
| "7 hooks auto-lint on every edit" | "Hooks auto-lint, format, type-check on every edit" |
| "14 coding skills" | "Coding skills activated dynamically" |
| "5 MCP servers + 3 LSP servers" | "MCP servers + language servers pre-configured" |
| "2,900+ lines of best practices" | "Production-tested best practices" |

**Why:** Quality over quantity. Counts become stale and create maintenance burden across many files. The value is in what the system does, not how many components it has.

## Workflow

1. **Search first** - Use Grep to find all occurrences:
   ```
   Grep pattern="old term" glob="*.{md,py,tsx,json,ts}"
   ```

2. **Update systematically** - Work through checklist above, section by section

3. **Verify consistency** - Search again to confirm no misses:
   ```
   Grep pattern="old term" glob="*.{md,py,tsx,json,ts}"
   ```

4. **Build website** - Verify site compiles after changes:
   ```bash
   cd docs/site && npm run build
   ```

## Common Updates

| Change Type | Key Locations |
|-------------|---------------|
| Command rename/add | sf/commands/*.md, README.md |
| Rule add/remove | sf/rules/*.md, README.md |
| Hook change | sf/hooks/hooks.json, sf/hooks/*.py, README.md |
| Feature description | launcher/banner.py, README.md, Internal Guide |
| Workflow change | sf/commands/*.md, sf/rules/*.md, README.md |
| Package rename | pyproject.toml, install.sh, launcher/__init__.py, README.md |
| Installer message | installer/cli.py, installer/ui.py, installer/steps/*.py |
| Terminology change | Search all locations in checklist above — grep for old term, replace everywhere |
