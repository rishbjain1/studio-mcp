# Changelog

All notable changes to studio-mcp. Dates are ship dates.

## [Unreleased]

On feature branches, landing after review:

- `feat/next-console` — streamable-HTTP transport (`--transport streamable-http`)
  and a Next.js/TypeScript web console: tool browser, schema-driven invoke
  forms, per-call latency + LLM cost, NDJSON status streaming for long tools,
  localStorage run history, `STUDIO_DEMO=1` fixture mode.
- `feat/agent-sdk-orchestration` — multi-agent graph
  (Planner → Generation ⇄ QC → Assembly) with QC-retry via `fix_suggestion`,
  human-in-the-loop gates, replayable per-run traces, CLI runner, and an
  optional Anthropic Agent SDK planner (`pip install studio-mcp[sdk]`).
- `feat/langfuse-eval` — keys-gated Langfuse tracing (span per stage,
  generation per LLM call) and an offline benchmark suite with a
  constraint-violating control task and a `STUDIO_LIVE=1` spend guard
  (`pip install studio-mcp[eval]`).
- `feat/ci` — this CI pipeline (test matrix + package build) and changelog.

## [0.1.0] — 2026-07-06

Initial public release.

- 14 MCP tools over the block-method film pipeline: `plan_shots`,
  `lock_campaign`, `qc_still`, `assemble`, `gen_still`, `animate`,
  `train_character`, `cut`, `upscale`, `reference_prompt`,
  `palette_from_image`, `project_status`, `list_models`, `craft_lookup`.
- Per-LLM-call cost + latency tracing (`studio_mcp/obs.py`).
- Local JSON project state under `STUDIO_ROOT` (`studio_mcp/state.py`).
- Higgsfield CLI render backend; `craft_lookup` grounded by creative-rag.
- 15 offline tests.
