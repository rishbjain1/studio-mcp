"""Verify animate: take shot 1's rendered still and animate it (img2vid)."""
import os

os.environ["STUDIO_ROOT"] = os.path.expanduser("~/studio-projects")
os.environ.setdefault("STUDIO_VIDEO_MODEL", "kling3_0_turbo")

from studio_mcp import server, state

P = "marea"
animate = getattr(server.animate, "fn", server.animate)

still_asset = state.load(P, "assets/still_1.json")
url = still_asset["urls"][0]
print("animating shot 1 from:", url[:80], "...")
clip = animate(P, shot_id=1, still=url)
print("CLIP urls:", clip["urls"])
print("ANIMATE OK" if clip["urls"] else "ANIMATE returned no url")
