# Eval + tracing plan (Langfuse + benchmark suite)

Instrument the MCP pipeline with Langfuse tracing and add a benchmark suite that
measures agent behavior quantitatively.

## Tracing (Langfuse)

- Wrap each tool call + LLM call as a Langfuse span (the per-call cost + latency
  tracing already added in `studio_mcp/llm.py` feeds this directly).
- One trace per pipeline run; nested spans per stage (plan/gen/qc/animate/assemble).
- Tag traces by project + model so runs are comparable over time.

## Benchmark suite

Define a fixed task set and score each run on:

- **Latency** — per-tool and end-to-end wall time.
- **Accuracy** — QC pass rate (style-drift check), citation-verify pass rate for
  craft_lookup calls.
- **Context fidelity** — does the generated shot match the brief's constraints
  (aspect ratio, shot type, HEX, no-music rule).
- **Task completion** — did the full plan→assemble run finish without human rescue.

## Checklist

- [x] Langfuse SDK + span wrappers (`studio_mcp/lf.py`; keys-gated no-op; obs forwards every LLM call as a generation)
- [x] Benchmark task set (`eval/tasks.json` — 2 real briefs + 1 constraint-violating control)
- [x] Scorers: latency, QC-pass, constraint-match, completion (`eval/scorers.py`; citation-pass pending craft_lookup fixtures)
- [x] `eval/run_benchmark.py` — offline (deterministic, free) by default; --live guarded by STUDIO_LIVE=1
- [ ] Wire scorecard into CI as a non-blocking report first, then a gate

## Status

✅ Tracing + offline benchmark shipped (22/22 tests). Langfuse activates the
moment LANGFUSE_PUBLIC_KEY/SECRET_KEY exist — no code change needed.
