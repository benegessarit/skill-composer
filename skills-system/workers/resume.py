"""Worker resume library for resuming paused workers in tmux sessions.

Task #1808: Core library implementation.
Task #1809: Command documentation and integration.

Provides functionality to resume workers using Claude's --continue flag.
"""

import logging
import shlex
import subprocess
import time
import uuid
from pathlib import Path

from formaltask.db.path import get_db_path
from formaltask.paths import get_claude_home, task_worktree

# Task #2493: Import from consolidated tmux library
from formaltask.tmux import is_pane_alive

log = logging.getLogger(__name__)

# Time to wait for Claude to start before checking pane health
PANE_STARTUP_WAIT_SECONDS = 10.0

class WorkerResumeError(Exception):
    """Base exception for worker resume operations."""


class WorktreeNotFoundError(WorkerResumeError):
    """Raised when worktree doesn't exist."""

    def __init__(self, task_id: int):
        self.task_id = task_id
        super().__init__(f"Worktree not found for task {task_id}")


class SessionExpiredError(WorkerResumeError):
    """Raised when Claude session no longer exists."""

    def __init__(self, session_id: str, task_id: int):
        self.session_id = session_id
        self.task_id = task_id
        super().__init__(f"Session {session_id} expired. Run: /worker-spawn {task_id}")


class InvalidSessionIdError(WorkerResumeError):
    """Raised when session ID is invalid format."""


class TmuxSpawnError(WorkerResumeError):
    """Raised when tmux session spawn fails."""

    def __init__(self, task_id: int, reason: str):
        self.task_id = task_id
        self.reason = reason
        super().__init__(f"Failed to spawn tmux session for task {task_id}: {reason}")


def find_worktree(task_id: int) -> Path:
    """Find worktree for task using convention."""
    worktree_path = task_worktree(task_id)
    if not worktree_path.is_dir():
        raise WorktreeNotFoundError(task_id)
    return worktree_path


def read_and_validate_session_id(session_id_file: Path) -> str:
    """Read session ID and validate format."""
    if not session_id_file.exists():
        raise FileNotFoundError(f"Session ID file not found: {session_id_file}")

    session_id = session_id_file.read_text().strip()

    if not session_id:
        raise InvalidSessionIdError("Session ID file is empty")

    try:
        uuid.UUID(session_id)
    except ValueError as err:
        raise InvalidSessionIdError(f"Invalid UUID format: '{session_id}'") from err

    return session_id


def worktree_to_project_path(worktree: Path) -> str:
    """Convert worktree path to Claude's project path format.

    Claude Code stores sessions in ~/.claude/projects/<project-path>/<session-id>/
    where project-path is the absolute path with '/' and '.' replaced by '-'.

    Example:
        ~/.claude/worktrees/task-2185
        -> -Users-davidbeyer--claude-worktrees-task-2185
    """
    # Resolve to absolute path and convert to string
    abs_path = str(worktree.resolve())
    # Replace '/' and '.' with '-'
    return abs_path.replace("/", "-").replace(".", "-")


def verify_session_exists(session_id: str, task_id: int, worktree: Path) -> None:
    """Verify session file exists in Claude projects.

    Claude stores sessions per-project at:
    ~/.claude/projects/<project-path>/<session-id>.jsonl
    """
    project_path = worktree_to_project_path(worktree)
    projects_dir = get_claude_home() / "projects"
    session_file = projects_dir / project_path / f"{session_id}.jsonl"

    if not session_file.is_file():
        raise SessionExpiredError(session_id, task_id)


def _clear_blocked_state(task_id: int) -> None:
    """Clear blocked state atomically.

    Task #2487: Uses single UPDATE statement to set status='in_progress' and
    clear blocked_question in one atomic operation. Skipping transition_task_status()
    loses state machine validation, but blocked->in_progress is always valid.
    """
    import sqlite3

    from formaltask.db.connection import DatabaseConnection

    try:
        db_path = get_db_path()
        with DatabaseConnection(db_path, exclusive=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tasks SET status = 'in_progress', blocked_question = NULL "
                "WHERE id = ? AND status IN ('blocked_user', 'blocked')",
                (task_id,),
            )
        log.info("Cleared blocked state for task %d", task_id)
    except sqlite3.Error as error:
        log.debug("Clear blocked state for task %d: %s", task_id, error)


def resume_worker_in_tmux(task_id: int, response: str) -> str:
    """Resume worker in a tmux session using Claude's --continue flag.

    Uses the same two-step spawn pattern as parallel_start.spawn_worker:
    1. Create tmux session with bash shell
    2. Send claude command via send-keys

    This is more robust because:
    - If claude fails to start, shell remains for debugging
    - Arguments are properly quoted in the command string
    - Consistent behavior with spawn_worker

    Args:
        task_id: The task ID to resume.
        response: Context message to pass when resuming (e.g., human decision).

    Returns:
        Tmux session name (e.g., "task-42").

    Raises:
        WorktreeNotFoundError: If worktree doesn't exist.
        FileNotFoundError: If session_id file not found.
        InvalidSessionIdError: If session ID is invalid format.
        SessionExpiredError: If Claude session directory doesn't exist.
        TmuxSpawnError: If tmux operations fail.
    """
    # 1. Find worktree (validates it exists)
    worktree = find_worktree(task_id)

    # 2. Read and validate session ID
    session_id_file = worktree / ".task" / "session_id"
    session_id = read_and_validate_session_id(session_id_file)

    # 3. Verify session exists in Claude projects directory
    verify_session_exists(session_id, task_id, worktree)

    # 4. Clear blocked state if worker was blocked (we're providing the answer)
    _clear_blocked_state(task_id)

    # 5. Tmux session name - use task-{id} for consistency with spawn_worker
    tmux_session = f"task-{task_id}"

    # 6. Kill existing session if any (ignore errors)
    subprocess.run(
        ["tmux", "kill-session", "-t", tmux_session],
        capture_output=True,
        timeout=30,
    )

    # 7. Spawn resumed worker using two-step pattern (bash shell + send-keys)
    # This matches parallel_start.spawn_worker for consistency
    try:
        # Step 1: Create tmux session with bash shell
        subprocess.run(
            [
                "tmux",
                "new-session",
                "-d",
                "-s",
                tmux_session,
                "-c",
                str(worktree),
                "bash",
                "--norc",
                "--noprofile",
            ],
            check=True,
            timeout=30,
        )

        # Step 2: Send claude resume command via send-keys
        # Use --continue flag with session ID to auto-resume without picker
        # Use --permission-mode bypassPermissions like spawn_worker
        # Prepend 'set +m' to disable bash job control
        # Append 'exec bash' to keep shell alive after Claude exits
        # Prepend resume guidance: task list state is lost on --continue
        resume_msg = (
            "RESUME CONTEXT: Your task list (TaskCreate/TaskList) was reset by session restart. "
            "Do NOT recreate tasks from the previous session. Continue from where you left off.\n\n"
            + response
        )
        claude_cmd = (
            f"set +m; claude --continue {shlex.quote(session_id)} "
            f"--permission-mode bypassPermissions "
            f"{shlex.quote(resume_msg)}; exec bash"
        )
        subprocess.run(
            ["tmux", "send-keys", "-t", tmux_session, claude_cmd, "Enter"],
            check=True,
            timeout=30,
        )

        # Wait and verify pane is alive (matches spawn_worker pattern)
        time.sleep(PANE_STARTUP_WAIT_SECONDS)
        if not is_pane_alive(tmux_session):
            # Clean up orphaned tmux session before raising
            subprocess.run(
                ["tmux", "kill-session", "-t", tmux_session],
                capture_output=True,
                timeout=5,
            )
            raise TmuxSpawnError(task_id, "pane is dead after resume")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as err:
        # Clean up orphaned tmux session on failure
        subprocess.run(
            ["tmux", "kill-session", "-t", tmux_session],
            capture_output=True,
            timeout=5,
        )
        raise TmuxSpawnError(task_id, str(err)) from err

    return tmux_session
