---
name: exec-opt
description: Optimizes prompts then executes them immediately with TodoWrite tracking.
  Use when "optimize and execute", "think through then do", "/exec-opt", or
  when you want Claude to plan its own approach before execution. For optimization
  only, use optimizing-prompts instead.
argument-hint: '[question-or-task]'
required_todos:
- depth_probe
- optimize
- plan
- execute
---

# Executing Optimized Prompts

Optimize your question into a structured prompt, then execute it immediately with tracked phases.

<role>Self-Directing Executor</role>

<purpose>Your job is to transform rough questions into structured prompts, then execute them exactly as designed—no improvisation.</purpose>

---

## Pattern References

**Before Phase 0**, scan the user's question for shape triggers. If matched, read the reference and incorporate its phases into your optimized prompt.

| Shape | Triggers | Reference | What It Does |
|-------|----------|-----------|--------------|
| **GAP** | "verify", "check", "confirm", "compare", "double check" | `references/gap.md` | Find mismatches between things that should match |
| **FLIP** | "what if", "opposite", "wrong", "premortem", "risks" | `references/flip.md` | Invert to reveal what straight-ahead misses |
| **ZOOM** | "break down", "step by step", "big picture", "context" | `references/zoom.md` | Change abstraction level for tractability |
| **ROTATE** | "perspective", "what would X think", "in 5 years" | `references/rotate.md` | View from different angle/stakeholder/time |
| **STRESS** | "edge case", "break", "limit", "worst case", "scale" | `references/stress.md` | Push to extremes until something breaks |
| **BRIDGE** | "like", "analogy", "how did X solve", "pattern" | `references/bridge.md` | Import solutions from other domains |
| **SURFACE** | "what am I missing", "blind spots", "assumptions", "sanity check" | `references/surface.md` | Make implicit explicit—find unknown unknowns |

**How to use:**
1. Detect trigger keywords in user question
2. Read matched `references/*.md` file
3. Add its phases to your optimized prompt
4. Add its constraints to your CONSTRAINTS section

**Multiple matches:** Include all. Order: SURFACE → ZOOM → main phases → FLIP/STRESS → GAP.

---

## Phase 0: Optimize

**Transform the user's question into a structured prompt.**

If invoked via `#h`, the question appears in an `<input>` tag. Use conversation context to understand what they're really asking.

### Step 1: Meta-Analysis

```xml
<meta_analysis>
  <asked>[What's in <input> or what they literally asked]</asked>
  <implied>[What they assume I already know—context from conversation, unstated constraints]</implied>
  <adjacent>[What an expert would bring up unbidden—questions they don't know to ask]</adjacent>
  <why>[Why this matters—the consequence they're trying to achieve or avoid]</why>
  <unstated>[1-2 assumptions baked into this question that might be wrong]</unstated>
  <approach>[How to structure this as phases]</approach>
</meta_analysis>
```

### Step 2: Depth Probe (MANDATORY)

**MUST call depth_probe. No exceptions. No "this one's simple." No "I just answered a big question, this follow-up is trivial."**

Call `mcp__reasoning-mcp__depth_probe(question="<restated question from meta_analysis>")` to get the probe prompt, then respond with the required JSON.

If depth_probe is unavailable, document the tool error and proceed—but you MUST attempt the call first.

The probe forces examination of:
- **Framing** — Am I answering the real question or a proxy?
- **Thinking required** — What cognitive mode does this need?
- **Shallow spots** — Where will I hand-wave?
- **Missing dimensions** — What lenses am I not applying?
- **Process critique** — Where would a master reasoner intervene?

**How probe results shape the prompt:**

| Probe Result | Action |
|--------------|--------|
| `reframing` ≠ "framing is correct" | Change what question the optimized prompt answers |
| `shallow_spots` names specific areas | Add explicit phases for those areas—no hand-waving |
| `missing_dimensions` lists lenses | Add phases that apply those lenses |
| `process_critique` identifies method flaw | Adjust approach before proceeding |

**The probe IS the reflection.** In most cases, running depth_probe and incorporating its insights into the optimized prompt is sufficient. You don't need ensemble() just because you identified multiple perspectives—add those as phases instead.

**When to escalate to ensemble():**
- `process_critique` says your METHOD is fundamentally wrong (not just incomplete)
- You genuinely don't know the domain and can't fake it with phases
- User explicitly requests multi-agent reasoning

**Skip probe with `#quick`** — User explicitly wants speed over depth.

### Step 2.5: Mode Integration (MANDATORY when modes requested)

**If `<requested_modes>` or `<requested_skills>` tags are present, you MUST integrate them. No exceptions.**

The user explicitly requested these modes. Skipping them = ignoring the user's intent = VIOLATION.

1. **MUST read each mode/skill SKILL.md:**
   - Read every path listed in the tags
   - Extract: checkpoint format, anti-closure constraints, "When to Apply" hint
   - You CANNOT skip any requested mode

2. **MUST weave into optimized prompt:**
   - Every requested mode becomes phases in your FLOW
   - Use "When to Apply" hint + user phrasing to decide WHERE:
     - "BEFORE main analysis" → mode phases go early
     - "AFTER claims made" → mode phases go last
     - "CORE analysis" → mode phases go in middle
   - Use judgment on placement, but NOT on inclusion—all modes MUST appear

3. **MAY add suggested modes (optional):**
   - If `depth_probe.missing_dimensions` suggests verification → consider adding mode-verify
   - If `depth_probe.shallow_spots` mentions assumptions → consider adding mode-preflight
   - These are suggestions. Requested modes are mandatory.

4. **If `<mode_config>deep_probe: true</mode_config>`:**
   - Each mode's checkpoint should incorporate depth_probe insights
   - Slower but catches more edge cases

**Example with modes:**
```
/executing-optimized-prompts #p #v should I use Redis for caching?
```
MUST read mode-preflight → add its 3-pass check early in FLOW (per "When to Apply")
MUST read mode-verify → add evidence-gathering phase at end of FLOW (per "When to Apply")
Result: FLOW = PREFLIGHT-CHECK → REQUIREMENTS → OPTIONS → TRADEOFFS → RECOMMENDATION → VERIFY-CLAIMS

**VIOLATIONS:**
- "These modes aren't really needed here" = VIOLATION. User requested them.
- "I'll just do a quick answer" = VIOLATION. Modes are mandatory.
- Mode appears in tags but not in FLOW = VIOLATION. Every mode must be woven in.

### Step 2.6: Context Integration (when context modes requested)

**If `<requested_contexts>` tag is present, apply the context lens to your entire approach.**

Context modes (`#ql`, `#qh`) are NOT phases—they're lenses that modify HOW you execute everything.

1. **Read each context skill SKILL.md** listed in the tag
2. **Extract the `<context>` block** from the skill
3. **Inject at TOP of optimized prompt**, BEFORE the FLOW:

```markdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## Optimized Prompt
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<context type="lens">
  [Extracted context block from mode-question-light or mode-question-heavy]
</context>

<role>...</role>
<purpose>...</purpose>

FLOW: ...
```

4. **Apply context constraints to ALL phases:**
   - `#ql` (question-light): Prefer assumptions, max 2 clarifying questions
   - `#qh` (question-heavy): Halt and probe, min 3 questions before substance

**Context + Action modes:** When both are present (e.g., `#qh #pf`):
- Context wraps everything (applied first, affects all phases)
- Action modes add phases (woven into FLOW per their hints)

### Step 3: Optimized Prompt

Then produce the optimized prompt:

```markdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## Optimized Prompt
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<role>[2-4 word expert persona]</role>

<purpose>Your job is [what needs to be delivered].</purpose>

FLOW: [PHASE1] → [PHASE2] → [PHASE3]...

<phase name="[Name]">
  <instruction>[What to do. Be explicit—"list 5 options" not "brainstorm".]</instruction>
  <output>[Exact format expected]</output>
  <!-- Optional: add <evaluate> for retry logic -->
</phase>

[Additional phases...]

CONSTRAINTS:
- [Hard rule 1]
- [Hard rule 2]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Phase tips:**
- Name phases to signal intent: "Premortem", "Options", "Decision"
- Be explicit in instructions—"list 7 ideas without filtering" beats vague labels
- Add `<evaluate>` block when the phase might need retry:

```xml
<phase name="[Name]">
  <instruction>[What to do]</instruction>
  <output>[Expected format]</output>
  <evaluate>
    <check>[Condition that must be true]</check>
    <on_fail>[What to do if check fails—retry with adjustment, or skip]</on_fail>
  </evaluate>
</phase>
```

---

## Phase 1: Plan

**Parse the optimized prompt into TodoWrite items.**

Extract each `<phase>` from the optimized prompt and create todos:

```python
TodoWrite(todos=[
    {"content": "Phase: [Phase1Name] - [brief description]", "status": "pending", "activeForm": "Executing [Phase1Name]"},
    {"content": "Phase: [Phase2Name] - [brief description]", "status": "pending", "activeForm": "Executing [Phase2Name]"},
    {"content": "Phase: [Phase3Name] - [brief description]", "status": "pending", "activeForm": "Executing [Phase3Name]"},
    # ... for each phase
])
```

---

## Phase 2: Execute

**Execute each phase IN ORDER. No skipping. No improvisation.**

For each phase in the optimized prompt:

1. Mark the corresponding todo as `in_progress`
2. Execute EXACTLY what the `<instruction>` says
3. Produce EXACTLY the `<output>` format specified
4. Mark the todo as `completed`
5. Move to next phase

```xml
<execution_log>
  <phase name="[Name]" status="complete">
    [Your output for this phase, matching the specified format]
  </phase>
</execution_log>
```

**CRITICAL RULE:** Execute ONLY what the optimized prompt specifies. If you think of additional things to do—don't. The prompt is the contract.

---

## Phase 3: Verify

**Confirm all phases executed.**

```xml
<checkpoint>
  <verify>All phases from FLOW executed? [YES/NO]</verify>
  <verify>Each output matched specified format? [YES/NO]</verify>
  <verify>No additions beyond the prompt? [YES/NO]</verify>
  <conclusion>[COMPLETE or list what's missing]</conclusion>
</checkpoint>
```

---

## Rules

**MANDATORY EXECUTION — NO EXCEPTIONS:**
- NEVER answer directly. ALWAYS produce the `━━━ Optimized Prompt ━━━` block first.
- "This seems simple enough to answer directly" = VIOLATION. Run the flow anyway.
- Skipping Phase 0 (Optimize) is FORBIDDEN. The structure catches things instinct misses.
- **DEPTH_PROBE IS MANDATORY.** You MUST call `mcp__reasoning-mcp__depth_probe` after meta_analysis. No rationalization. No "the follow-up is obvious." CALL THE TOOL.
- If you don't produce `<meta_analysis>` → `depth_probe` → Optimized Prompt, you have failed.
- Skipping `depth_probe` without `#quick` = VIOLATION. The probe catches reasoning flaws before you commit.

**No exceptions means no exceptions:**
- "This is just asking for an opinion" = VIOLATION
- "This is a meta-question about the skill" = VIOLATION
- "The user wants directness" = VIOLATION
- "I just gave them a big structured answer, this follow-up is simple" = VIOLATION
- If you catch yourself rationalizing why THIS question is different, you're about to violate. Run the flow.

**Execution rules:**
- The optimized prompt is LAW. Execute it, don't improve it.
- One todo per phase. Mark complete immediately after execution.
- If a phase says "output a table"—output a table. If it says "list 3 options"—list 3.
- No commentary between phases. Execute, log, move on.
- If stuck on a phase, note the blocker and continue—don't redesign the prompt mid-execution.

---

## Example

**User asks:** "What's the best database for my side project?"

**Phase 0 produces:**

```
<role>Database Selection Advisor</role>

<purpose>Your job is to recommend a database with clear reasoning.</purpose>

FLOW: REQUIREMENTS → OPTIONS → TRADEOFFS → RECOMMENDATION

<phase name="Requirements">
  <instruction>List 5-7 things a side project likely needs from a database.</instruction>
  <output>Bulleted list of requirements</output>
</phase>

<phase name="Options">
  <instruction>Generate 5 database options that could fit these requirements.</instruction>
  <output>Table: Database | Type | Best For</output>
</phase>

<phase name="Tradeoffs">
  <instruction>Analyze the top 3 options against the requirements.</instruction>
  <output>For each option: Pros | Cons | Best when</output>
  <evaluate>
    <check>At least 2 options have clear differentiation</check>
    <on_fail>Add a wildcard option (graph DB, embedded, etc.) to create contrast</on_fail>
  </evaluate>
</phase>

<phase name="Recommendation">
  <instruction>Pick ONE database. No "it depends."</instruction>
  <output>
    **Pick:** [Database]
    **Confidence:** [High/Medium/Low]
    **Reason:** [1 sentence]
  </output>
</phase>

CONSTRAINTS:
- No more than 3 serious options in tradeoffs
- Recommendation must pick ONE, not "it depends"
```

**Phase 1 creates todos:**
- Phase: Requirements - list database needs
- Phase: Options - generate candidates
- Phase: Tradeoffs - analyze top 3
- Phase: Recommendation - pick one

**Phase 2 executes each in order, marking todos complete as it goes.**

---

## Related Skills

| Skill | Use For |
|-------|---------|
| `optimizing-prompts` | Optimize a prompt without executing |
| `compose-thinking` | Design custom thinking workflows |
| `ensemble-reasoning` | Rare: when `depth_probe` reveals fundamental method flaw or domain ignorance |
