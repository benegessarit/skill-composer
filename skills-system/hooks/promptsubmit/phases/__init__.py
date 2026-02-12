"""UserPromptSubmit phase functions — skill-related subset.

Full version also includes update_session_activity and task_context,
which depend on FormalTask infrastructure. This standalone version
includes only skill-related phases.
"""

from hooks.promptsubmit.phases import (
    prompt_optimizer,
    skill_queue_reminder,
    skill_run_initializer,
)

# Ordered list of phase check functions
# skill_run_initializer first so SkillRun is created before skill loads
# skill_queue_reminder last — fires every turn during active skill sessions
PHASES = [
    skill_run_initializer.check,
    prompt_optimizer.check,
    skill_queue_reminder.check,
]

__all__ = [
    "prompt_optimizer",
    "skill_queue_reminder",
    "skill_run_initializer",
    "PHASES",
]
