# Skill Composer

Declarative prompt composition for Claude Code. Like CSS for your AI.

## The Idea

You know how CSS lets you compose styles? `.btn.primary.large` stacks three independent concerns. Each class does one thing. They combine at render time.

Skill Composer does this for Claude Code prompts.

```
#pref #ver What's the best way to refactor this auth module?
```

That's preflight-mode (triple-check before acting) composed with verify-mode (prove claims with evidence). Two independent thinking patterns, combined at prompt-time.

## Why This Exists

Claude keeps forgetting to think carefully before acting. `#pref` forces preflight checks. `#ver` forces evidence. Stacking them (`#pref #ver`) compounds the forcing.

It's discipline disguised as syntax.

The stacking idea comes from CSS (classes compose) and Unix pipes (small tools chain). Not claiming novelty—just applying old patterns to a new problem.

## Quick Start

```bash
# Clone the repo
git clone https://github.com/benegessarit/skill-composer.git

# Copy skills to Claude Code
cp -r skill-composer/skills/* ~/.claude/skills/

# Add the hook to your project's .claude/settings.json
cat <<'EOF' >> .claude/settings.json
{
  "hooks": {
    "UserPromptSubmit": [{
      "type": "command",
      "command": "python3 /path/to/skill-composer/hooks/promptsubmit/runner.py",
      "timeout": 5000
    }]
  }
}
EOF

# Use it
#pref Should I use Redis or Postgres for this cache?
```

## The Modes

### Action Modes (WHAT to do)

| Trigger | Mode | What It Does |
|---------|------|--------------|
| `#pref` | preflight | Triple-check before execution. Facts, completeness, consequences. |
| `#ver` | verify | Prove claims with evidence. Show receipts or retract. |
| `#clar` | clarify | Surface interpretations before answering. |
| `#comp` | compare | Side-by-side comparison with clear criteria. |
| `#teach` | teach-me | Socratic teaching. Build understanding, don't dump info. |
| `#research` | research | Two-phase: survey landscape, then deep-dive on what matters. |
| `#trace` | trace | Follow execution paths through code. |
| `#judge` | judge | Honest evaluation without cheerleading. |
| `#handoff` | handoff | Save comprehensive context for future sessions. |

### Context Modes (HOW to think)

| Trigger | Mode | What It Does |
|---------|------|--------------|
| `#qlight` | question-light | Add thoughtful questions without interrogation. |
| `#qheavy` | question-heavy | Ruthless clarification. Interrogate every assumption. |

### Deep Variants

Add `*` for depth probe (metacognitive audit before executing):

```
#pref* Am I over-engineering this?
```

## Composition

### Hashtag Stacking

Modes compose left-to-right:

```
#qheavy #pref Is this migration safe?
```

Context mode (`#qheavy`) modifies HOW the action mode (`#pref`) runs.

### With exec-opt

Full composition with the exec-opt optimization flow:

```
/exec-opt #pref #ver #qheavy Should I use GraphQL here?
```

This runs:
1. Meta-analysis (what's really being asked)
2. Depth probe (where will thinking be shallow)
3. Preflight checks
4. Evidence verification
5. All with heavy questioning

## How It Works

- **Declarative**: You declare WHAT thinking patterns to apply. The modes handle how.
- **Composable**: Modes are independent. They stack at runtime, no inheritance.
- **Late binding**: Modes compose at prompt-time, not definition-time.

## Optional: Reasoning MCP

The `*` deep variants (e.g., `#pref*`) use [reasoning-mcp](https://github.com/benegessarit/reasoning-mcp) for metacognitive depth probing. Skill-composer works fine without it, but the MCP adds structure when you want Claude to really slow down.

What reasoning-mcp provides:

- **depth_probe**: Audit reasoning before starting — where will analysis be shallow?
- **ensemble**: Generate personas, role-play each in separate turns, with chaos agents and orchestrators
- **perturb**: Stress-test assumptions via chaos engineering (negate, remove, extreme, opposite)
- **synthesize**: Forced multi-perspective synthesis with dissent tracking
- **plan_prompt**: Weighted execution budgets — allocate 100 points across phases, forcing real trade-offs
- **pause / surface / audit_probe**: Mid-execution cognitive checkpoints

```bash
# Install reasoning-mcp
pip install git+https://github.com/benegessarit/reasoning-mcp.git

# Add to Claude Code
claude mcp add reasoning-mcp -- python -m reasoning_mcp
```

Without reasoning-mcp installed, deep variants fall back to inline probing—still useful, just less rigorous.

## Components

### skills/ + hooks/ — Use This

Copy skills and hook. Works immediately. No dependencies. See Quick Start above.

### reasoning-mcp/ — Optional Depth

MCP server for metacognitive tools (depth_probe, ensemble, plan_prompt, etc.). Works standalone. Single dependency: `mcp>=1.0.0`.

```bash
pip install ./reasoning-mcp          # or: pip install reasoning-mcp[test]
claude mcp add reasoning-mcp -- python -m reasoning_mcp
```

Full tool documentation, parameters, and examples: **[reasoning-mcp/README.md](reasoning-mcp/README.md)**

### skills-system/ — Build Your Own

Reference implementation showing how to add infrastructure around skills. Not required to use skill-composer — it shows one way to build observability and enforcement.

What it demonstrates:

- **SQLite span tracking** — per-invocation execution state machine (active → suspended → completed)
- **Step dependency DAG** — blocks out-of-order step reads via `consumes`/`produces` YAML frontmatter
- **Hook pipeline** — 7 hooks across 4 lifecycle events (PromptSubmit, PreToolUse, PostToolUse, SessionEnd)
- **SkillRun output management** — structured directories for multi-agent skills
- **Worker resume** — resume paused workers across sessions via `claude --continue`

Architecture, schema, state machine diagrams: **[skills-system/README.md](skills-system/README.md)**

### Repository Structure

```
skill-composer/
├── skills/                 # Skill definitions (copy to ~/.claude/skills/)
│   ├── exec-opt/           # Execution optimizer with thinking tools + lenses
│   │   ├── SKILL.md        # Core skill definition
│   │   ├── steps/          # Step files with consumes/produces frontmatter
│   │   └── references/     # Thinking tool + lens reference files
│   └── mode-*/             # Mode modifiers (#pref, #ver, #clar, etc.)
├── hooks/                  # UserPromptSubmit hook for hashtag detection
│   ├── hooks.json          # Hook registration
│   └── promptsubmit/       # Mode composition engine
│       └── phases/prompt_optimizer.py
├── reasoning-mcp/          # MCP server for structured reasoning
│   ├── src/reasoning_mcp/  # 9 tools: ensemble, invoke, perturb, synthesize,
│   │                       #   depth_probe, plan_prompt, pause, surface, audit_probe
│   ├── tests/              # 59 tests
│   └── pyproject.toml      # Deps: mcp>=1.0.0
└── skills-system/          # Reference implementation (see skills-system/README.md)
    ├── db/                 # SQLite: span tracking + event ledger
    ├── hooks/              # 7 hooks across 4 lifecycle events
    ├── utils/              # SkillRun output management
    └── workers/            # Worker resume via --continue
```

## Related Work

Similar approaches exist:

- [IBM PDL](https://ibm.github.io/prompt-declaration-language/) — YAML-based prompt programming
- [Prompt Decorators](https://arxiv.org/abs/2510.19850) — academic work on composable control tokens
- [DSPy](https://github.com/stanfordnlp/dspy) — full programming model for LLM pipelines

Those are more ambitious. This is smaller: hashtags that stack in a Claude Code session.

## License

MIT
