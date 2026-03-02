# Contributing to Meridian Vault

Thank you for your interest in contributing to the Meridian Vault!

## Getting Started

1. Fork the repository and clone it locally
2. Explore the vault structure: `rules/`, `commands/`, `agents/`, `hooks/`
3. Install Python dependencies if working on hooks: `uv sync`

## PR Checklist

Before submitting a pull request, ensure:

- [ ] Linting passes on hook scripts: `uv run ruff check hooks/`
- [ ] `hooks/hooks.json` is valid JSON: `python3 -m json.tool hooks/hooks.json`
- [ ] All referenced Python scripts in hooks.json exist
- [ ] Markdown files are well-formed and spell-checked
- [ ] Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/)

## Code Style

### Ruff

For `.py` files in `hooks/`:

```bash
uv run ruff check hooks/
uv run ruff format hooks/
```

### basedpyright

For type checking hook scripts:

```bash
uv run basedpyright hooks/
```

## Vault Contribution Quality Criteria

When adding new vault assets, ensure:

- **Rules** — are actionable and specific; avoid vague guidance; include examples
- **Commands** — slash commands must have a clear trigger, purpose, and expected output
- **Agents** — include a description of when to invoke and what the agent checks for
- **Hooks** — must be tested locally; async hooks must not block the main loop
- **Modes** — localized modes must be reviewed by a native speaker where possible

## Questions?

Open a [GitHub Discussion](https://github.com/thebotclub/meridian-vault/discussions) for general questions.
