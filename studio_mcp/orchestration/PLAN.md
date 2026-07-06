# Multi-agent orchestration plan

Refactor the linear studio-mcp pipeline (plan → gen → qc → animate → cut → assemble)
into an explicit multi-agent graph with shared trace context and human gates.
Coordination is native Python (thin-first, same idiom as the raw-httpx `llm.py`);
adopting the Anthropic Agent SDK for LLM-driven planning is a tracked follow-up.

## Why

Today the pipeline is a fixed sequence of tool calls. Making it an agent graph gives:
- **Autonomy** — a planner agent decides which tools to call and in what order for a brief.
- **Traceability** — every agent step (decision, tool call, result) is logged and replayable.
- **Human-in-the-loop gates** — QC and cost checkpoints pause for approval before continuing.

## Shape

- `PlannerAgent` — turns a brief into a shot plan (wraps `plan_shots`).
- `GenerationAgent` — drives `gen_still` / `animate`, retries on QC failure.
- `QCAgent` — runs `qc_still`, decides pass/regenerate, escalates to human on repeated drift.
- `AssemblyAgent` — `cut` + `assemble`.
- Orchestrator — runs the graph, shared trace context, guardrails between stages.

## Checklist

- [x] Define agent interfaces + shared trace/context object
- [x] Wrap existing MCP tools as agent-callable actions
- [x] Planner → Generation → QC loop with retry + human gate
- [x] Emit a structured trace per run (ties into the Langfuse work on `feat/langfuse-eval`)
- [x] Offline end-to-end smoke test of the full graph (llm/render stubbed — see
      `tests/test_orchestration.py`: all-pass, retry-with-fix-suggestion, gate-halt,
      gate-override paths)
- [ ] Live end-to-end run on the MARÉA project (spends render + LLM credits — needs go-ahead)
- [x] SDKPlannerAgent — PlannerAgent's decision layer on the Anthropic Agent SDK
      (`sdk_planner.py`, optional `pip install studio-mcp[sdk]`; offline-tested with a
      stubbed `query`; live SDK runs use the local Claude runtime = operator's auth)

## Status

✅ Graph implemented + offline smoke tests green (20/20 suite).
Run it:  `python -m studio_mcp.orchestration --project marea --brief "..." [--yes]`
