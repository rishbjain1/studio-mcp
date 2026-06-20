"""Live smoke test — plan_shots through the real LLM layer (small, cheap)."""
import os
import tempfile

from studio_mcp import server

os.environ["STUDIO_ROOT"] = tempfile.mkdtemp()

plan_shots = getattr(server.plan_shots, "fn", server.plan_shots)
brief = "MARÉA — wordless coastal slow-burn. A woman in grey returns to a tide-worn shore at dusk; the sea remembers her. Diegetic SFX only."
plan = plan_shots(brief, project="marea", n_shots=4)

print("title:", plan.get("title"))
print("shots:", len(plan["shots"]))
for s in plan["shots"]:
    print(f"  [{s['id']}] {s['type']:8} {s['camera_move']:16} {s['duration_s']}s — {s['action'][:60]}")
assert len(plan["shots"]) >= 1
assert all({"id", "type", "camera_move", "duration_s", "action"} <= set(s) for s in plan["shots"])
print("LIVE OK")
