#!/usr/bin/env python3
"""Live integration test for skill span state machine.

Uses a temp DB — no production data touched. Exercises:
1. Span creation (new skill)
2. Step append (same skill, new step)
3. Skill switch (suspend A, create B)
4. Skill return (suspend B, resume A)
5. Subagent step delegation
6. Session end (complete all active + suspended)
7. Session end with no session_id (safe no-op)
8. Exclusive lock under concurrency
9. Monolithic skill (SKILL.md, no steps)
10. Life events emitted correctly

Run: python test_spans_live.py
"""

import json
import sys
import tempfile
import threading
from pathlib import Path

# Patch DB_PATH before any imports touch it
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_path = Path(_tmp.name)
_tmp.close()

sys.path.insert(0, str(Path(__file__).parent))

import db.connection as conn_mod
conn_mod.DB_PATH = _tmp_path
conn_mod._schema_initialized = False

from db.connection import open_db
from hooks.posttool.phases.step_logger import _get_or_create_span, _suspend_current_span
from hooks.pretool.phases.subagent_step_tracker import check as subagent_check
from hooks.session_end.phases import close_active_skill_session

SESSION = "test-session-001"
PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
results = []


def assert_eq(label, actual, expected):
    if actual == expected:
        print(f"  {PASS} {label}")
        results.append(True)
    else:
        print(f"  {FAIL} {label}: expected {expected!r}, got {actual!r}")
        results.append(False)


def assert_in(label, needle, haystack):
    if needle in haystack:
        print(f"  {PASS} {label}")
        results.append(True)
    else:
        print(f"  {FAIL} {label}: {needle!r} not in {haystack!r}")
        results.append(False)


def get_span(span_id):
    with open_db() as db:
        row = db.execute("SELECT * FROM skill_span WHERE span_id = ?", (span_id,)).fetchone()
    return dict(row) if row else None


def get_spans_by_session(session_id):
    with open_db() as db:
        rows = db.execute(
            "SELECT * FROM skill_span WHERE session_id = ? ORDER BY started_at",
            (session_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_events(session_id=None):
    with open_db() as db:
        if session_id:
            rows = db.execute(
                "SELECT * FROM life_event WHERE session_id = ? ORDER BY timestamp",
                (session_id,),
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM life_event ORDER BY timestamp").fetchall()
    return [dict(r) for r in rows]


# ── Test 1: Create new span ──────────────────────────────────────────
print("\n1. Create new span (skill-a, step-1)")
span_a = _get_or_create_span("skill-a", "step-1", session_id=SESSION)
assert_eq("span_id returned", span_a is not None, True)
s = get_span(span_a)
assert_eq("status = active", s["status"], "active")
assert_eq("skill = skill-a", s["skill"], "skill-a")
assert_eq("steps = ['step-1']", json.loads(s["steps"]), ["step-1"])
assert_eq("first_step = step-1", s["first_step"], "step-1")
assert_eq("session_id set", s["session_id"], SESSION)
assert_eq("parent_span_id = None", s["parent_span_id"], None)


# ── Test 2: Append step to existing span ──────────────────────────────
print("\n2. Append step (skill-a, step-2)")
span_a2 = _get_or_create_span("skill-a", "step-2", session_id=SESSION)
assert_eq("same span_id", span_a2, span_a)
s = get_span(span_a)
assert_eq("steps appended", json.loads(s["steps"]), ["step-1", "step-2"])
assert_eq("last_step updated", s["last_step"], "step-2")


# ── Test 3: Skill switch — suspend A, create B ───────────────────────
print("\n3. Skill switch: suspend skill-a, create skill-b")
_suspend_current_span("skill-a", session_id=SESSION)
s = get_span(span_a)
assert_eq("skill-a suspended", s["status"], "suspended")
assert_eq("suspended_at set", s["suspended_at"] is not None, True)

span_b = _get_or_create_span("skill-b", "intro", session_id=SESSION)
assert_eq("new span for skill-b", span_b != span_a, True)
sb = get_span(span_b)
assert_eq("skill-b active", sb["status"], "active")
assert_eq("parent = skill-a span", sb["parent_span_id"], span_a)
assert_eq("skill-b steps", json.loads(sb["steps"]), ["intro"])


# ── Test 4: Return to skill-a — suspend B, resume A ──────────────────
print("\n4. Return to skill-a: suspend skill-b, resume skill-a")
_suspend_current_span("skill-b", session_id=SESSION)
sb = get_span(span_b)
assert_eq("skill-b suspended", sb["status"], "suspended")

span_a3 = _get_or_create_span("skill-a", "step-3", session_id=SESSION)
assert_eq("resumed same span", span_a3, span_a)
s = get_span(span_a)
assert_eq("skill-a active again", s["status"], "active")
assert_eq("suspended_at cleared", s["suspended_at"], None)
assert_eq("steps include step-3", json.loads(s["steps"]), ["step-1", "step-2", "step-3"])


# ── Test 5: Subagent step delegation ──────────────────────────────────
print("\n5. Subagent step delegation")
ctx = {
    "tool_name": "Task",
    "tool_input": {"prompt": "Read /skills/skill-a/steps/step-4.md and follow it"},
    "session_id": SESSION,
}
subagent_check(ctx)
s = get_span(span_a)
assert_eq("step-4 appended by subagent", json.loads(s["steps"]), ["step-1", "step-2", "step-3", "step-4"])

# Dedup: same step again should not append
subagent_check(ctx)
s = get_span(span_a)
assert_eq("dedup: no double step-4", json.loads(s["steps"]), ["step-1", "step-2", "step-3", "step-4"])

# Non-Task tool: should be no-op
subagent_check({
    "tool_name": "Read",
    "tool_input": {"prompt": "Read /skills/skill-a/steps/step-5.md"},
    "session_id": SESSION,
})
s = get_span(span_a)
assert_eq("non-Task ignored", json.loads(s["steps"]), ["step-1", "step-2", "step-3", "step-4"])

# Internal skill filtered
subagent_check({
    "tool_name": "Task",
    "tool_input": {"prompt": "Read /skills/_internal/steps/hidden.md"},
    "session_id": SESSION,
})
spans = get_spans_by_session(SESSION)
assert_eq("no span for _internal", all(s["skill"] != "_internal" for s in spans), True)


# ── Test 6: Session end — complete all active + suspended ─────────────
print("\n6. Session end: complete all active + suspended spans")
s_a = get_span(span_a)
s_b = get_span(span_b)
assert_eq("pre: skill-a active", s_a["status"], "active")
assert_eq("pre: skill-b suspended", s_b["status"], "suspended")

close_active_skill_session({"session_id": SESSION})

s_a = get_span(span_a)
s_b = get_span(span_b)
assert_eq("skill-a completed", s_a["status"], "completed")
assert_eq("skill-a completed_at set", s_a["completed_at"] is not None, True)
assert_eq("skill-b completed (was suspended)", s_b["status"], "completed")
assert_eq("skill-b completed_at set", s_b["completed_at"] is not None, True)


# ── Test 7: Session end with no session_id — should be no-op ─────────
print("\n7. Session end with no session_id (should be no-op)")
span_other = _get_or_create_span("skill-c", "s1", session_id="other-session")
close_active_skill_session({"session_id": None})
close_active_skill_session({})
s_other = get_span(span_other)
assert_eq("other session untouched", s_other["status"], "active")
close_active_skill_session({"session_id": "other-session"})


# ── Test 8: Exclusive lock correctness ────────────────────────────────
print("\n8. Exclusive lock: concurrent-safe step append")
SESSION_LOCK = "lock-test-session"
span_lock = _get_or_create_span("lock-skill", "s0", session_id=SESSION_LOCK)
errors = []

def append_step(step_name):
    try:
        _get_or_create_span("lock-skill", step_name, session_id=SESSION_LOCK)
    except Exception as e:
        errors.append(str(e))

threads = [threading.Thread(target=append_step, args=(f"t{i}",)) for i in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()

assert_eq("no errors from concurrent appends", len(errors), 0)
s = get_span(span_lock)
steps = json.loads(s["steps"])
assert_eq("all 10 steps appended", len(steps), 11)  # s0 + t0..t9
assert_eq("no duplicates", len(steps), len(set(steps)))
close_active_skill_session({"session_id": SESSION_LOCK})


# ── Test 9: SKILL.md invocation (no step) ─────────────────────────────
print("\n9. SKILL.md invocation (monolithic skill, no step)")
SESSION_MONO = "mono-session"
span_mono = _get_or_create_span("mono-skill", None, session_id=SESSION_MONO)
s = get_span(span_mono)
assert_eq("first_step = SKILL", s["first_step"], "SKILL")
assert_eq("steps = ['SKILL']", json.loads(s["steps"]), ["SKILL"])
close_active_skill_session({"session_id": SESSION_MONO})


# ── Test 10: Events emitted ──────────────────────────────────────────
print("\n10. Life events emitted")
events = get_events()
assert_eq("events exist", len(events) > 0, True)
event_types = {e["event_type"] for e in events}
assert_in("session_end events", "session_end", event_types)
assert_in("subagent_step_delegate events", "subagent_step_delegate", event_types)


# ── Summary ───────────────────────────────────────────────────────────
print(f"\n{'='*50}")
_tmp_path.unlink(missing_ok=True)
failed = results.count(False)
if failed == 0:
    print(f"{PASS} All {len(results)} assertions passed. Temp DB cleaned up.")
else:
    print(f"{FAIL} {failed}/{len(results)} assertions failed.")
sys.exit(failed)
