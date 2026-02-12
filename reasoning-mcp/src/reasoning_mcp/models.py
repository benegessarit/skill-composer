"""Data models for the Generative Agent Ensemble MCP."""
from dataclasses import dataclass, field


@dataclass
class Agent:
    """A generated persona for reasoning about a specific question."""

    name: str
    role: str
    purpose: str
    perspective: str
    is_chaos: bool = False
    is_orchestrator: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "purpose": self.purpose,
            "perspective": self.perspective,
            "is_chaos": self.is_chaos,
            "is_orchestrator": self.is_orchestrator,
        }


@dataclass
class Invocation:
    """Record of a single agent invocation."""

    agent: str
    response: str
    raises: list[str] = field(default_factory=list)
    suggests_next: str | None = None


@dataclass
class Perturbation:
    """Record of a perturbation applied to test reasoning robustness."""

    target: str
    mode: str
    impact: str  # survives, breaks, weakens
    explanation: str


@dataclass
class Session:
    """Tracks session state through the ensemble reasoning workflow."""

    id: str
    question: str
    agents: list[Agent] = field(default_factory=list)
    min_agents: int = 3
    invocations: list[Invocation] = field(default_factory=list)
    perturbations: list[Perturbation] = field(default_factory=list)
    synthesized: bool = False
