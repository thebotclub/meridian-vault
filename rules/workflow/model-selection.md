# Model Selection Guidance

Tribunal supports configuring a default Claude model (or any compatible model) via `tribunal model set <model-id>`.
Choose the right model for the task to balance capability, speed, and cost.

## When to Use Each Model

### Claude Opus 4.5 / Opus 4 — Complex Tasks
Use Opus when:
- Designing system architecture or writing technical specifications
- Running spec planning sessions that need deep reasoning
- Acting as a verification or review agent (spec-reviewer-quality checks)
- Debugging subtle, multi-layered problems
- Evaluating trade-offs across complex design spaces

> The `spec-reviewer-quality` agent in this vault uses Opus because verifying
> specification compliance requires deep reasoning and holistic understanding
> of requirements, design constraints, and implementation nuances — tasks
> where speed is less important than correctness.

### Claude Sonnet 4.5 / Sonnet 4 — Day-to-Day Work (Recommended Default)
Use Sonnet when:
- Implementing features in standard TDD cycles (red → green → refactor)
- Writing or reviewing code during normal sprints
- Refactoring, adding tests, updating documentation
- Most interactive coding sessions

Sonnet is the recommended default. It covers the vast majority of development
work well, and is significantly faster and cheaper than Opus.

### Claude Haiku 3.5 — Quick, Lightweight Tasks
Use Haiku when:
- Looking up a fact, checking a config value, or confirming a setting
- Simple, bounded edits (rename a variable, fix a typo, update a version)
- Context checks (what files are open, what is the current plan status)
- Running as a fast helper agent in a multi-agent pipeline

### Third-Party / Custom Models — Passthrough
Claude Code supports OpenAI-compatible models via its `--model` flag. Any model ID
can be set and it will be passed through to Claude Code without validation. Examples:

| Model ID | Provider | Notes |
|---|---|---|
| `minimax/MiniMax-Text-01` | MiniMax | Long-context model |
| `THUDM/glm-4-9b-chat` | THUDM | Open-source GLM model |
| `google/gemini-2.0-flash` | Google | Fast multimodal model |
| `openai/gpt-4o` | OpenAI | Multimodal flagship |
| `deepseek/deepseek-r1` | DeepSeek | Reasoning model |

Claude Code will return an error if the model ID is invalid or not available in
your configured provider environment.

## Configuring the Default Model

```bash
# List all available models (built-in + examples + your custom list)
tribunal model list

# Show current default
tribunal model get

# Set a built-in Claude model as default
tribunal model set claude-sonnet-4-5

# Set a third-party model (passthrough — no validation)
tribunal model set minimax/MiniMax-Text-01

# Set any model, suppressing the unrecognised-model warning
tribunal model set some-custom-id --force

# Save a custom model to your list (appears in tribunal model list)
tribunal model add minimax/MiniMax-Text-01 --name "MiniMax Text 01" --provider "MiniMax"
tribunal model add THUDM/glm-4-9b-chat --name "GLM-4" --provider "THUDM"

# Remove a custom model from your list
tribunal model remove THUDM/glm-4-9b-chat

# Override just for one session (does not persist)
tribunal launch --model claude-opus-4-5

# Override AND save as new default
tribunal launch --model claude-opus-4-5 --save

# Reset to Claude Code's built-in default
tribunal model clear
```

## Config Schema

`~/.tribunal/config.json`:
```json
{
  "model": "claude-sonnet-4-5",
  "custom_models": [
    {"id": "minimax/MiniMax-Text-01", "name": "MiniMax Text 01", "provider": "MiniMax"},
    {"id": "THUDM/glm-4-9b-chat", "name": "GLM-4", "provider": "THUDM"}
  ]
}
```

## Built-in Model IDs Reference

| Model ID | Display Name | Best For |
|---|---|---|
| `claude-opus-4-5` | Claude Opus 4.5 | Complex tasks, architecture, spec review |
| `claude-sonnet-4-5` | Claude Sonnet 4.5 | Day-to-day implementation (recommended) |
| `claude-haiku-3-5` | Claude Haiku 3.5 | Quick lookups, simple edits |
| `claude-opus-4` | Claude Opus 4 | Previous-gen highly capable |
| `claude-sonnet-4` | Claude Sonnet 4 | Previous-gen balanced |
| `claude-3-7-sonnet-20250219` | Claude Sonnet 3.7 | Extended thinking support |

Custom and third-party model IDs are supported without validation — pass any model ID
and Claude Code will handle the error if it's not recognised.
