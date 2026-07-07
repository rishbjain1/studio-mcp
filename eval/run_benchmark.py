"""Run the benchmark task set against the pipeline and emit a scorecard.

Offline by default: llm/render are stubbed with each task's fixture plan, so
the run is deterministic and free — it exercises the real tool code paths
(plan_shots → lock_campaign → gen_still → qc_still → assemble) end to end.

Live mode (--live, plus STUDIO_LIVE=1 as a spend guard) uses the real LLM +
render backends and Langfuse tracing when keys are configured.

Usage:
    .venv/bin/python eval/run_benchmark.py            # offline, free
    STUDIO_LIVE=1 .venv/bin/python eval/run_benchmark.py --live
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))


def _fn(tool):
    return getattr(tool, "fn", tool)


def run_task(task: dict, offline: bool) -> dict:
    from studio_mcp import lf, llm, render, server

    project = f"bench-{task['id']}"
    timings: dict[str, float] = {}
    verdicts: list[dict] = []

    if offline:
        llm.chat_json = lambda messages, model=None: json.loads(json.dumps(task["stub_plan"]))
        llm.vision_json = lambda image, prompt, model=None: {
            "scores": {"intent": 90, "look": 90, "character": 90},
            "pass": True, "fix_suggestion": "",
        }
        render.image_model = lambda: "stub_model"
        render.generate = lambda model, prompt, image=None, params=None: {
            "urls": [f"stub://{project}.png"], "raw": {},
        }

    def timed(stage: str, fn, **kwargs):
        started = time.perf_counter()
        try:
            return fn(**kwargs)
        finally:
            timings[stage] = round((time.perf_counter() - started) * 1000, 1)

    with lf.span(f"benchmark:{task['id']}", offline=offline):
        plan = timed("plan_shots", _fn(server.plan_shots),
                     brief=task["brief"], project=project, n_shots=task["n_shots"])
        timed("lock_campaign", _fn(server.lock_campaign), project=project, **task["lock"])
        for shot in plan["shots"]:
            asset = timed(f"gen_still:{shot['id']}", _fn(server.gen_still),
                          project=project, shot_id=shot["id"])
            verdicts.append(timed(f"qc_still:{shot['id']}", _fn(server.qc_still),
                                  project=project, image=asset["urls"][0],
                                  shot_id=shot["id"]))
        manifest = timed("assemble", _fn(server.assemble), project=project)
    lf.flush()

    from eval.scorers import completion, constraint_match, qc_pass_rate, scorecard_row

    c_score, c_detail = constraint_match(plan, manifest, task["expected"])
    q_score, q_detail = qc_pass_rate(verdicts)
    done_score, done_detail = completion({"manifest": manifest})
    return scorecard_row(
        task["id"],
        {"constraint_match": round(c_score, 3), "qc_pass_rate": round(q_score, 3),
         "completion": done_score},
        {"constraints": c_detail, "qc": q_detail, "completion": done_detail},
        timings,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true",
                        help="use real LLM + render backends (costs money)")
    parser.add_argument("--out", default=str(HERE / "out" / "scorecard.json"))
    args = parser.parse_args()

    if args.live and os.environ.get("STUDIO_LIVE") != "1":
        print("refusing --live without STUDIO_LIVE=1 (spend guard)", file=sys.stderr)
        return 2

    os.environ["STUDIO_ROOT"] = tempfile.mkdtemp(prefix="studio-bench-")
    tasks = json.loads((HERE / "tasks.json").read_text())
    rows = [run_task(t, offline=not args.live) for t in tasks]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"mode": "live" if args.live else "offline",
                                    "rows": rows}, indent=2))

    print(f"{'task':30} {'agg':>6} {'constraint':>10} {'qc':>6} {'done':>5} {'e2e ms':>8}")
    for r in rows:
        print(f"{r['task']:30} {r['aggregate']:>6} "
              f"{r['scores']['constraint_match']:>10} {r['scores']['qc_pass_rate']:>6} "
              f"{r['scores']['completion']:>5} {r['latency_ms']['end_to_end_ms']:>8}")
    print(f"\nscorecard → {out_path}")

    # control task must score < 1 on constraints or the scorers are broken
    control = next(r for r in rows if r["task"] == "constraint-violator")
    if control["scores"]["constraint_match"] >= 1.0:
        print("FAIL: control task passed constraints — scorers not catching violations",
              file=sys.stderr)
        return 1
    return 0 if all(r["scores"]["completion"] == 1.0 for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
