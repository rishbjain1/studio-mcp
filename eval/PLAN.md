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

- [ ] Add Langfuse SDK + span wrappers around tool/LLM calls
- [ ] Define benchmark task set (fixture briefs + expected constraints)
- [ ] Scorers: latency, QC-pass, citation-pass, constraint-match, completion
- [ ] `eval/run_benchmark.py` — run the set, emit a scorecard
- [ ] Wire scorecard into CI as a non-blocking report first, then a gate

## Status

🚧 In progress — tracing scaffolding. Builds on the per-call cost/latency obs
already on `main`.
