"""The agent graph: Planner → Generation ⇄ QC → Assembly.

Each agent wraps studio-mcp tool functions (the same callables the MCP server
exposes) as traced, agent-callable actions. The Orchestrator runs the graph
over a RunContext, so every decision, tool call, retry, and human gate lands
in one replayable trace.
"""
from __future__ import annotations

from typing import Any

from .. import server, state
from . import OrchestrationHalt, RunContext


def _fn(tool: Any):
    """FastMCP keeps the original callable on .fn (same trick as the tests)."""
    return getattr(tool, "fn", tool)


class Agent:
    """Base agent. Subclasses wrap studio-mcp tools as agent-callable actions."""

    name: str = "agent"

    def run(self, ctx: RunContext) -> Any:
        raise NotImplementedError


class PlannerAgent(Agent):
    """Turns a brief into a block-method shot plan (wraps plan_shots).

    Reuses an existing plan for the project — planning is the expensive,
    LLM-backed step, so it is idempotent per project.
    """

    name = "planner"

    def __init__(self, n_shots: int = 12):
        self.n_shots = n_shots

    def run(self, ctx: RunContext) -> dict:
        plan = state.load(ctx.project, "plan.json")
        if plan is not None:
            ctx.record_decision(self.name, "reuse existing plan.json")
            return plan
        return ctx.call(
            self.name, "plan_shots", _fn(server.plan_shots),
            brief=ctx.brief, project=ctx.project, n_shots=self.n_shots,
        )


class QCAgent(Agent):
    """Runs qc_still and decides pass / regenerate (wraps qc_still)."""

    name = "qc"

    def review(self, ctx: RunContext, shot_id: int, image: str) -> dict:
        return ctx.call(
            self.name, "qc_still", _fn(server.qc_still),
            project=ctx.project, image=image, shot_id=shot_id,
            threshold=ctx.qc_threshold,
        )


class GenerationAgent(Agent):
    """Drives gen_still per shot, retrying on QC failure with the QC agent's
    fix_suggestion as a director's note. Escalates to the human gate when
    retries are exhausted (repeated style drift)."""

    name = "generation"

    def __init__(self, qc: QCAgent | None = None):
        self.qc = qc or QCAgent()

    def run(self, ctx: RunContext) -> list[dict]:
        plan = state.load(ctx.project, "plan.json")
        if plan is None:
            raise ValueError(f"No plan for {ctx.project!r} — run PlannerAgent first.")
        clips: list[dict] = []
        for shot in plan["shots"]:
            clips.append(self._render_shot(ctx, shot["id"]))
        return clips

    def _render_shot(self, ctx: RunContext, shot_id: int) -> dict:
        note = ""
        verdict: dict = {}
        for _attempt in range(ctx.max_qc_retries + 1):
            asset = ctx.call(
                self.name, "gen_still", _fn(server.gen_still),
                project=ctx.project, shot_id=shot_id, note=note,
            )
            image = asset["urls"][0]
            verdict = self.qc.review(ctx, shot_id, image)
            if verdict.get("pass"):
                return {"shot_id": shot_id, "path": image, "qc": verdict}
            note = verdict.get("fix_suggestion", "")
        # Retries exhausted: a human decides whether to ship the last take.
        ctx.gate("qc_exhausted", self.name, {"shot_id": shot_id, "verdict": verdict})
        return {"shot_id": shot_id, "path": image, "qc": verdict, "forced": True}


class AssemblyAgent(Agent):
    """Builds the cut manifest from the plan + rendered clips (wraps assemble)."""

    name = "assembly"

    def run(self, ctx: RunContext, clips: list[dict] | None = None) -> dict:
        return ctx.call(
            self.name, "assemble", _fn(server.assemble),
            project=ctx.project,
            clips=[{"shot_id": c["shot_id"], "path": c["path"]} for c in (clips or [])],
        )


class Orchestrator:
    """Runs the full graph over one RunContext and persists the trace."""

    def __init__(
        self,
        planner: PlannerAgent | None = None,
        generation: GenerationAgent | None = None,
        assembly: AssemblyAgent | None = None,
    ):
        self.planner = planner or PlannerAgent()
        self.generation = generation or GenerationAgent()
        self.assembly = assembly or AssemblyAgent()

    def run(self, ctx: RunContext) -> dict:
        try:
            self.planner.run(ctx)
            clips = self.generation.run(ctx)
            ctx.gate("pre_assembly", "orchestrator",
                     {"clips": len(clips), "forced": sum(1 for c in clips if c.get("forced"))})
            manifest = self.assembly.run(ctx, clips)
        except OrchestrationHalt:
            ctx.save_trace(status="halted")
            raise
        except Exception:
            ctx.save_trace(status="failed")
            raise
        trace_path = ctx.save_trace(status="complete")
        return {"manifest": manifest, "clips": clips, "trace": str(trace_path)}
