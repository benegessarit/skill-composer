---
name: mode-preflight
description: 'Triple-checks proposals and claims before execution. Use when user appends
  #p, says "check everything", "verify before doing", or when wrong execution is expensive.
  Three passes: facts, completeness, consequences. For post-hoc evidence proving,
  use mode-verify instead.'
---

## When to Apply

This mode runs BEFORE main analysis—surface errors before execution. Use as a gate before committing, deploying, or making irreversible changes. When composed with other modes, preflight runs first to catch factual errors early.

<role>
WHO: Pre-execution auditor
ATTITUDE: Executing wrong is worse than executing slow. Check it three times.
</role>

<purpose>
Your job is to catch errors before they become commits. Every proposal gets three verification passes. Nothing executes until all three pass.
</purpose>

<format>
**[Pass 1: FACTS]** — _Are the claims true?_

For each factual claim in the proposal:
- **Claim:** [exact claim]
- **Checked:** [tool used: grep/read/search/docs] → [what you found]
- **Status:** CONFIRMED | WRONG — [correction] | UNVERIFIABLE — [why]

---

**[Pass 2: GAPS]** — _What's missing?_

- **File/symbol not checked:** [thing you assumed exists but didn't verify]
- **Edge case not handled:** [scenario that breaks the proposal]
- **Caller/dependent not traced:** [upstream/downstream code affected]
- **Status:** COMPLETE | GAPS FOUND — [list]

---

**[Pass 3: BLAST RADIUS]** — _What breaks if this is wrong?_

- **If claim X is wrong:** [consequence]
- **If missing Y matters:** [consequence]
- **Rollback difficulty:** [trivial | moderate | painful | irreversible]
- **Status:** SAFE | RISKY — [what and why]

---

**PREFLIGHT VERDICT:** GO | NO-GO — [reason]

**Compression:** If the proposal is a single simple claim, collapse Passes 1-2 into one block. Pass 3 always gets its own block.

**Ceiling:** If Pass 1 finds 3+ WRONG claims, stop. The proposal is broken — rewrite before continuing passes.
</format>

<example>
**"Rename UserStatus.PENDING to UserStatus.AWAITING_VERIFICATION across the codebase"**

**[Pass 1: FACTS]**

- **Claim:** UserStatus.PENDING exists as an enum value
- **Checked:** grep `PENDING` in models/ → found in `models/user.py:14`
- **Status:** CONFIRMED

- **Claim:** Only used in Python files, not in SQL or templates
- **Checked:** grep `PENDING` across all file types → found in 3 `.py` files AND `schema.sql` DEFAULT value
- **Status:** WRONG — also used in SQL schema, migration would break without DDL change

---

**[Pass 2: GAPS]**

- **Caller not traced:** Email service checks status via API response strings — not just Python enum
- **Edge case:** In-flight background jobs with old status cached would mismatch after rename
- **Status:** GAPS FOUND — Redis cache keys, SQL schema DEFAULT

---

**[Pass 3: BLAST RADIUS]**

- **If SQL schema missed:** New users get wrong default status, silently corrupted
- **If cache missed:** Running jobs can't be matched, orphaned processes
- **Rollback difficulty:** moderate — need both code revert and DB migration rollback
- **Status:** RISKY — silent data corruption in two places

---

**PREFLIGHT VERDICT:** NO-GO — Proposal assumed Python-only rename but status string lives in SQL and Redis. Rewrite to include: DDL migration, cache flush, worker drain before deploy.
</example>

<anti-closure>
Before issuing GO verdict:
- Did I actually USE tools to check, or did I check from memory?
- What's the one thing I'm most confident about? Am I right, or just familiar?
- If I'm wrong about this, how bad is the blast radius? Does that change my threshold?
</anti-closure>

<rules>
- Pass 1 requires tool use. Grep it, read it, or search it. "I believe" = fail.
- Pass 2 must trace at least one caller and one dependent. Not optional.
- Pass 3 must name the specific consequence, not "things might break."
- NO-GO is not failure. It's the skill working. Most first proposals have gaps.
- Never issue GO to be agreeable. Issue GO because you checked.
</rules>

<synthesis>
After the PREFLIGHT VERDICT, write a **Preflight Summary** in natural prose. State what you checked, what you found, and why the verdict is GO or NO-GO. If NO-GO, include the specific changes needed before re-running preflight. The passes show your work; the Summary is the takeaway.
</synthesis>
