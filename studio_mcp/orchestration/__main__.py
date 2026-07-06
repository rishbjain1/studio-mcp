"""CLI runner:  python -m studio_mcp.orchestration --project marea --brief "..."

Human gates prompt on the terminal; pass --yes for unattended runs.
"""
from __future__ import annotations

import argparse
import json

from . import Orchestrator, OrchestrationHalt, RunContext


def _terminal_gate(gate: str, info: dict) -> bool:
    answer = input(f"[gate:{gate}] {json.dumps(info, default=str)} — continue? [y/N] ")
    return answer.strip().lower() in ("y", "yes")


def main() -> None:
    parser = argparse.ArgumentParser(prog="studio-mcp orchestration")
    parser.add_argument("--project", required=True)
    parser.add_argument("--brief", required=True)
    parser.add_argument("--shots", type=int, default=12)
    parser.add_argument("--qc-retries", type=int, default=2)
    parser.add_argument("--yes", action="store_true", help="auto-approve all gates")
    args = parser.parse_args()

    ctx = RunContext(
        project=args.project,
        brief=args.brief,
        max_qc_retries=args.qc_retries,
        **({} if args.yes else {"approve": _terminal_gate}),
    )
    from .graph import PlannerAgent

    orch = Orchestrator(planner=PlannerAgent(n_shots=args.shots))
    try:
        result = orch.run(ctx)
    except OrchestrationHalt as halt:
        print(f"halted: {halt}")
        raise SystemExit(2)
    print(json.dumps({"trace": result["trace"],
                      "shots": len(result["clips"]),
                      "total_duration_s": result["manifest"]["total_duration_s"]},
                     indent=2))


if __name__ == "__main__":
    main()
