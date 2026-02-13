"""Skill report output helper.

Provides two patterns for skill output:
1. Simple: `write_skill_report()` - single report file
2. Parallel: `SkillRun` - structured directory for multi-agent skills

Directory Structure (Parallel):
    ~/projects/{project}/{skill}/
    ├── runs/{date}-{slug}/
    │   ├── context.md          # Shared context (Phase 0)
    │   ├── handoffs/           # Per-persona handoff files
    │   ├── outputs/            # Per-persona output files
    │   └── synthesis.md        # Final synthesized result
    └── reports/                # Published reports
"""

from __future__ import annotations

import fcntl
import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

def _get_claude_home() -> Path:
    return Path.home() / ".claude"

# Breadcrumb file for contract validation hooks (LIST of active skills)
ACTIVE_SKILLS_BREADCRUMB = _get_claude_home() / "tmp" / "active-skills.json"
# Session file written by SessionStart hook
CURRENT_SESSION_FILE = _get_claude_home() / "tmp" / "current-session.json"


def _read_session_field(key: str) -> str | None:
    """Read a field from the current session file."""
    if CURRENT_SESSION_FILE.exists():
        try:
            data = json.loads(CURRENT_SESSION_FILE.read_text())
            return data.get(key)
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def get_current_session_id() -> str | None:
    return _read_session_field("session_id")


def _slugify(title: str) -> str:
    """Convert title to URL-safe slug."""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def _detect_project() -> str | None:
    """Detect current project from environment or cwd.

    Detection order:
    1. PROJECT_ROOT env var (set by FormalTask workers)
    2. Git root of current directory
    3. Parent directory name if in ~/projects/
    4. None (falls back to skill-only path)
    """
    # 1. Check PROJECT_ROOT env var
    project_root = os.environ.get("PROJECT_ROOT")
    if project_root:
        return Path(project_root).name

    # 2. Try git root
    cwd = Path.cwd()
    git_dir = cwd
    while git_dir != git_dir.parent:
        if (git_dir / ".git").exists():
            return git_dir.name
        git_dir = git_dir.parent

    # 3. Check if in ~/projects/{project}/
    home = Path.home()
    projects_dir = home / "projects"
    try:
        rel = cwd.relative_to(projects_dir)
        parts = rel.parts
        if parts:
            return parts[0]
    except ValueError:
        pass

    return None


def _skill_base_dir(skill: str, project: str | None) -> Path:
    """Base directory for skill output: ~/projects/{project}/{skill}/ or ~/projects/{skill}/."""
    home = Path.home()
    if project:
        return home / "projects" / project / skill
    return home / "projects" / skill


def write_skill_report(skill: str, title: str, content: str) -> Path:
    """Write skill report to ~/projects/{project}/{skill}/reports/{date}-{slug}.md.

    If project cannot be detected, writes to ~/projects/{skill}/reports/.
    """
    project = _detect_project()
    reports_dir = _skill_base_dir(skill, project) / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    slug = _slugify(title)
    filename = f"{date_str}-{slug}.md"

    report_path = reports_dir / filename
    report_path.write_text(content)
    return report_path


@dataclass
class SkillRun:
    """Manages directory structure for a parallel skill invocation.

    Use for skills that spawn multiple subagents needing:
    - Shared context file
    - Per-persona handoff files
    - Per-persona output files
    - Final synthesis

    Example:
        >>> run = SkillRun.create("critiquing-exhaustively", "Review auth module")
        >>> run.write_context("# Context\\nAnalyzing auth module...")
        >>> run.write_handoff("skeptic", "# Skeptic Handoff\\n...")
        >>> run.write_synthesis("# Synthesis\\n...")
        >>> run.publish_report()  # Copies synthesis to reports/
    """

    skill: str
    title: str
    project: str | None
    dir: Path

    @classmethod
    def create(cls, skill: str, title: str, session_id: str | None = None) -> SkillRun:
        """Create a new skill run with standard directory structure.

        Creates:
            {base}/runs/{date}-{slug}/
            {base}/runs/{date}-{slug}/handoffs/
            {base}/runs/{date}-{slug}/outputs/

        Where {base} is ~/projects/{project}/{skill}/ or ~/projects/{skill}/

        Args:
            session_id: Session ID from hook context. Pass explicitly to avoid
                cross-instance contamination from the shared current-session.json file.
        """
        project = _detect_project()

        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        slug = _slugify(title)
        base_name = f"{date_str}-{slug}"

        base = _skill_base_dir(skill, project)

        # Auto-increment if directory exists
        runs_base = base / "runs"
        run_name = base_name
        counter = 1
        while (runs_base / run_name).exists():
            counter += 1
            run_name = f"{base_name}-{counter:02d}"

        run_dir = runs_base / run_name

        # Create directory structure
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "handoffs").mkdir(exist_ok=True)
        (run_dir / "outputs").mkdir(exist_ok=True)

        # Append to breadcrumb list for contract validation hooks
        # (list allows multiple skills in one session)
        ACTIVE_SKILLS_BREADCRUMB.parent.mkdir(parents=True, exist_ok=True)
        lock_path = ACTIVE_SKILLS_BREADCRUMB.with_suffix(".lock")
        with open(lock_path, "w") as lock_fd:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            existing: list = []
            if ACTIVE_SKILLS_BREADCRUMB.exists():
                try:
                    existing = json.loads(ACTIVE_SKILLS_BREADCRUMB.read_text())
                    if not isinstance(existing, list):
                        existing = []  # Migrate from old single-object format
                except (json.JSONDecodeError, ValueError):
                    existing = []

            existing.append(
                {
                    "skill": skill,
                    "run_dir": str(run_dir),
                    "project": project,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "session_id": session_id or get_current_session_id(),
                }
            )
            ACTIVE_SKILLS_BREADCRUMB.write_text(json.dumps(existing, indent=2))

        return cls(skill=skill, title=title, project=project, dir=run_dir)

    @property
    def context(self) -> Path:
        """Path to shared context file."""
        return self.dir / "context.md"

    @property
    def handoffs(self) -> Path:
        """Path to handoffs directory."""
        return self.dir / "handoffs"

    @property
    def outputs(self) -> Path:
        """Path to outputs directory."""
        return self.dir / "outputs"

    @property
    def synthesis(self) -> Path:
        """Path to synthesis file."""
        return self.dir / "synthesis.md"

    @property
    def log(self) -> Path:
        """Path to run log file."""
        return self.dir / "run.log"

    @property
    def reports_dir(self) -> Path:
        """Path to reports directory for this skill."""
        return _skill_base_dir(self.skill, self.project) / "reports"

    def write_context(self, content: str) -> Path:
        """Write shared context for all subagents."""
        self.context.write_text(content)
        return self.context

    def write_handoff(self, persona: str, content: str) -> Path:
        """Write handoff file for a specific persona."""
        path = self.handoffs / f"{_slugify(persona)}.md"
        path.write_text(content)
        return path

    def write_synthesis(self, content: str) -> Path:
        """Write final synthesis combining all persona outputs."""
        self.synthesis.write_text(content)
        return self.synthesis

    def publish_report(self, content: str | None = None) -> Path:
        """Publish final report to reports directory.

        Args:
            content: Report content. If None, uses synthesis.md content.

        Returns:
            Path to published report.
        """
        report_content = content or self.synthesis.read_text()
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = self.reports_dir / f"{self.dir.name}.md"
        report_path.write_text(report_content)
        return report_path
