#!/usr/bin/env python3
"""PreCompact hook: extract missed queue observations via LLM.

Safety net for skill sessions. Fires at compaction to catch observations
Claude missed despite the PromptSubmit reminder. Appends extracted entries
to the skill's pending-queue.md file.
"""

import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add project root for imports when run directly
_project_root = str(Path(__file__).parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from hooks.pre_compact.handoff_transcript import handoff_transcript
    from hooks.pre_compact.transcript_snapshot import find_last_compaction_line
except ImportError:
    handoff_transcript = None
    find_last_compaction_line = None

logger = logging.getLogger(__name__)

MODEL = "openai/gpt-5.2-high"
BASE_URL = "https://openrouter.ai/api/v1"

QUEUE_SKILLS = {
    "learning-companion": {
        "path": Path.home() / "life" / "learning" / "pending-queue.md",
        "web": Path.home() / "life" / "learning" / "web.md",
        "arrows": "-> Node: node-name (familiarity change)\n-> Edge: node-a <-> node-b \"connecting insight\"\n-> Evidence: what was learned, mode",
    },
    "therapy-journal": {
        "path": Path.home() / "life" / "therapy-journal" / "pending-queue.md",
        "web": Path.home() / "life" / "therapy-journal" / "state.md",
        "arrows": "-> State: delta to state.md\n-> Bridge: Janie connection",
    },
    "goal-compass": {
        "path": Path.home() / "life" / "goals" / "pending-queue.md",
        "web": Path.home() / "life" / "goals" / "sheet.md",
        "arrows": "-> Evidence: pattern or non-win data point\n-> State: state.json delta\n-> Sheet: sheet.md update candidate",
    },
}

EXTRACTION_PROMPT = """\
You are a dedup-aware safety net for a {skill} session. Claude was supposed to
log learning moments to a queue file but may have missed some during compaction.

ALREADY QUEUED (do NOT re-extract these):
{existing_queue}

ALREADY IN KNOWLEDGE WEB (do NOT re-extract these):
{existing_web}

RULES:
1. Only extract moments the user CONFIRMED understanding of (said "yes", "got it",
   "makes sense", asked a follow-up showing comprehension — not just listened).
2. Skip anything already covered by ALREADY QUEUED or ALREADY IN KNOWLEDGE WEB above.
   Same insight reworded = duplicate. Same node/edge pair = duplicate.
3. Skip: small talk, clarifying questions, tool usage, setup, captures to study queue.
4. Output NOTHING if no genuinely new confirmed moments. Prefer silence over duplication.

For each NEW confirmed moment, output exactly:

---
### {{{{timestamp}}}}
{{{{one-line context}}}}
{arrows}

No preamble, no explanation, no commentary."""


def skill_queue_flush(ctx: dict) -> None:
    """Extract missed observations and append to pending-queue."""
    if handoff_transcript is None or find_last_compaction_line is None:
        return

    # Guard: skip workers
    if Path(".task/id").exists():
        return

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return

    transcript_path_str = ctx.get("transcript_path")
    if not transcript_path_str:
        return

    transcript_path = Path(transcript_path_str)
    if not transcript_path.exists():
        return

    session_id = transcript_path.stem

    # Check for active or suspended skill span (suspended survives nesting)
    try:
        from db.connection import open_db

        with open_db() as db:
            row = db.execute(
                "SELECT skill FROM skill_span "
                "WHERE status IN ('active', 'suspended') AND session_id = ? "
                "ORDER BY started_at DESC LIMIT 1",
                (session_id,),
            ).fetchone()
    except Exception as e:
        logger.debug("skill_queue_flush: db query failed: %s", e)
        return

    if not row:
        return

    skill = row["skill"]
    info = QUEUE_SKILLS.get(skill)
    if not info:
        return

    # Extract transcript segment since last compaction
    start_line = find_last_compaction_line(transcript_path)
    segment = handoff_transcript(transcript_path, start_line=start_line)
    if len(segment) < 200:
        return

    # Load existing context for dedup
    queue_path = info["path"]
    existing_queue = queue_path.read_text().strip() if queue_path.exists() else "(empty)"
    web_path = info.get("web")
    existing_web = "(none)"
    if web_path and web_path.exists():
        existing_web = web_path.read_text().strip()

    # Call LLM to extract observations
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url=BASE_URL,
            default_headers={
                "HTTP-Referer": "https://github.com/anthropics/claude-code",
                "X-Title": "Claude Code Hooks",
            },
        )

        prompt = EXTRACTION_PROMPT.format(
            skill=skill,
            arrows=info["arrows"],
            existing_queue=existing_queue,
            existing_web=existing_web,
        )

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": segment},
            ],
        )
        extracted = response.choices[0].message.content
    except Exception as e:
        logger.warning("skill_queue_flush: LLM call failed: %s", e)
        return

    if not extracted or not extracted.strip() or extracted.strip().lower() in ("none", "nothing"):
        return

    # Fix placeholder timestamps with real ones
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ")
    extracted = extracted.replace("{timestamp}", now)
    extracted = extracted.replace("{{timestamp}}", now)

    # Append to pending-queue
    queue_path.parent.mkdir(parents=True, exist_ok=True)

    current = queue_path.read_text() if queue_path.exists() else ""
    separator = "\n" if current and not current.endswith("\n") else ""
    queue_path.write_text(current + separator + extracted.strip() + "\n")


def main() -> None:
    payload = json.load(sys.stdin)
    try:
        skill_queue_flush(payload)
    except Exception as e:
        logger.warning("skill_queue_flush failed (non-blocking): %s", e)


if __name__ == "__main__":
    main()
