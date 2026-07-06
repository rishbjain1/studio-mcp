"""SDKPlannerAgent — PlannerAgent's decision layer on the Anthropic Agent SDK.

Drop-in replacement for PlannerAgent: instead of the raw-httpx `llm.chat_json`
call inside plan_shots, the shot plan comes from a Claude agent run via
`claude_agent_sdk.query` (which drives the local Claude Code runtime, so it
uses the operator's existing auth — no separate API key).

    from studio_mcp.orchestration import Orchestrator, RunContext
    from studio_mcp.orchestration.sdk_planner import SDKPlannerAgent

    Orchestrator(planner=SDKPlannerAgent()).run(RunContext(project=..., brief=...))
"""
from __future__ import annotations

import asyncio
from typing import Any

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

from .. import llm, state
from ..prompts import PLAN_SYSTEM, plan_user
from . import RunContext
from .graph import PlannerAgent


async def _plan_via_sdk(brief: str, n_shots: int) -> dict:
    options = ClaudeAgentOptions(
        system_prompt=PLAN_SYSTEM,
        max_turns=1,
        allowed_tools=[],  # pure planning — no tool use
    )
    chunks: list[str] = []
    async for message in query(prompt=plan_user(brief, n_shots), options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    chunks.append(block.text)
    plan = llm._extract_json("".join(chunks))
    if plan is None:
        raise ValueError(f"SDK planner returned no JSON plan: {''.join(chunks)[:300]}")
    return plan


class SDKPlannerAgent(PlannerAgent):
    """Plans shots through the Anthropic Agent SDK instead of llm.chat_json."""

    name = "planner-sdk"

    def run(self, ctx: RunContext) -> dict:
        existing = state.load(ctx.project, "plan.json")
        if existing is not None:
            ctx.record_decision(self.name, "reuse existing plan.json")
            return existing

        def _call(brief: str, n_shots: int) -> dict:
            plan: dict[str, Any] = asyncio.run(_plan_via_sdk(brief, n_shots))
            plan["project"] = ctx.project
            plan["brief"] = brief
            state.save(ctx.project, "plan.json", plan)
            return plan

        return ctx.call(self.name, "plan_shots(sdk)", _call,
                        brief=ctx.brief, n_shots=self.n_shots)
