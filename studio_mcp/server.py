"""studio-mcp — block-method film pipeline as MCP tools.

v1 (thin-first, no render backend): plan_shots, lock_campaign, qc_still, assemble.
v1.1 adds the render phase (train_character, gen_still, animate) via the
Higgsfield CLI. See README.

Run:  studio-mcp           (stdio)
"""
from __future__ import annotations

import hashlib

from mcp.server.fastmcp import FastMCP

from . import llm, prompts, render, state
from .prompts import (
    PLAN_SYSTEM,
    QC_SYSTEM,
    image_prompt,
    motion_prompt,
    plan_user,
    qc_user,
)

mcp = FastMCP("studio-mcp")


@mcp.tool()
def plan_shots(brief: str, project: str, n_shots: int = 12) -> dict:
    """Turn a brief into a structured block-method shot plan.

    Plans every shot (type, camera move, duration, action) before any pixel is
    generated. Saves to the project's plan.json and returns it.

    Args:
        brief: plain-language description of the spot/scene.
        project: project name (scopes all state, e.g. "marea").
        n_shots: target number of shots.
    """
    plan = llm.chat_json(
        [
            {"role": "system", "content": PLAN_SYSTEM},
            {"role": "user", "content": plan_user(brief, n_shots)},
        ]
    )
    plan["project"] = project
    plan["brief"] = brief
    state.save(project, "plan.json", plan)
    return plan


@mcp.tool()
def lock_campaign(
    project: str,
    aspect: str,
    camera: str,
    day_stock: str,
    hex_palette: list[str],
    elements: list[str],
    night_stock: str = "",
    vibe: str = "",
    style_header: str = "",
    lens_map: dict | None = None,
    audio: str = "diegetic SFX only, no music; lip-sync where dialogue",
) -> dict:
    """Lock the campaign look once — every shot's prompt inherits it.

    Args:
        project: project name.
        aspect: Soul aspect ratio — one of 1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3.
            (No 2.39:1 in Soul — use 16:9 and crop to scope in post.)
        camera: camera + film system, e.g. "35mm film".
        day_stock: daytime film stock, e.g. "Kodak Vision3 250D".
        hex_palette: HEX palette locking color DNA, e.g. ["#1b2a3a", "#c8a15a"].
        elements: recurring named people/props/locations to keep consistent.
        night_stock: nighttime stock, e.g. "Cinestill 800T" (optional).
        vibe: the soul layer — feeling/era/references (optional; plan_shots seeds it).
        style_header: grade + lighting + camera DNA baked into every prompt (optional).
        lens_map: focal+aperture per intent, e.g. {"face": "75mm f/1.4"} (optional).
        audio: audio rule (default: diegetic SFX, no music).
    """
    if aspect not in prompts.ASPECT_RATIOS:
        raise ValueError(
            f"aspect {aspect!r} not supported by Soul. Use one of: "
            + ", ".join(sorted(prompts.ASPECT_RATIOS))
        )
    lock = {
        "project": project,
        "aspect": aspect,
        "camera": camera,
        "day_stock": day_stock,
        "night_stock": night_stock,
        "hex_palette": hex_palette,
        "elements": elements,
        "vibe": vibe,
        "style_header": style_header,
        "lens_map": lens_map or {},
        "audio": audio,
    }
    lock["lock_id"] = hashlib.sha1(repr(sorted(lock.items())).encode()).hexdigest()[:10]
    state.save(project, "lock.json", lock)
    return lock


@mcp.tool()
def qc_still(project: str, image: str, shot_id: int, threshold: int = 75) -> dict:
    """Style-drift QC on a generated still against the shot intent + locked look.

    Vision model scores intent / look / character (0-100). Pass requires every
    score >= threshold. Saves the verdict and returns it. An agent re-rolls the
    still when pass is false, using fix_suggestion.

    Args:
        project: project name.
        image: local path or http URL of the still to review.
        shot_id: which shot in plan.json this still is for.
        threshold: minimum passing score per dimension.
    """
    plan = state.load(project, "plan.json")
    lock = state.load(project, "lock.json")
    if plan is None:
        raise ValueError(f"No plan for project {project!r}. Run plan_shots first.")
    if lock is None:
        raise ValueError(f"No lock for project {project!r}. Run lock_campaign first.")
    shot = next((s for s in plan["shots"] if s["id"] == shot_id), None)
    if shot is None:
        raise ValueError(f"Shot {shot_id} not in plan for {project!r}.")

    verdict = llm.vision_json(image, f"{QC_SYSTEM}\n\n{qc_user(shot, lock, threshold)}")
    verdict["shot_id"] = shot_id
    verdict["image"] = image
    state.save(project, f"qc/{shot_id}.json", verdict)
    return verdict


@mcp.tool()
def assemble(project: str, clips: list[dict] | None = None) -> dict:
    """Build the cut manifest — shot order, durations, and audio notes.

    Uses the plan for order/timing. If clips (e.g. [{"shot_id":1,"path":"..."}])
    are provided (v1.1+), they are attached per shot. The actual NLE cut stays
    manual in v1; this is the edit blueprint.

    Args:
        project: project name.
        clips: optional rendered-clip refs keyed by shot_id.
    """
    plan = state.load(project, "plan.json")
    lock = state.load(project, "lock.json")
    if plan is None:
        raise ValueError(f"No plan for project {project!r}. Run plan_shots first.")
    clip_by_shot = {c["shot_id"]: c.get("path") for c in (clips or [])}

    timeline = []
    for s in plan["shots"]:
        has_dialogue = any(w in s["action"].lower() for w in ("say", "says", "speak", "line:", '"'))
        timeline.append(
            {
                "shot_id": s["id"],
                "type": s["type"],
                "duration_s": s["duration_s"],
                "action": s["action"],
                "clip": clip_by_shot.get(s["id"]),
                "lip_sync": bool(has_dialogue),
            }
        )

    manifest = {
        "project": project,
        "title": plan.get("title", project),
        "total_duration_s": sum(s["duration_s"] for s in plan["shots"]),
        "audio": (lock or {}).get("audio", "diegetic SFX only, no music"),
        "timeline": timeline,
    }
    state.save(project, "manifest.json", manifest)
    return manifest


def _load_shot(project: str, shot_id: int) -> tuple[dict, dict, dict]:
    """Load (plan, lock, shot) or raise a clear error."""
    plan = state.load(project, "plan.json")
    lock = state.load(project, "lock.json")
    if plan is None:
        raise ValueError(f"No plan for project {project!r}. Run plan_shots first.")
    if lock is None:
        raise ValueError(f"No lock for project {project!r}. Run lock_campaign first.")
    shot = next((s for s in plan["shots"] if s["id"] == shot_id), None)
    if shot is None:
        raise ValueError(f"Shot {shot_id} not in plan for {project!r}.")
    return plan, lock, shot


@mcp.tool()
def gen_still(project: str, shot_id: int) -> dict:
    """Render a Soul-mode still for one shot, on-model to the campaign lock.

    Builds the prompt from the shot + lock, runs the Higgsfield image model
    (set STUDIO_IMAGE_MODEL), and returns the result URL(s). Run qc_still next.

    Requires: `higgsfield auth login` + STUDIO_IMAGE_MODEL.
    """
    _, lock, shot = _load_shot(project, shot_id)
    soul = state.load(project, "soul.json")
    ref_id = (soul or {}).get("soul_id")
    prompt = image_prompt(shot, lock, has_ref=bool(ref_id))
    params = {"aspect_ratio": lock.get("aspect", "16:9"), "quality": "2k"}
    if ref_id:
        params["custom_reference_id"] = ref_id
    result = render.generate(render.image_model(), prompt, params=params)
    asset = {"shot_id": shot_id, "prompt": prompt, "params": params, "urls": result["urls"]}
    state.save(project, f"assets/still_{shot_id}.json", asset)
    return asset


@mcp.tool()
def animate(project: str, shot_id: int, still: str) -> dict:
    """Animate a QC-passed still into a clip (img2vid).

    Args:
        project: project name.
        shot_id: which shot (for motion/duration).
        still: local path or URL of the still to animate.

    Requires: `higgsfield auth login` + STUDIO_VIDEO_MODEL.
    """
    _, _, shot = _load_shot(project, shot_id)
    prompt = motion_prompt(shot)
    result = render.generate(render.video_model(), prompt, image=still)
    asset = {"shot_id": shot_id, "prompt": prompt, "still": still, "urls": result["urls"]}
    state.save(project, f"assets/clip_{shot_id}.json", asset)
    return asset


@mcp.tool()
def train_character(project: str, name: str, photos: list[str]) -> dict:
    """Train a Soul character reference (self-clone) from 3-5 photos.

    Uploads each photo, trains a Soul-2 reference, saves the soul_id to project
    state. Use the soul_id in later gen_still runs for a face-consistent character.

    Requires: `higgsfield auth login`.
    """
    if not 3 <= len(photos) <= 5:
        raise ValueError("Provide 3-5 reference photos.")
    image_ids = [render.upload(p) for p in photos]
    result = render.train_soul(name, image_ids)
    record = {"name": name, "soul_id": result["soul_id"], "photos": photos}
    state.save(project, "soul.json", record)
    return record


@mcp.tool()
def project_status(project: str) -> dict:
    """Report what stages exist for a project (plan / lock / QC / manifest)."""
    plan = state.load(project, "plan.json")
    lock = state.load(project, "lock.json")
    manifest = state.load(project, "manifest.json")
    qc_dir = state.project_dir(project, create=False) / "qc"
    return {
        "project": project,
        "dir": str(state.project_dir(project, create=False)),
        "has_plan": plan is not None,
        "shots": len(plan["shots"]) if plan else 0,
        "has_lock": lock is not None,
        "qc_done": sorted(int(p.stem) for p in qc_dir.glob("*.json")) if qc_dir.exists() else [],
        "has_manifest": manifest is not None,
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
