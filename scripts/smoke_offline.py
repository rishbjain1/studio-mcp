"""Offline smoke test — tool registration + assemble logic, no LLM calls."""
import asyncio
import os
import tempfile

from studio_mcp import server, state

os.environ["STUDIO_ROOT"] = tempfile.mkdtemp()

tools = asyncio.run(server.mcp.list_tools())
print("tools:", [t.name for t in tools])

fake_plan = {
    "project": "t", "title": "Test", "shots": [
        {"id": 1, "type": "wide", "camera_move": "static", "duration_s": 4,
         "subject": "sea", "action": "waves roll in"},
        {"id": 2, "type": "cu", "camera_move": "handheld", "duration_s": 3,
         "subject": "woman", "action": 'she says "wait"'},
    ],
}
state.save("t", "plan.json", fake_plan)
state.save("t", "lock.json", {"audio": "diegetic SFX only, no music"})

assemble = server.assemble.fn if hasattr(server.assemble, "fn") else server.assemble
m = assemble("t")
print("total_s:", m["total_duration_s"], "| audio:", m["audio"])
print("shot2 lip_sync:", m["timeline"][1]["lip_sync"], "(expect True)")
assert m["total_duration_s"] == 7
assert m["timeline"][1]["lip_sync"] is True
print("OFFLINE OK")
