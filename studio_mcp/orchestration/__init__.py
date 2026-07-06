"""Multi-agent orchestration layer over the studio-mcp tools.

Coordinates PlannerAgent / GenerationAgent / QCAgent / AssemblyAgent as an
explicit agent graph (Anthropic Agent SDK) with a shared, traceable context and
human-in-the-loop gates between stages. See PLAN.md.

Status: in progress — interfaces below are the target surface, not yet wired.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TraceStep:
    """One recorded step in an orchestration run (decision or tool call)."""

    agent: str
    action: str
    inputs: dict[str, Any] = field(default_factory=dict)
    output: Any = None
    latency_ms: float | None = None


@dataclass
class RunContext:
    """Shared context threaded through every agent in a run."""

    project: str
    brief: str
    trace: list[TraceStep] = field(default_factory=list)

    def record(self, step: TraceStep) -> None:
        self.trace.append(step)


class Agent:
    """Base agent. Subclasses wrap studio-mcp tools as agent-callable actions."""

    name: str = "agent"

    def run(self, ctx: RunContext) -> RunContext:  # pragma: no cover - stub
        raise NotImplementedError("orchestration agents not yet implemented")
