# Multi-agent orchestration plan

Refactor the linear studio-mcp pipeline (plan → gen → qc → animate → cut → assemble)
into an explicit multi-agent graph coordinated by the Anthropic Agent SDK.

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
- Orchestrator — Anthropic Agent SDK, shared trace context, guardrails between stages.

## Checklist

- [ ] Define agent interfaces + shared trace/context object
- [ ] Wrap existing MCP tools as agent-callable actions
- [ ] Planner → Generation → QC loop with retry + human gate
- [ ] Emit a structured trace per run (ties into the Langfuse work on `feat/langfuse-eval`)
- [ ] End-to-end run on the MARÉA project as the smoke test

## Status

🚧 In progress — interface design.
