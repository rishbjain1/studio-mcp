"""Chain smoke test — the studio trio end-to-end.

Exercises: ai-content-pipeline method (a planning/lock question) → studio-mcp
`craft_lookup` tool → creative-rag `/query` → grounded, cited, verified answer.

Needs creative-rag running on CRAG_URL (default http://127.0.0.1:8000):
    cd ~/creative-rag && .venv/bin/python -m uvicorn creative_rag.api:app --port 8000
"""
import os
import sys

from studio_mcp import server

CRAG_URL = os.environ.get("CRAG_URL", "http://127.0.0.1:8000")

# A real planning-stage question the skill would ask while locking a campaign.
QUESTION = "what film stock and lens for a moody dusk beach scene?"

craft_lookup = getattr(server.craft_lookup, "fn", server.craft_lookup)

try:
    res = craft_lookup(QUESTION, top_k=4)
except Exception as e:  # connection refused = service down
    print(f"CHAIN FAIL — creative-rag not reachable at {CRAG_URL}: {e}", file=sys.stderr)
    print("start it: cd ~/creative-rag && .venv/bin/python -m uvicorn creative_rag.api:app --port 8000",
          file=sys.stderr)
    raise SystemExit(1)

answer = res.get("answer", "")
sources = res.get("sources") or []
verification = res.get("verification") or {}

print("Q:", QUESTION)
print("answer:", answer[:200].replace("\n", " "), "...")
print("sources:", len(sources), "->", [s.get("source") for s in sources][:4])
print("verified supported:", verification.get("supported"))

# The chain is healthy only if it returned a grounded, cited answer.
assert answer and "not in the corpus" not in answer.lower(), "no grounded answer"
assert sources, "no citations returned"
assert verification.get("supported") is True, "answer not verified-supported"
print("CHAIN OK")
