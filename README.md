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
# Install the plugin
claude plugins install github:benegessarit/skill-composer

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

The `*` deep variants (e.g., `#pref*`) can use [reasoning-mcp](https://github.com/benegessarit/reasoning-mcp) for metacognitive depth probing. It's loosely coupled—skill-composer works fine without it, but the MCP adds structure when you want Claude to really slow down.

What reasoning-mcp does:

- **depth_probe**: Forces Claude to audit its reasoning before starting ("where will my analysis be shallow?")
- **ensemble**: Claude generates personas for the question, then role-plays each in separate turns (enforced—can't collapse into one response)
- **chaos agent**: Stress-tests assumptions via perturbation (what if we negate this? remove it? take it to extreme?)
- **orchestrator**: Watches the discussion and pushes for depth when it's getting superficial
- **forced synthesis**: Tracks dissent and requires explicit conclusion

```bash
# Install reasoning-mcp
pip install git+https://github.com/benegessarit/reasoning-mcp.git

# Add to Claude Code
claude mcp add reasoning-mcp -- python -m reasoning_mcp
```

Without reasoning-mcp installed, deep variants fall back to inline probing—still useful, just less rigorous.

## Related Work

Similar approaches exist:

- [IBM PDL](https://ibm.github.io/prompt-declaration-language/) — YAML-based prompt programming
- [Prompt Decorators](https://arxiv.org/abs/2510.19850) — academic work on composable control tokens
- [DSPy](https://github.com/stanfordnlp/dspy) — full programming model for LLM pipelines

Those are more ambitious. This is smaller: hashtags that stack in a Claude Code session. No config files, no build step.

## License

MIT
