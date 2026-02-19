"""Hashtag mode triggers and exec-opt composition.

Patterns supported:
    #pref question       → invoke mode-preflight (always with depth_probe)
    #qlight question     → set question-light context
    #qheavy question     → set question-heavy context
    /exec-opt #pref #ver q → compose modes into exec-opt flow
    /exec-opt /skill q   → compose skills into exec-opt flow
"""

from __future__ import annotations

import re
from pathlib import Path

# === SKILL LOCATIONS ===
SKILLS_DIR = Path.home() / ".claude/skills"
EXEC_OPT_PATH = SKILLS_DIR / "exec-opt/SKILL.md"

# === ACTION MODE DEFINITIONS ===
# Maps mode key to (trigger_pattern, skill_name, is_deep)
# All action modes include depth_probe by default
ACTION_MODES = {
    "preflight": (r"#pref", "mode-preflight", True),
    "verify": (r"#ver", "mode-verify", True),
    "clarify": (r"#clar", "mode-clarify", True),
    "compare": (r"#comp", "mode-compare", True),
    "teach_me": (r"#teach", "mode-teach-me", True),
    "research": (r"#research", "mode-research", True),
    "trace": (r"#trace", "mode-trace", True),
    "judge": (r"#judge", "mode-judge", True),
    "handoff": (r"#handoff", "mode-handoff", True),
}

# === CONTEXT MODE DEFINITIONS ===
# Context modes modify HOW all phases run, don't add phases
CONTEXT_MODES = {
    "question_light": (r"#qlight", "mode-question-light"),
    "question_heavy": (r"#qheavy", "mode-question-heavy"),
    "track": (r"#track", "tracking-discussion"),
}

# Compile patterns with proper lookahead
ACTION_PATTERNS = {
    key: re.compile(rf"\s*{pattern}(?=\s|[?!.,;]|$)", re.IGNORECASE)
    for key, (pattern, _, _) in ACTION_MODES.items()
}

CONTEXT_PATTERNS = {
    key: re.compile(rf"\s*{pattern}(?=\s|[?!.,;]|$)", re.IGNORECASE)
    for key, (pattern, _) in CONTEXT_MODES.items()
}

# === EXEC-OPT COMPOSITION PATTERNS ===

# /exec-opt with hashtag modes: /exec-opt #pf #vf question
EXEC_OPT_WITH_HASHTAGS = re.compile(
    r"^/exec-opt\s+(.+)$",
    re.IGNORECASE | re.DOTALL,
)

# Extract hashtag modes from text (matches #pref, #ver, #qheavy, etc.)
HASHTAG_MODE_PATTERN = re.compile(
    r"(?:^|(?<=\s))(#[a-z][a-z0-9-]*)(?=\s|$)",
    re.IGNORECASE,
)

# Legacy: /exec-opt+skill1,skill2 question
MULTI_SKILL_PLUS_PATTERN = re.compile(
    r"^/exec-opt\+([a-z][a-z0-9-]*(?:,[a-z][a-z0-9-]*)*)\s+(.+)$",
    re.IGNORECASE | re.DOTALL,
)

# Multi-slash: /exec-opt /skill1 /skill2 question
MULTI_SLASH_START = re.compile(
    r"^/exec-opt\s+",
    re.IGNORECASE,
)

# Extract skill names: /skill-name (lowercase-hyphenated)
SKILL_NAME_PATTERN = re.compile(r"(?:^|(?<=\s))/([a-z][a-z0-9]*(?:-[a-z0-9]+)*)(?=\s|$)")


def _read_exec_opt() -> str:
    """Read exec-opt content."""
    if EXEC_OPT_PATH.exists():
        return EXEC_OPT_PATH.read_text()
    return ""


def _detect_action_mode(prompt: str) -> tuple[str | None, str, bool]:
    """Detect action mode from hashtag flags.

    Returns:
        (mode_key, clean_prompt, is_deep)
    """
    for mode_key, pattern in ACTION_PATTERNS.items():
        if pattern.search(prompt):
            # Remove all hashtag patterns from prompt
            clean = prompt
            for p in ACTION_PATTERNS.values():
                clean = p.sub("", clean)
            for p in CONTEXT_PATTERNS.values():
                clean = p.sub("", clean)
            clean = " ".join(clean.split())

            _, _, is_deep = ACTION_MODES[mode_key]
            return mode_key, clean, is_deep
    return None, prompt, False


def _detect_context_mode(prompt: str) -> tuple[str | None, str]:
    """Detect context mode from hashtag flags.

    Returns:
        (mode_key, clean_prompt)
    """
    for mode_key, pattern in CONTEXT_PATTERNS.items():
        if pattern.search(prompt):
            # Remove all hashtag patterns from prompt
            clean = prompt
            for p in CONTEXT_PATTERNS.values():
                clean = p.sub("", clean)
            for p in ACTION_PATTERNS.values():
                clean = p.sub("", clean)
            clean = " ".join(clean.split())
            return mode_key, clean
    return None, prompt


def _extract_hashtag_modes(text: str) -> tuple[list[str], list[str], str]:
    """Extract hashtag modes from text.

    Returns:
        (action_modes, context_modes, remaining text)
    """
    all_hashtags = HASHTAG_MODE_PATTERN.findall(text)

    action_modes = []
    context_modes = []

    for h in all_hashtags:
        h_lower = h.lower()
        # Check if it's a context mode
        is_context = False
        for _, (pattern, _) in CONTEXT_MODES.items():
            if re.match(pattern, h_lower):
                context_modes.append(h)
                is_context = True
                break
        if not is_context:
            action_modes.append(h)

    clean = HASHTAG_MODE_PATTERN.sub("", text)
    clean = " ".join(clean.split()).strip()
    return action_modes, context_modes, clean


def _hashtag_to_action_skill(hashtag: str) -> tuple[str, bool] | None:
    """Convert action hashtag to (skill_name, is_deep).

    Args:
        hashtag: Like '#pref' or '#ver'

    Returns:
        (skill_name, is_deep) or None if not recognized
    """
    h = hashtag.strip().lower()

    for mode_key, pattern in ACTION_PATTERNS.items():
        if pattern.match(h) or pattern.match(" " + h):
            _, skill_name, is_deep = ACTION_MODES[mode_key]
            return skill_name, is_deep
    return None


def _hashtag_to_context_skill(hashtag: str) -> str | None:
    """Convert context hashtag to skill_name.

    Args:
        hashtag: Like '#qlight' or '#qheavy'

    Returns:
        skill_name or None if not recognized
    """
    h = hashtag.strip().lower()

    for mode_key, pattern in CONTEXT_PATTERNS.items():
        if pattern.match(h) or pattern.match(" " + h):
            _, skill_name = CONTEXT_MODES[mode_key]
            return skill_name
    return None


def _compose_with_modes(
    action_hashtags: list[str], context_hashtags: list[str], question: str
) -> str | None:
    """Compose exec-opt with hashtag modes.

    Args:
        action_hashtags: List like ['#pref', '#ver']
        context_hashtags: List like ['#qheavy']
        question: The user's question

    Returns:
        Composed content with metadata tags, or None if base skill not found
    """
    base_content = _read_exec_opt()
    if not base_content:
        return None

    # Resolve action hashtags to skill paths
    action_lines = []
    has_deep = False
    for h in action_hashtags:
        resolved = _hashtag_to_action_skill(h)
        if resolved:
            skill_name, is_deep = resolved
            action_lines.append(f"- {skill_name}: {SKILLS_DIR / skill_name / 'SKILL.md'}")
            if is_deep:
                has_deep = True

    # Resolve context hashtags to skill paths
    context_lines = []
    for h in context_hashtags:
        skill_name = _hashtag_to_context_skill(h)
        if skill_name:
            context_lines.append(f"- {skill_name}: {SKILLS_DIR / skill_name / 'SKILL.md'}")

    # Build output
    result = base_content + f"\n\n<input>\n{question}\n</input>\n"

    if action_lines:
        result += f"\n<requested_modes>\n" + "\n".join(action_lines) + "\n</requested_modes>\n"

    if context_lines:
        result += (
            f"\n<requested_contexts>\n" + "\n".join(context_lines) + "\n</requested_contexts>\n"
        )

    result += f"\n<mode_config>\ndeep_probe: {str(has_deep).lower()}\n</mode_config>\n"

    return result


def _compose_multi_skill(skill_names: list[str], question: str) -> str | None:
    """Compose exec-opt with slash skills.

    Args:
        skill_names: List like ['debugging', 'tdd']
        question: The user's question

    Returns:
        Composed content with metadata, or None if base skill not found
    """
    base_content = _read_exec_opt()
    if not base_content:
        return None

    skill_lines = "\n".join(f"- {s}: {SKILLS_DIR / s / 'SKILL.md'}" for s in skill_names)

    return f"""{base_content}

<input>
{question}
</input>

<requested_skills>
{skill_lines}
</requested_skills>
"""


def _extract_multi_slash_skills(prompt: str) -> tuple[list[str], str] | None:
    """Extract skills from multi-slash pattern.

    Pattern: /exec-opt /skill1 /skill2 question

    Returns:
        (skill_names, question) if detected, None otherwise
    """
    if not MULTI_SLASH_START.match(prompt):
        return None

    all_skills = SKILL_NAME_PATTERN.findall(prompt)

    if not all_skills or all_skills[0] != "exec-opt":
        return None

    additional_skills = all_skills[1:]
    if not additional_skills:
        return None

    # Extract question
    question = prompt
    for skill in all_skills:
        question = re.sub(rf"(?:^|(?<=\s))/{re.escape(skill)}(?=\s|$)", "", question)
    question = " ".join(question.split()).strip()

    return additional_skills, question


def _read_context_skill(skill_name: str) -> str:
    """Read context skill content."""
    path = SKILLS_DIR / skill_name / "SKILL.md"
    if path.exists():
        return path.read_text()
    return ""


def _invoke_skill_context(
    skill_name: str, question: str, deep: bool = False, context_skill: str | None = None
) -> str:
    """Generate context that instructs Claude to invoke a skill.

    Args:
        skill_name: The skill to invoke (e.g., 'mode-preflight')
        question: The user's cleaned question
        deep: Whether to also call depth_probe
        context_skill: Optional context mode skill name
    """
    deep_instruction = ""
    if deep:
        deep_instruction = """
**DEPTH_PROBE REQUIRED:** After invoking the skill, you MUST also call:
```python
mcp__reasoning-mcp__depth_probe(question="<the question>")
```
Incorporate probe insights into your response.
"""

    context_block = ""
    if context_skill:
        context_content = _read_context_skill(context_skill)
        if context_content:
            context_block = f"""
<active_context skill="{context_skill}">
{context_content}
</active_context>

**CONTEXT IS ACTIVE.** The above context modifies HOW you execute everything below.
"""

    return f"""{context_block}**MANDATORY: Invoke skill before responding.**

You MUST invoke the `{skill_name}` skill IMMEDIATELY using:

```python
Skill("{skill_name}")
```

Do this BEFORE generating any other response.
{deep_instruction}
<user-question>
{question}
</user-question>"""


def _context_only_response(context_skill: str, question: str) -> str:
    """Generate response for context-only invocation (no action mode)."""
    context_content = _read_context_skill(context_skill)

    return f"""<active_context skill="{context_skill}">
{context_content}
</active_context>

**CONTEXT IS ACTIVE.** Apply the above context constraints to your response.

<user-question>
{question}
</user-question>"""


def check(ctx: dict) -> dict | None:
    """Detect hashtag modes and exec-opt composition.

    Patterns:
        #pref question        → invoke mode-preflight + depth_probe
        #qlight question      → apply question-light context
        #qheavy #pref q       → context + action mode
        /exec-opt #pref #ver q → compose modes into exec-opt
        /exec-opt /skill1 q   → compose skills into exec-opt
        /exec-opt+s1,s2 q     → legacy compose

    Returns:
        dict with context key, or None
    """
    prompt = ctx.get("prompt", "").strip()

    # === EXEC-OPT WITH HASHTAG MODES ===
    # Pattern: /exec-opt #pf #vf question
    exec_opt_match = EXEC_OPT_WITH_HASHTAGS.match(prompt)
    if exec_opt_match:
        rest = exec_opt_match.group(1)
        action_hashtags, context_hashtags, question = _extract_hashtag_modes(rest)

        if action_hashtags or context_hashtags:
            composed = _compose_with_modes(action_hashtags, context_hashtags, question)
            if composed:
                return {"context": composed}

    # === MULTI-SLASH SKILLS ===
    # Pattern: /exec-opt /skill1 /skill2 question
    multi_slash = _extract_multi_slash_skills(prompt)
    if multi_slash:
        skill_names, question = multi_slash
        composed = _compose_multi_skill(skill_names, question)
        if composed:
            return {"context": composed}

    # === LEGACY PLUS PATTERN ===
    # Pattern: /exec-opt+skill1,skill2 question
    multi_match = MULTI_SKILL_PLUS_PATTERN.match(prompt)
    if multi_match:
        skills_raw = multi_match.group(1)
        question = multi_match.group(2).strip()
        skill_names = [s.strip().lower() for s in skills_raw.split(",")]

        composed = _compose_multi_skill(skill_names, question)
        if composed:
            return {"context": composed}

    # === STANDALONE HASHTAG MODES ===
    # Detect context mode first
    context_key, clean_prompt = _detect_context_mode(prompt)
    context_skill = None
    if context_key:
        _, context_skill = CONTEXT_MODES[context_key]

    # Detect action mode
    action_key, clean_prompt, is_deep = _detect_action_mode(clean_prompt if context_key else prompt)

    if action_key is None and context_key is None:
        return None

    if not clean_prompt.strip():
        return None

    # Context only (no action mode)
    if action_key is None and context_skill:
        return {"context": _context_only_response(context_skill, clean_prompt)}

    # Action mode (possibly with context)
    if action_key:
        _, skill_name, _ = ACTION_MODES[action_key]
        return {
            "context": _invoke_skill_context(
                skill_name, clean_prompt, deep=is_deep, context_skill=context_skill
            )
        }

    return None
