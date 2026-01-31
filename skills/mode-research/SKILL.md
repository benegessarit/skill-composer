---
name: mode-research
description: >-
  Two-phase research mode. Use when #research prefix detected. Phase 1: Exa search
  for landscape survey. Phase 2: Firecrawl skill for deep dives on promising results.
  For quick lookups, use firecrawl directly.
---

# Research Mode

<role>Research Strategist</role>

<purpose>Your job is to survey the landscape FIRST, then drill deep on what matters.</purpose>

---

## Phase 1: Exa Survey

**Get the lay of the land with broad search.**

Use exa MCP for initial survey:

```python
mcp__gateway__call_mcp_tool(
    mcp_name="exa",
    tool_name="web_search_exa",
    arguments={"query": "<research topic>", "numResults": 10}
)
```

**Output format:**

```markdown
## Landscape Survey

**Query:** [what you searched]
**Sources found:** [count]

| # | Source | Why Relevant | Deep Dive? |
|---|--------|--------------|------------|
| 1 | [title](url) | [1-line reason] | YES/NO |
| 2 | [title](url) | [1-line reason] | YES/NO |
...

**Initial observations:**
- [Pattern 1]
- [Pattern 2]
- [Gap or question]

**Deep dive targets:** [list URLs marked YES]
```

**Selection criteria for deep dive:**
- Primary sources > secondary commentary
- Recent > stale (check dates)
- Technical depth > marketing fluff
- Diverse perspectives > echo chamber

---

## Phase 2: Firecrawl Deep Dives

**Invoke firecrawl skill for each deep dive target.**

```python
Skill("firecrawl")
```

Then for each URL:

```bash
firecrawl scrape <url> --formats markdown
```

**After each deep dive, extract:**

```markdown
### Deep Dive: [Source Title]

**URL:** [url]
**Key findings:**
1. [Finding with evidence]
2. [Finding with evidence]
3. [Finding with evidence]

**Quotes worth preserving:**
> "[exact quote]" — [source]

**Contradicts survey?** YES/NO — [if yes, what]
**New questions raised:** [if any]
```

---

## Phase 3: Synthesis

**Combine survey + deep dives into answer.**

```markdown
## Research Synthesis

**Question:** [original research question]

**TL;DR:** [2-3 sentence answer]

**Evidence base:**
- [# sources surveyed]
- [# deep dives completed]
- [confidence: high/medium/low]

**Key findings:**
1. [Finding] — supported by [sources]
2. [Finding] — supported by [sources]
3. [Finding] — supported by [sources]

**Dissenting views:** [if any credible disagreement exists]

**Gaps in research:** [what couldn't be determined]

**Sources:**
- [Source 1](url) — [what it contributed]
- [Source 2](url) — [what it contributed]
```

---

## Rules

- **Survey before diving.** Don't go deep on the first result. Get the landscape.
- **Limit deep dives to 3-5.** More isn't better—synthesis quality drops.
- **Cite everything.** No claims without source attribution.
- **Flag contradictions.** If sources disagree, say so explicitly.
- **Admit gaps.** "I couldn't find evidence for X" is valid output.

---

## When to Apply

This mode runs as CORE analysis—neither first nor last.

Use when:
- Researching unfamiliar topics
- Need current state of something
- Comparing options with external evidence
- Fact-checking claims against sources

Skip when:
- Answer is in codebase (use code search)
- User provided the sources already
- Quick factual lookup (just use firecrawl directly)
