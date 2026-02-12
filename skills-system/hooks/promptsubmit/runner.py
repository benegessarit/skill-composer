#!/usr/bin/env python3
"""UserPromptSubmit hook runner - plain function architecture.

Task #2569: Simple list + loop pattern (no discovery).
Reads stdin JSON payload and executes all phases in order.
"""

import json
import sys
from pathlib import Path

# Add project root for imports when run directly
_project_root = str(Path(__file__).parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from hooks.promptsubmit.phases import PHASES


def main() -> None:
    """Entry point for UserPromptSubmit hook.

    Executes all phases in order. All phases fail open
    (errors logged but don't block - promptsubmit cannot block).

    Accumulates all phase contexts, joins with double newline,
    and outputs a single hookSpecificOutput for Claude.
    """
    payload = json.load(sys.stdin)

    contexts = []
    system_message = None

    for phase_fn in PHASES:
        try:
            result = phase_fn(payload)
            if result and isinstance(result, dict) and "context" in result:
                contexts.append(result["context"])
                # First systemMessage wins
                if not system_message and "systemMessage" in result:
                    system_message = result["systemMessage"]
        except Exception as e:
            # Fail open: log error but continue with remaining phases
            # Use stderr since promptsubmit cannot output errors to stdout
            print(f"Warning: {phase_fn.__name__} failed: {e}", file=sys.stderr)

    if contexts:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": "\n\n".join(contexts),
            }
        }
        if system_message:
            output["systemMessage"] = system_message
        print(json.dumps(output))


if __name__ == "__main__":
    main()
