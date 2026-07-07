"""Orchestration smoke tests — full graph end-to-end, offline.

llm.* and render.* are stubbed (no network/API); everything else — agents,
retry loop, gates, trace, state files — is the real code path.
"""
import json
import os
import tempfile

import pytest

os.environ["STUDIO_ROOT"] = tempfile.mkdtemp()

from studio_mcp import llm, render, state
from studio_mcp.orchestration import Orchestrator, OrchestrationHalt, RunContext

PLAN = {
    "title": "smoke",
    "shots": [
        {"id": 1, "type": "wide", "duration_s": 4, "action": "hero walks in",
         "camera_move": "slow push-in"},
        {"id": 2, "type": "close", "duration_s": 3, "action": 'she says "go"',
         "camera_move": "static"},
    ],
}


@pytest.fixture()
def project(monkeypatch):
    name = f"smoke-{os.urandom(4).hex()}"
    monkeypatch.setattr(llm, "chat_json", lambda messages: dict(PLAN))
    monkeypatch.setattr(render, "image_model", lambda: "stub_model")
    monkeypatch.setattr(
        render, "generate",
        lambda model, prompt, params=None: {"urls": [f"https://stub/{hash(prompt) & 0xffff}.png"]},
    )
    state.save(name, "lock.json", {
        "project": name, "aspect": "16:9", "camera": "35mm film",
        "day_stock": "Kodak Vision3 250D", "hex_palette": ["#111111"],
        "elements": [], "audio": "diegetic SFX only, no music",
    })
    return name


def test_full_graph_all_pass(project, monkeypatch):
    monkeypatch.setattr(
        llm, "vision_json",
        lambda image, prompt: {"scores": {"intent": 90, "look": 90, "character": 90},
                               "pass": True, "fix_suggestion": ""},
    )
    ctx = RunContext(project=project, brief="a smoke test spot")
    result = Orchestrator().run(ctx)

    assert result["manifest"]["total_duration_s"] == 7
    assert [c["shot_id"] for c in result["clips"]] == [1, 2]
    assert all(c["qc"]["pass"] for c in result["clips"])
    # trace persisted and replayable
    run = json.loads(open(result["trace"]).read())
    assert run["status"] == "complete"
    actions = [s["action"] for s in run["steps"]]
    assert "plan_shots" in actions and "assemble" in actions
    assert actions.count("gen_still") == 2 and actions.count("qc_still") == 2
    assert "gate:pre_assembly" in actions
    # every tool call carries latency (decisions and gates don't)
    tool_calls = {"plan_shots", "gen_still", "qc_still", "assemble"}
    assert all(s["latency_ms"] is not None for s in run["steps"] if s["action"] in tool_calls)


def test_qc_retry_uses_fix_suggestion(project, monkeypatch):
    verdicts = iter([
        {"scores": {"intent": 40, "look": 40, "character": 40},
         "pass": False, "fix_suggestion": "warmer light"},
        {"scores": {"intent": 90, "look": 90, "character": 90},
         "pass": True, "fix_suggestion": ""},
    ] + [{"scores": {"intent": 90, "look": 90, "character": 90},
          "pass": True, "fix_suggestion": ""}] * 4)
    monkeypatch.setattr(llm, "vision_json", lambda image, prompt: next(verdicts))

    ctx = RunContext(project=project, brief="retry spot")
    result = Orchestrator().run(ctx)

    gen_steps = [s for s in ctx.trace if s.action == "gen_still" and s.inputs["shot_id"] == 1]
    assert len(gen_steps) == 2
    assert gen_steps[1].inputs["note"] == "warmer light"  # QC feedback closed the loop
    assert result["manifest"]["total_duration_s"] == 7


def test_gate_halts_on_exhausted_qc(project, monkeypatch):
    monkeypatch.setattr(
        llm, "vision_json",
        lambda image, prompt: {"scores": {"intent": 10, "look": 10, "character": 10},
                               "pass": False, "fix_suggestion": "hopeless"},
    )
    declined = []

    def gate(name, info):
        declined.append(name)
        return False

    ctx = RunContext(project=project, brief="drifting spot",
                     approve=gate, max_qc_retries=1)
    with pytest.raises(OrchestrationHalt):
        Orchestrator().run(ctx)

    assert declined == ["qc_exhausted"]
    run = state.load(project, f"runs/{ctx.run_id}.json")
    assert run["status"] == "halted"


def test_gate_approval_forces_shot_through(project, monkeypatch):
    monkeypatch.setattr(
        llm, "vision_json",
        lambda image, prompt: {"scores": {"intent": 10, "look": 10, "character": 10},
                               "pass": False, "fix_suggestion": "still off"},
    )
    ctx = RunContext(project=project, brief="director overrides",
                     approve=lambda name, info: True, max_qc_retries=1)
    result = Orchestrator().run(ctx)

    assert all(c.get("forced") for c in result["clips"])
    assert result["manifest"]["total_duration_s"] == 7


def test_sdk_planner_offline(project, monkeypatch):
    """SDKPlannerAgent drives the same graph; the Agent SDK query is stubbed."""
    # Optional extra: pip install studio-mcp[sdk]. Skip cleanly if absent.
    pytest.importorskip("claude_agent_sdk")
    from claude_agent_sdk import AssistantMessage, TextBlock

    from studio_mcp.orchestration import sdk_planner

    async def fake_query(*, prompt, options=None):
        assert "shot" in prompt.lower()  # got the real plan_user prompt
        yield AssistantMessage(
            content=[TextBlock(text=json.dumps(PLAN))], model="stub-model"
        )

    monkeypatch.setattr(sdk_planner, "query", fake_query)
    monkeypatch.setattr(
        llm, "vision_json",
        lambda image, prompt: {"scores": {"intent": 90, "look": 90, "character": 90},
                               "pass": True, "fix_suggestion": ""},
    )

    ctx = RunContext(project=project, brief="sdk-planned spot")
    orch = Orchestrator(planner=sdk_planner.SDKPlannerAgent())
    result = orch.run(ctx)

    assert result["manifest"]["total_duration_s"] == 7
    assert state.load(project, "plan.json")["brief"] == "sdk-planned spot"
    assert any(s.agent == "planner-sdk" for s in ctx.trace)
