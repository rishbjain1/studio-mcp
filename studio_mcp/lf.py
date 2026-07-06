"""Optional Langfuse tracing — active only when keys are configured.

Set LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY (and LANGFUSE_HOST for
self-hosted) and every LLM call plus each benchmark/pipeline stage lands in
Langfuse as a span/generation. Without keys, every helper is a no-op, so the
pipeline has zero hard dependency on the vendor.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

_client: Any = None


def enabled() -> bool:
    return bool(
        os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY")
    )


def client() -> Any:
    """Lazy singleton; None when tracing is disabled or the SDK is missing."""
    global _client
    if _client is None and enabled():
        try:
            from langfuse import Langfuse
        except ImportError:
            return None
        _client = Langfuse()
    return _client


@contextmanager
def span(name: str, **metadata: Any) -> Iterator[Any]:
    """Trace a pipeline stage. No-op context manager when disabled."""
    c = client()
    if c is None:
        yield None
        return
    with c.start_as_current_observation(name=name, as_type="span",
                                        metadata=metadata or None) as s:
        yield s


def log_generation(model: str, input_tokens: int, output_tokens: int,
                   cost_usd: float, latency_ms: float) -> None:
    """Record one LLM call as a Langfuse generation (called from obs)."""
    c = client()
    if c is None:
        return
    with c.start_as_current_observation(
        name="llm_call",
        as_type="generation",
        model=model,
        usage_details={"input": input_tokens, "output": output_tokens},
        cost_details={"total": cost_usd},
        metadata={"latency_ms": latency_ms},
    ):
        pass


def flush() -> None:
    c = client()
    if c is not None:
        c.flush()
