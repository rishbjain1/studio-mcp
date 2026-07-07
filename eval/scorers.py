"""Benchmark scorers — pure functions over pipeline artifacts.

Each returns a float in [0, 1] plus a detail dict, so the scorecard can show
both the number and why.
"""
from __future__ import annotations

from typing import Any


def constraint_match(plan: dict, manifest: dict, expected: dict) -> tuple[float, dict]:
    """Does the generated plan honor the brief's hard constraints?"""
    checks: dict[str, bool] = {}
    shots = plan.get("shots", [])
    if "n_shots" in expected:
        checks["n_shots"] = len(shots) == expected["n_shots"]
    if "max_total_duration_s" in expected:
        total = sum(s.get("duration_s", 0) for s in shots)
        checks["duration"] = total <= expected["max_total_duration_s"]
    for word in expected.get("must_mention", []):
        text = " ".join(s.get("action", "") for s in shots).lower()
        checks[f"mentions:{word}"] = word.lower() in text
    if expected.get("no_music"):
        checks["no_music"] = "no music" in (manifest.get("audio", "") or "").lower()
    score = sum(checks.values()) / len(checks) if checks else 1.0
    return score, checks


def qc_pass_rate(verdicts: list[dict]) -> tuple[float, dict]:
    """Fraction of shots whose final QC verdict passed."""
    if not verdicts:
        return 0.0, {"verdicts": 0}
    passed = sum(1 for v in verdicts if v.get("pass"))
    return passed / len(verdicts), {"passed": passed, "total": len(verdicts)}


def completion(result: dict | None) -> tuple[float, dict]:
    """Did plan→assemble finish without human rescue?"""
    ok = bool(result and result.get("manifest"))
    return (1.0 if ok else 0.0), {"finished": ok}


def latency_summary(timings: dict[str, float]) -> dict[str, float]:
    """Not a score — raw per-stage + end-to-end wall times for the report."""
    out = dict(timings)
    out["end_to_end_ms"] = round(sum(timings.values()), 1)
    return out


def aggregate(scores: dict[str, float]) -> float:
    """One headline number per task: mean of the individual scores."""
    vals = list(scores.values())
    return round(sum(vals) / len(vals), 3) if vals else 0.0


def scorecard_row(task_id: str, scores: dict[str, float], details: dict[str, Any],
                  timings: dict[str, float]) -> dict:
    return {
        "task": task_id,
        "aggregate": aggregate(scores),
        "scores": scores,
        "details": details,
        "latency_ms": latency_summary(timings),
    }
