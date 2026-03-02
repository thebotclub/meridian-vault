# Context Continuation - Endless Mode for All Sessions

**Rule:** When context reaches critical levels, save state and continue seamlessly in a new session.

## Quality Over Speed - CRITICAL

**NEVER rush or compromise quality due to context pressure.**

- You can ALWAYS continue in the next session - work is never lost
- A well-done task split across 2 sessions is better than a rushed task in 1 session
- **Quality is the #1 metric** - clean code, proper tests, thorough implementation
- Do NOT skip tests, compress explanations, or cut corners to "beat" context limits

**The context limit is not your enemy.** It's just a checkpoint. The plan file, Skillfield Memory, and continuation files ensure seamless handoff. Trust the system.

### ⛔ But at 90%+, HANDOFF OVERRIDES EVERYTHING

**At 90% context, the handoff IS the quality action.** Failing to hand off means losing ALL work.

- **"Finish current task" means the single tool call in progress** - NOT "fix every remaining error"
- **Do NOT start new fix cycles** at 90%+ (running linters, fixing type errors, running tests)
- **Document remaining errors** in the continuation file for the next session
- The "fix ALL errors" rule is **suspended** at 90%+ - incomplete fixes are expected and acceptable
- The next session will continue exactly where you left off - nothing is lost

## Session Identity

Continuation files are stored under `~/.skillfield/sessions/<session-id>/` where `<session-id>` comes from the `SF_SESSION_ID` environment variable (defaults to `"default"` if not set). This ensures parallel sessions don't interfere with each other's continuation state.

**⚠️ CRITICAL: The context monitor hook prints the EXACT absolute path to use.** Copy the path from the hook output — do NOT try to resolve `$SF_SESSION_ID` yourself. If you need the path before the hook fires, resolve it explicitly:

```bash
echo $SF_SESSION_ID
```

Then construct the path: `~/.skillfield/sessions/<resolved-id>/continuation.md`

## How It Works

This enables "endless mode" for any development session, not just /spec workflows:

1. **Context Monitor** warns at 80% and 90% usage
2. **You save state** to Skillfield Memory before clearing
3. **Skillfield restarts** Claude with continuation prompt
4. **Skillfield Memory injects** your saved state
5. **You continue** where you left off

## When Context Warning Appears

When you see the context warning (80% or 90%), take action:

### At 80% - Prepare for Continuation

1. **Invoke the Context Compressor agent** to synthesize observations into a compact handoff:
   ```
   Skill(skill="context-compressor")
   ```
   This produces `~/.skillfield/sessions/<session_id>/context-summary.md`.

2. Wrap up current task if possible
3. Avoid starting new complex work
4. Review the context-summary.md output and correct any inaccuracies

### At 90% - Mandatory Continuation Protocol

**⚠️ CRITICAL: Execute ALL steps below in a SINGLE turn. DO NOT stop, wait for user response, or output summary and then pause. Write file → Trigger clear → Done.**

**Step 1: VERIFY Before Writing (CRITICAL)**

Before writing the continuation file, you MUST run verification commands:
```bash
# Run the project's test suite (e.g., uv run pytest -q, bun test, npm test)
# Run the project's type checker (e.g., basedpyright src, tsc --noEmit)
```

**DO NOT claim work is complete without showing verification output in the continuation file.**

**Step 2: Check for Active Plan (MANDATORY)**

**⚠️ CRITICAL: You MUST check for an active plan before deciding which handoff command to use.**

```bash
# Check for non-VERIFIED plans (most recent first by filename)
ls -1 docs/plans/*.md 2>/dev/null | sort -r | head -5
```

Then check the Status field in the most recent plan file(s). An **active plan** is any plan with `Status: PENDING` or `Status: COMPLETE` (not `VERIFIED`).

**Decision Tree:**
| Situation | Command to Use |
|-----------|----------------|
| Active plan exists (PENDING/COMPLETE) | `~/.skillfield/bin/skillfield send-clear docs/plans/YYYY-MM-DD-name.md` |
| No active plan (all VERIFIED or none exist) | `~/.skillfield/bin/skillfield send-clear --general` |

**NEVER use `--general` when there's an active plan file. This loses the plan context!**

**Step 3: Write Session Summary to File (GUARANTEED BACKUP)**

Write the summary using the Write tool to the **exact path printed by the context monitor hook** (Step 1 in the hook output). The path is an absolute path like `/Users/you/.skillfield/sessions/12345/continuation.md`. **Do NOT use `$SF_SESSION_ID` as a literal string in the file path — the Write tool cannot resolve shell variables.**

Include VERIFIED status with actual command output.

```markdown
# Session Continuation

**Task:** [Brief description of what you were working on]
**Active Plan:** [path/to/plan.md or "None"]

## VERIFIED STATUS (run just before handoff):
- Test suite → **X passed** or **X failed** (be honest!)
- Type checker → **X errors** or **0 errors**
- If tests fail or errors exist, document WHAT is broken

## Completed This Session:
- [x] [What was VERIFIED as finished]
- [ ] [What was started but NOT verified/complete]

## IN PROGRESS / INCOMPLETE:
- [Describe exactly what was being worked on]
- [What command was being run]
- [What error or issue was being fixed]

## Next Steps:
1. [IMMEDIATE: First thing to do - be SPECIFIC]
2. [Include exact file:line if fixing something]

## Files Changed:
- `path/to/file.py` - [what was changed]
```

**CRITICAL: If you were in the middle of fixing something, say EXACTLY what and where. The next agent cannot read your mind.**

**Step 4: Output Summary AND Trigger Clear (SAME TURN)**

Output brief summary then IMMEDIATELY trigger clear in the same response:

```
🔄 Session handoff - [brief task description]. Triggering restart...
```

Then execute the send-clear command (do NOT wait for user response):

**Use the correct command based on Step 2:**

```bash
# If active plan exists (PREFERRED - preserves plan context):
~/.skillfield/bin/skillfield send-clear docs/plans/YYYY-MM-DD-name.md

# ONLY if NO active plan exists:
~/.skillfield/bin/skillfield send-clear --general
```

This triggers session continuation in Endless Mode:
1. Waits 10s for Skillfield Memory to capture the session
2. Waits 5s for graceful shutdown (SessionEnd hooks run)
3. Waits 5s for session hooks to complete
4. Waits 3s for Skillfield Memory initialization
5. Restarts Claude with the continuation prompt

Or if no active session, inform user:
```
Context at 90%. Please run `/clear` and then tell me to continue where I left off.
```

**Step 4: After Restart**

The new session receives:
- Skillfield Memory context injection (including your Session End Summary)
- A continuation prompt instructing you to resume

### At 95%+ - EMERGENCY HANDOFF

**⚠️ CRITICAL OVERRIDE: At 95%+, skip ALL verification. Two steps only.**

When context is at or above 95%, running tests, type checkers, or linters is too expensive — it will push the session over 100% and lose ALL work. Skip everything except the minimum required for the next session to continue.

**EMERGENCY HANDOFF — 2 steps only, in a SINGLE turn:**

**Step 1: Write minimal continuation file**

Write to the exact path from the context monitor hook output:

```markdown
# EMERGENCY HANDOFF — Context at 95%+

**Task:** [One sentence: what you were doing]
**Active Plan:** [path/to/plan.md or "None"]

## Last Action:
[The LAST tool call or file you were editing]

## Next Steps:
1. [IMMEDIATE: the very next action to take, as specific as possible]

## NOTE: No verification run — context was at 95%+. Run tests first before continuing.
```

**Step 2: Trigger send-clear immediately**

```bash
# If active plan exists:
~/.skillfield/bin/skillfield send-clear docs/plans/YYYY-MM-DD-name.md

# If no active plan:
~/.skillfield/bin/skillfield send-clear --general
```

**DO NOT:**
- Run tests, linters, or type checkers
- Write a full session summary
- Check git status
- Ask the user anything

**The next session will run verification before continuing work.**

## ⛔ MANDATORY: Clean Up Stale Continuation Files at Session Start

**At the START of EVERY session (not just continuation sessions), delete any stale continuation file:**

```bash
rm -f ~/.skillfield/sessions/$SF_SESSION_ID/continuation.md
```

**Why this is critical:** Stale continuation files from previous sessions cause the Write tool to fail (it requires reading before writing). If the stale file contains old context, it can corrupt the handoff. This cleanup MUST happen before any work begins — even in quick-mode sessions that aren't continuations.

**When to clean up:**
- At the very start of every new session
- Before writing a new continuation file (as a safety net)
- The `send-clear` command does NOT guarantee the file is deleted

## Resuming After Session Restart

When a new session starts with a continuation prompt:

1. **Resolve session ID and read continuation file:**
   ```bash
   # Resolve the actual session ID first
   echo $SF_SESSION_ID
   ```
   Then use the Read tool with the resolved absolute path (e.g., `~/.skillfield/sessions/12345/continuation.md`). **Do NOT pass `$SF_SESSION_ID` to the Read tool — resolve it first.**

2. **Delete the continuation file after reading it:**
   ```bash
   rm -f ~/.skillfield/sessions/$SF_SESSION_ID/continuation.md
   ```

3. **Also check Skillfield Memory** for injected context about "Session Continuation"

4. **Acknowledge the continuation** - Tell user: "Continuing from previous session..."

5. **Resume the work** - Execute the "Next Steps" from the continuation file immediately

## Integration with /spec

If you're in a /spec workflow (plan file exists):
- Use the existing `/spec --continue <plan-path>` mechanism
- The plan file is your source of truth

If you're in general development (no plan file):
- Use this continuation protocol
- Skillfield Memory observations are your source of truth

## Quick Reference

| Context Level | Action |
|---------------|--------|
| < 80% | Continue normally |
| 80-89% | Wrap up current work, avoid new features |
| 90-94% | **MANDATORY:** Verify → Save state → Clear session → Continue |
| ≥ 95% | **EMERGENCY:** Skip verification → Write minimal file → send-clear → Done |

## Skillfield Commands for Endless Mode

```bash
# Check context percentage
~/.skillfield/bin/skillfield check-context --json

# Trigger session continuation (no continuation prompt)
~/.skillfield/bin/skillfield send-clear

# Trigger continuation WITH plan (PREFERRED when plan exists):
~/.skillfield/bin/skillfield send-clear docs/plans/YYYY-MM-DD-name.md

# Trigger continuation WITHOUT plan (ONLY when no active plan):
~/.skillfield/bin/skillfield send-clear --general
```

**⚠️ ALWAYS check for active plans before using `--general`. See Step 2 above.**

## Important Notes

1. **Don't ignore 90% warnings** - Context will fail at 100%
2. **Save before clearing** - Lost context cannot be recovered
3. **Skillfield Memory is essential** - It bridges sessions with observations
4. **Trust the injected context** - It's your previous session's state
