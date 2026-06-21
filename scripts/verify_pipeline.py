"""Full end-to-end verification on a real MARÉA shot:
plan_shots -> lock_campaign -> gen_still (real Higgsfield) -> qc_still (vision)."""
import os

os.environ["STUDIO_ROOT"] = os.path.expanduser("~/studio-projects")
os.environ.setdefault("STUDIO_IMAGE_MODEL", "cinematic_studio_soul_location")

from studio_mcp import server

P = "marea"
plan_shots = getattr(server.plan_shots, "fn", server.plan_shots)
lock = getattr(server.lock_campaign, "fn", server.lock_campaign)
gen = getattr(server.gen_still, "fn", server.gen_still)
qc = getattr(server.qc_still, "fn", server.qc_still)

brief = (
    "MARÉA — wordless coastal slow-burn. A woman in grey returns to a tide-worn "
    "shore at dusk; the sea remembers her. Diegetic SFX only."
)

plan = plan_shots(brief, project=P, n_shots=3)
print("PLAN:", plan["title"], "·", len(plan["shots"]), "shots · vibe:", plan.get("vibe", ""))
lk = lock(
    P,
    aspect="21:9",  # cinemascope — closest to 2.39:1
    camera="35mm film, soft handheld",
    day_stock="Kodak Vision3 250D",
    night_stock="Kodak Vision3 500T",
    hex_palette=["#1b2a3a", "#c8a15a", "#8a8f99"],
    elements=["a woman in a grey wool coat"],
    vibe=plan.get("vibe", ""),
    style_header="dusk coastal grade, low contrast, soft halation",
)
print("LOCK:", lk["lock_id"], "· aspect", lk["aspect"])

print("GEN shot 1 — real Higgsfield Soul render (blocks until done)...")
still = gen(P, shot_id=1)
print("STILL urls:", still["urls"])

img = still["urls"][0] if still["urls"] else None
if img:
    print("QC shot 1 (vision)...")
    v = qc(P, image=img, shot_id=1)
    print("QC pass:", v.get("pass"), "· scores:", v.get("scores"))
    print("notes:", str(v.get("notes", ""))[:220])
print("PIPELINE OK")
