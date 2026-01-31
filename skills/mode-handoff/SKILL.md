---
name: mode-handoff
description: 'Save comprehensive context to a handoff file for future sessions. Use
  when user appends #o, says "save this context", "handoff", "for next time", or when
  ending a session with important context. Creates a persistent record.'
---

## When to Apply

This mode runs AFTER main work—capture context at the end. Use when important decisions, context, or progress should persist beyond this session. When composed with other modes, handoff runs last to capture everything that happened.

<role>
WHO: Context archivist
ATTITUDE: Future-you will thank present-you for good notes. Capture what matters.
</role>

<purpose>
Your job is to create a handoff document that lets a future session (or different agent) pick up where this one left off without re-deriving everything.
</purpose>

<checkpoint>
## Before creating handoff:

**Session topic:** [one-line summary]

**What was accomplished:** [bullet list of concrete outcomes]

**What's still pending:** [unfinished work, blockers, next steps]

**Key decisions made:** [choices that shouldn't be re-litigated]

**Important context:** [things that aren't obvious but matter]
</checkpoint>

<handoff-format>
Create file at: `<PROJECT_ROOT>/.claude/handoffs/YYYY-MM-DD-<slug>.md`

Where `<slug>` is 2-4 words describing the topic (e.g., `auth-refactor`, `api-design-decisions`).

**File structure:**
```markdown
# Handoff: [Topic]

**Date:** YYYY-MM-DD
**Session:** [brief description of what this session was about]

## Summary
[2-3 sentences capturing the essential context]

## Decisions Made
- **[Decision 1]:** [what was decided and why]
- **[Decision 2]:** [what was decided and why]

## Work Completed
- [x] [Completed item 1]
- [x] [Completed item 2]

## Pending / Next Steps
- [ ] [What still needs to be done]
- [ ] [Blockers or dependencies]

## Files Touched
- `path/to/file1.py` — [what changed]
- `path/to/file2.py` — [what changed]

## Context for Future Sessions
[Anything non-obvious that future-you needs to know. Gotchas, constraints, "we tried X and it didn't work because Y".]

## Related
- [Links to PRs, issues, other handoffs if relevant]
```
</handoff-format>

<anti-closure>
Before writing handoff:
- Would someone with no context understand what happened?
- Did I capture WHY decisions were made, not just WHAT?
- Is the "pending" section actionable, or vague?
- Did I include the non-obvious context that will be forgotten?
</anti-closure>

<rules>
- Create the `.claude/handoffs/` directory if it doesn't exist.
- Use ISO date format (YYYY-MM-DD) for sorting.
- Slug should be lowercase-hyphenated, descriptive.
- Decisions need rationale—"we chose X" is useless without "because Y".
- Files touched should note WHAT changed, not just that they changed.
- "Context for Future Sessions" is the most valuable section—don't skip it.
</rules>

<synthesis>
After creating the handoff, confirm the file path and summarize what was captured. If this is part of ongoing work, note when/how to reference this handoff in the next session.
</synthesis>
