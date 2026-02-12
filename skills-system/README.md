# Skills System Architecture

How skills are tracked, enforced, and resumed across Claude Code sessions.

## Database

SQLite with WAL mode, stored at `~/life/life.db`. Connection via `open_db()` context manager — guarantees close even on exceptions:

```python
from db.connection import open_db

with open_db() as db:
    row = db.execute("SELECT ...").fetchone()
    db.commit()
```

Schema auto-creates on first connection per process.

### skill_span — Per-invocation execution tracking

```sql
CREATE TABLE IF NOT EXISTS skill_span (
    span_id TEXT PRIMARY KEY,
    skill TEXT NOT NULL,
    parent_span_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    first_step TEXT,
    last_step TEXT,
    steps TEXT DEFAULT '[]',
    session_id TEXT,
    started_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    completed_at TEXT,
    suspended_at TEXT
);
```

### life_event — Append-only event ledger

```sql
CREATE TABLE IF NOT EXISTS life_event (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    skill TEXT NOT NULL,
    phase TEXT DEFAULT '',
    event_type TEXT DEFAULT 'phase_enter',
    session_id TEXT DEFAULT '',
    payload TEXT DEFAULT ''
);
```

## Hook Pipeline (Skill Lifecycle)

```
USER INVOKES /daily-planner
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ UserPromptSubmit: skill_run_initializer.py                   │
│   • Detects /skill-name invocation                           │
│   • Reads SKILL.md frontmatter (uses_skill_run, etc.)        │
│   • Extracts phases from ## Phase N: headers                 │
│   • Writes skill_todos.json marker for TodoWrite validation  │
│   • Injects mode context (full vs quick: /skill vs /skill -) │
│   • Creates SkillRun output directory if uses_skill_run      │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ UserPromptSubmit: prompt_optimizer.py                         │
│   • Detects hashtag modes (#pref, #ver, #qheavy, etc.)      │
│   • Composes modes into exec-opt flow                        │
│   • Handles /exec-opt #pref #ver multi-composition           │
│   • Handles /exec-opt /skill1 /skill2 multi-slash            │
└─────────────────────────────────────────────────────────────┘
        │
        ▼ Claude reads step files (steps/*.md)
        │
┌─────────────────────────────────────────────────────────────┐
│ PreToolUse: step_gate.py (ENFORCEMENT)                       │
│   • Intercepts Read of */skills/*/steps/*.md                 │
│   • Parses consumes/produces YAML frontmatter                │
│   • Queries skill_span.steps for visited steps               │
│   • BLOCKS read if consumed artifacts not yet produced       │
│   • ROOT_INPUTS ("user-request") always satisfied            │
│   • No active span = not invoking = allow (editing safe)     │
│   • Fail-open on errors                                      │
└─────────────────────────────────────────────────────────────┘
        │
        ▼ Read completes
        │
┌─────────────────────────────────────────────────────────────┐
│ PostToolUse: step_logger.py (TRACKING)                       │
│   • Intercepts Read of */skills/*/steps/*.md AND */SKILL.md  │
│   • 3-branch span algorithm (under EXCLUSIVE lock):          │
│     1. Active span exists → append step                      │
│     2. Suspended span → resume + append                      │
│     3. Neither → create new span                             │
│   • Detects skill switches (A→B), suspends A, creates B     │
│   • Parent span = composition signal (B.parent → A)          │
│   • Emits life_event for every step_enter                    │
│   • Injects adaptive context (visit count, ancestry)         │
└─────────────────────────────────────────────────────────────┘
        │
        ▼ Session ends or compaction
        │
┌─────────────────────────────────────────────────────────────┐
│ SessionEnd: close_active_skill_session                        │
│   • Early-returns if no session_id (prevents global UPDATE)  │
│   • Completes both active AND suspended spans                │
│   • Emits session_end event for most recent open skill       │
│   • Prevents cross-session bleed                             │
└─────────────────────────────────────────────────────────────┘
```

### Supporting Hooks

| Hook | Phase | Purpose |
|------|-------|---------|
| PreToolUse | `skill_stage_tracker` | Registers planning stages for planning skills |
| PreToolUse | `skill_todo_validator` | Validates TodoWrite against required_todos |
| PreToolUse | `subagent_step_tracker` | Tracks step reads delegated to Task subagents |
| PromptSubmit | `skill_queue_reminder` | Injects pending-queue reminder during skill sessions |
| PreCompact | `skill_queue_flush` | LLM extracts missed queue observations before compaction |

## Step Dependency DAG

Skills define steps in `steps/*.md` with YAML frontmatter:

```yaml
---
consumes: [user-request]
produces: [depth-probe]
---
## Step 1: Depth Probe
...
```

The `step_gate.py` hook:
1. Parses ALL step files for a skill on first access (cached per-process)
2. Builds `produces_map` (artifact → step) and `consumes_map` (step → [artifacts])
3. On each step read, checks if all consumed artifacts have been produced by visited steps
4. `optional: true` steps can be skipped without breaking the chain
5. `ROOT_INPUTS` (like "user-request") are always satisfied
6. No active span for this skill = not invoking it (editing, browsing) — always allows

## Span State Machine

```
                ┌──────────┐
    create ──→  │  active   │  ──→ completed (session end)
                └──────────┘
                   │    ▲
         suspend   │    │  resume (re-read SKILL.md)
                   ▼    │
                ┌──────────┐
                │ suspended │  ──→ completed (session end)
                └──────────┘
```

- **active**: Skill is currently executing. Steps get appended.
- **suspended**: Another skill took over. Resumes when this skill's SKILL.md or step is read again.
- **completed**: Session ended or explicitly closed. Terminal state. Both active and suspended spans complete on session end.
- All queries scoped by `session_id` — no cross-session interference.

## SkillRun (Output Management)

`SkillRun` creates structured output directories for multi-agent skills:

```
~/projects/{project}/{skill}/
├── runs/{date}-{slug}/
│   ├── context.md          # Shared context (Phase 0)
│   ├── handoffs/           # Per-persona handoff files
│   ├── outputs/            # Per-persona output files
│   ├── run.log             # Timestamped execution log
│   └── synthesis.md        # Final synthesized result
└── reports/                # Published reports
```

Active skills tracked in `~/.claude/tmp/active-skills.json` (breadcrumb file, file-locked).

## Mode System

Hashtag-triggered modes compose with skills:

| Trigger | Mode | Skill |
|---------|------|-------|
| `#pref` | preflight | mode-preflight |
| `#ver` | verify | mode-verify |
| `#clar` | clarify | mode-clarify |
| `#comp` | compare | mode-compare |
| `#teach` | teach-me | mode-teach-me |
| `#research` | research | mode-research |
| `#trace` | trace | mode-trace |
| `#judge` | judge | mode-judge |
| `#qlight` | question-light | mode-question-light (context) |
| `#qheavy` | question-heavy | mode-question-heavy (context) |

**Deep variants**: Append `*` (e.g., `#pref*`) for depth_probe integration.

**Quick mode**: `/skill -` → follows `quick:` instructions, skips `(full only)` phases.

## Worker Resume

Workers can be resumed across sessions using `claude --continue`:

1. Find worktree: `~/.claude/worktrees/task-{id}`
2. Read session ID: `.task/session_id` in worktree
3. Verify session exists: `~/.claude/projects/{project-path}/{session-id}.jsonl`
4. Clear blocked state in DB (atomic UPDATE)
5. Spawn tmux: `claude --continue {session_id} --permission-mode bypassPermissions "{response}"`
6. Verify pane alive after startup wait

Key detail: Task list state is lost on `--continue`. Resume message warns Claude not to recreate tasks.

Note: Worker resume depends on the `formaltask` package (not included in this repo).

## File Inventory

```
skills-system/
├── README.md
├── db/
│   ├── connection.py                      # open_db() context manager, WAL, auto-schema
│   ├── event.py                           # emit_event + query helpers
│   └── models.py                          # LifeEvent Pydantic model
├── hooks/
│   ├── promptsubmit/
│   │   ├── runner.py                      # Entry point (stdin JSON → phases → stdout)
│   │   ├── phases/__init__.py             # Phase ordering
│   │   ├── phases/skill_run_initializer.py
│   │   ├── phases/prompt_optimizer.py
│   │   └── phases/skill_queue_reminder.py
│   ├── pretool/
│   │   ├── phases/step_gate.py            # DAG enforcement
│   │   ├── phases/skill_stage_tracker.py
│   │   ├── phases/skill_todo_validator.py
│   │   └── phases/subagent_step_tracker.py
│   ├── posttool/
│   │   └── phases/step_logger.py          # Span tracking (EXCLUSIVE lock)
│   ├── session_end/
│   │   └── phases/__init__.py             # close_active_skill_session
│   └── pre_compact/
│       └── skill_queue_flush.py
├── utils/
│   └── skill_output.py                    # SkillRun + write_skill_report
├── workers/
│   └── resume.py                          # Worker resume via --continue (requires formaltask)
└── test_spans_live.py                     # Integration test: 40 assertions across 10 scenarios
```

## Dependencies

- Python 3.11
- SQLite 3 (WAL mode)
- pydantic (LifeEvent model)
- pyyaml (step frontmatter parsing)
- openai (skill_queue_flush LLM calls — optional, graceful degradation without API key)
