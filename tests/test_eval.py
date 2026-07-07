"""Eval layer tests — Langfuse wrapper (no-op + capture) and scorers. Offline."""
import os
import sys
import tempfile
from pathlib import Path

os.environ["STUDIO_ROOT"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.scorers import aggregate, completion, constraint_match, qc_pass_rate
from studio_mcp import lf, obs


# --- lf: disabled state is a clean no-op ---
def test_lf_disabled_without_keys(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    monkeypatch.setattr(lf, "_client", None)
    assert not lf.enabled()
    with lf.span("stage", project="x") as s:
        assert s is None
    lf.log_generation("m", 1, 2, 0.001, 12.5)  # must not raise
    lf.flush()


def test_obs_forwards_to_lf(monkeypatch):
    captured = []
    monkeypatch.setattr(lf, "log_generation",
                        lambda *args: captured.append(args))
    obs.trace_call("claude-sonnet-4-6", 1000, 500, 321.0)
    assert len(captured) == 1
    model, in_tok, out_tok, cost, latency = captured[0]
    assert (model, in_tok, out_tok, latency) == ("claude-sonnet-4-6", 1000, 500, 321.0)
    assert cost == obs.cost_usd("claude-sonnet-4-6", 1000, 500)


def test_lf_span_uses_client_when_enabled(monkeypatch):
    class FakeObservation:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    class FakeClient:
        def __init__(self):
            self.calls = []

        def start_as_current_observation(self, **kwargs):
            self.calls.append(kwargs)
            return FakeObservation()

        def flush(self):
            self.calls.append({"flushed": True})

    fake = FakeClient()
    monkeypatch.setattr(lf, "client", lambda: fake)
    with lf.span("plan", project="marea"):
        pass
    lf.log_generation("m1", 10, 20, 0.005, 99.0)
    assert fake.calls[0]["name"] == "plan"
    assert fake.calls[0]["as_type"] == "span"
    assert fake.calls[1]["as_type"] == "generation"
    assert fake.calls[1]["usage_details"] == {"input": 10, "output": 20}
    assert fake.calls[1]["cost_details"] == {"total": 0.005}


# --- scorers ---
PLAN = {"shots": [
    {"id": 1, "duration_s": 4, "action": "waves on the beach"},
    {"id": 2, "duration_s": 3, "action": "she enters the water"},
]}
MANIFEST = {"audio": "diegetic SFX only, no music"}


def test_constraint_match_all_pass():
    score, checks = constraint_match(PLAN, MANIFEST, {
        "n_shots": 2, "max_total_duration_s": 10,
        "must_mention": ["beach", "water"], "no_music": True,
    })
    assert score == 1.0 and all(checks.values())


def test_constraint_match_catches_violations():
    score, checks = constraint_match(PLAN, MANIFEST, {
        "n_shots": 3, "max_total_duration_s": 5, "must_mention": ["submarine"],
    })
    assert score == 0.0
    assert not checks["n_shots"] and not checks["duration"]
    assert not checks["mentions:submarine"]


def test_qc_pass_rate_and_completion():
    score, _ = qc_pass_rate([{"pass": True}, {"pass": False}])
    assert score == 0.5
    assert qc_pass_rate([])[0] == 0.0
    assert completion({"manifest": {"x": 1}})[0] == 1.0
    assert completion(None)[0] == 0.0


def test_aggregate():
    assert aggregate({"a": 1.0, "b": 0.5}) == 0.75
