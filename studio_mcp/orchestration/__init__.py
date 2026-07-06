"""Multi-agent orchestration layer over the studio-mcp tools.

Coordinates PlannerAgent / GenerationAgent / QCAgent / AssemblyAgent as an
explicit agent graph with a shared, traceable context and human-in-the-loop
gates between stages. See PLAN.md.

Run:  python -m studio_mcp.orchestration --project marea --brief "..."
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from .. import state


class OrchestrationHalt(RuntimeError):
    """A human gate declined to continue; the run stops cleanly."""


@dataclass
class TraceStep:
    """One recorded step in an orchestration run (decision or tool call)."""

    agent: str
    action: str
    inputs: dict[str, Any] = field(default_factory=dict)
    output: Any = None
    error: str | None = None
    latency_ms: float | None = None


def _auto_approve(gate: str, info: dict[str, Any]) -> bool:
    return True


@dataclass
class RunContext:
    """Shared context threaded through every agent in a run.

    approve: human-in-the-loop gate — called at checkpoints (QC exhausted,
    pre-assembly). Return False to halt the run. Defaults to auto-approve so
    unattended runs and tests proceed.
    """

    project: str
    brief: str
    approve: Callable[[str, dict[str, Any]], bool] = _auto_approve
    max_qc_retries: int = 2
    qc_threshold: int = 75
    trace: list[TraceStep] = field(default_factory=list)
    run_id: str = field(default_factory=lambda: time.strftime("%Y%m%d-%H%M%S"))

    def record(self, step: TraceStep) -> None:
        self.trace.append(step)

    def record_decision(self, agent: str, decision: str) -> None:
        self.record(TraceStep(agent=agent, action="decision", output=decision))

    def call(self, agent: str, action: str, fn: Callable[..., Any], **inputs: Any) -> Any:
        """Run a tool call as a traced step; errors are recorded then re-raised."""
        started = time.perf_counter()
        step = TraceStep(agent=agent, action=action, inputs=inputs)
        try:
            step.output = fn(**inputs)
            return step.output
        except Exception as err:
            step.error = f"{type(err).__name__}: {err}"
            raise
        finally:
            step.latency_ms = round((time.perf_counter() - started) * 1000, 1)
            self.record(step)

    def gate(self, name: str, agent: str, info: dict[str, Any]) -> None:
        """Pause at a human checkpoint; halt the run if not approved."""
        approved = self.approve(name, info)
        self.record(TraceStep(agent=agent, action=f"gate:{name}", inputs=info,
                              output={"approved": approved}))
        if not approved:
            raise OrchestrationHalt(f"gate {name!r} declined: {info}")

    def save_trace(self, status: str = "complete") -> Any:
        """Persist the structured run trace under the project's runs/ dir."""
        return state.save(
            self.project,
            f"runs/{self.run_id}.json",
            {
                "run_id": self.run_id,
                "project": self.project,
                "brief": self.brief,
                "status": status,
                "steps": [vars(s) for s in self.trace],
            },
        )


from .graph import (  # noqa: E402  (re-export the graph API)
    Agent,
    AssemblyAgent,
    GenerationAgent,
    Orchestrator,
    PlannerAgent,
    QCAgent,
)

__all__ = [
    "Agent",
    "AssemblyAgent",
    "GenerationAgent",
    "Orchestrator",
    "OrchestrationHalt",
    "PlannerAgent",
    "QCAgent",
    "RunContext",
    "TraceStep",
]
