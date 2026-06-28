"""Lightweight observability — per-LLM-call cost, latency, and a trace line.

Every LLM call through the `llm` layer is timed, priced from its token usage, and
emitted as one structured JSON trace line on stderr. No external deps, no vendor
agent — just enough to make cost and latency legible in a production pipeline.
"""
from __future__ import annotations

import json
import sys

# USD per 1M tokens (input, output). Source: claude-api reference, 2026-06.
PRICES: dict[str, tuple[float, float]] = {
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-opus-4-6": (5.0, 25.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-fable-5": (10.0, 50.0),
}
DEFAULT_PRICE = (5.0, 25.0)  # unknown model → assume Opus-tier (conservative)


def cost_usd(model: str, in_tok: int, out_tok: int) -> float:
    p_in, p_out = PRICES.get(model, DEFAULT_PRICE)
    return round((in_tok * p_in + out_tok * p_out) / 1_000_000, 6)


def trace_call(model: str, in_tok: int, out_tok: int, latency_ms: float) -> None:
    """Emit one structured trace line for an LLM call."""
    print(json.dumps({
        "event": "llm_call",
        "model": model,
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "cost_usd": cost_usd(model, in_tok, out_tok),
        "latency_ms": latency_ms,
    }), file=sys.stderr, flush=True)
