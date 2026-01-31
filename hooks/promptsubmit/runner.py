#!/usr/bin/env python3
"""UserPromptSubmit hook runner for skill-composer plugin.

Reads stdin JSON payload and executes prompt_optimizer phase.
Outputs context for Claude if mode detected.
"""

import json
import sys
from pathlib import Path

# Add hooks to path for local import
sys.path.insert(0, str(Path(__file__).parent.parent))

from promptsubmit.phases import prompt_optimizer


def main() -> None:
    """Entry point for UserPromptSubmit hook.

    Executes prompt_optimizer phase. Fails open (errors logged but don't block).
    If phase returns a dict with "context" key, outputs hookSpecificOutput.
    """
    payload = json.load(sys.stdin)

    try:
        result = prompt_optimizer.check(payload)
        if result and isinstance(result, dict) and "context" in result:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": result["context"]
                }
            }
            if "systemMessage" in result:
                output["systemMessage"] = result["systemMessage"]
            print(json.dumps(output))
    except Exception as e:
        print(f"Warning: prompt_optimizer failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
