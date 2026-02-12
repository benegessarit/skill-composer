---
consumes: [user-request]
produces: [depth-probe]
---
## Step 1: Depth Probe

Analyze the request, select thinking tools, gate on confidence.

### 1a. Call depth_probe (MANDATORY)

**MUST call. No exceptions. No "this one's simple."**

Before calling, internally analyze: what's asked, what's implied, what an expert would add unbidden, what assumptions might be wrong. Use this to restate the question — don't write the analysis out.

Call `mcp__reasoning-mcp__depth_probe(question="<restated question>")` → respond with required JSON.

If unavailable via direct call, use `mcp__gateway__call_mcp_tool(mcp_name="reasoning-mcp", tool_name="depth_probe", arguments={...})`.

If unavailable, document the error and proceed — but you MUST attempt the call first.

### 1b. Design Your Thinking Path (MANDATORY)

This is the highest-leverage moment in the entire skill. Think HARD here.

The Shape and Lens tables in SKILL.md are **ingredients, not a menu.** Don't pick from them. Design the optimal reasoning path for THIS specific task — borrowing, combining, inverting, or ignoring them as needed.

#### Step 1: What does this task ACTUALLY need?

Spend real effort here. Don't rush to the ingredients.

1. **What cognitive moves does this task demand?** Name them in your own words. Not "FLIP" — what specifically needs inverting and why?
2. **What will I get wrong if I think linearly?** Be concrete. Not "I might miss something" — what specifically?
3. **What's the ideal output shape?** What structure would make the user say "that's exactly right"?

Write your answers inline. If they're generic, you didn't think hard enough. Redo them.

#### Step 2: Design your phases

With your cognitive needs clear, now design phases that serve them. The reference files (`references/*.md`) are available as raw material — scan the Shape/Lens tables, read any that seem relevant. Borrow phase structures, combine ideas from multiple shapes, or invent entirely new ones.

For each phase you design:
- **Name it** (shape names if they fit, your own if they don't)
- **Write the instruction** (1-2 sentences, specific to THIS task)
- **Specify the output format**
- **Add constraints** from depth_probe's `shallow_spots` and `missing_dimensions`

**Copying a reference file's phases verbatim = you didn't think.** Adapt or invent.

**Explicit overrides:** `#lens` tags or named shapes ("use FLIP") still activate — but you design how they manifest for this task, not copy-paste from the reference.

For lenses: **Read** `references/lens-inflection.md` and apply WHO/ATTITUDE + constraint inflections.

#### Quality bar

Your thinking path should feel *designed for this question*, not assembled from parts. A reader should see your phases and think "that's a smart way to approach this specific problem" — not "that's GAP + FLIP + STRESS."

**Skipping this step = VIOLATION. Generic phases that could apply to any question = VIOLATION.**

### 1c. Confidence Gate

**HIGH:** State interpretation in 1 sentence. Proceed.
**LOW or MEDIUM:** AskUserQuestion with 1-3 questions. Wait.
