"""studio-mcp — block-method film pipeline as MCP tools.

v1 (thin-first, no render backend): plan_shots, lock_campaign, qc_still, assemble.
v1.1 adds the render phase (train_character, gen_still, animate) via the
Higgsfield CLI. See README.

Run:  studio-mcp           (stdio)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os

import httpx
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
def gen_still(project: str, shot_id: int, note: str = "", model: str = "") -> dict:
    """Render a Soul-mode still for one shot, on-model to the campaign lock.

    Builds the prompt from the shot + lock, runs a Higgsfield image model, and
    returns the result URL(s). Run qc_still next.

    Args:
        project: project name.
        shot_id: which shot in plan.json.
        note: director's note for a re-roll — pass a failed qc_still's
            fix_suggestion here to correct the next render (closes the QC loop).
        model: image model job_set_type to use (e.g. "soul_cinematic",
            "text2image_soul_v2"). Defaults to STUDIO_IMAGE_MODEL. Use
            list_models("image") to see options.

    Requires: `higgsfield auth login` + a model (param or STUDIO_IMAGE_MODEL).
    """
    _, lock, shot = _load_shot(project, shot_id)
    soul = state.load(project, "soul.json")
    ref_id = (soul or {}).get("soul_id")
    prompt = image_prompt(shot, lock, has_ref=bool(ref_id))
    if note:
        prompt += f" DIRECTOR'S NOTE (correct these from the prior take): {note}"
    # aspect_ratio is universal across image models; other params are model-
    # specific, so opt in via STUDIO_IMAGE_PARAMS (JSON) rather than hardcode.
    params = {"aspect_ratio": lock.get("aspect", "16:9")}
    extra = os.environ.get("STUDIO_IMAGE_PARAMS")
    if extra:
        params.update(json.loads(extra))
    if ref_id:
        params["custom_reference_id"] = ref_id
    use_model = model or render.image_model()
    result = render.generate(use_model, prompt, params=params)
    asset = {
        "shot_id": shot_id,
        "model": use_model,
        "prompt": prompt,
        "note": note,
        "params": params,
        "urls": result["urls"],
    }
    state.save(project, f"assets/still_{shot_id}.json", asset)
    return asset


@mcp.tool()
def animate(
    project: str, shot_id: int, still: str,
    model: str = "", direct: bool = True, hero: bool = False,
) -> dict:
    """Animate a QC-passed still into a clip (img2vid).

    Three modes:
    - hero=True: the full Seedance hero path — vision reads the frame and writes a
      timecoded, lip-sync-aware Seedance prompt (style prefix + SHOT beats +
      liveness negatives); defaults to the seedance_2_0 model. For dialogue /
      one-take / must-be-perfect shots.
    - direct=True (default): a DP persona reads the frame and decides the cinematic
      move; technical operator-as-human layer appended. Daily driver.
    - both False: the fast template (no vision call). Bulk.

    Args:
        project: project name.
        shot_id: which shot (for motion/duration).
        still: local path or URL of the still to animate.
        model: video model job_set_type. Defaults: hero→seedance_2_0, else
            STUDIO_VIDEO_MODEL (e.g. kling3_0_turbo).
        direct: DP vision direction (ignored if hero=True).
        hero: Seedance hero path (timecoded beats, lip-sync).

    Requires: `higgsfield auth login` + a model.
    """
    _, lock, shot = _load_shot(project, shot_id)
    if hero:
        decision = llm.vision(
            still, prompts.DP_SYSTEM + "\n\n" + prompts.seedance_hero_user(shot, lock)
        ).strip()
        prompt = decision
        use_model = model or render.video_model_or_none() or "seedance_2_0"
    elif direct:
        decision = llm.vision(
            still, prompts.DP_SYSTEM + "\n\n" + prompts.direct_motion_user(shot)
        ).strip()
        prompt = f"{decision} {prompts.motion_tech(shot)}"
        use_model = model or render.video_model()
    else:
        decision = ""
        prompt = motion_prompt(shot)
        use_model = model or render.video_model()
    result = render.generate(use_model, prompt, image=still)
    asset = {"shot_id": shot_id, "model": use_model,
             "mode": "hero" if hero else ("directed" if direct else "template"),
             "motion_direction": decision, "prompt": prompt, "still": still,
             "urls": result["urls"]}
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


@mcp.tool()
def reference_prompt(reference: str, swap_subject: str = "") -> dict:
    """Break a reference image into a ready-to-use 6-layer prompt.

    References are for understanding, not copying: a vision model extracts the
    vibe/lighting/camera/finish and outputs a prompt that recreates the *look*.
    Optionally swap the subject while keeping the look locked.

    Args:
        reference: local path or URL of the reference image.
        swap_subject: if set, keep the look but swap to this subject
            (e.g. "a woman in a grey wool coat on a dusk shore").
    """
    instruction = prompts.REF_BREAKDOWN_SYSTEM + "\n\n" + prompts.ref_breakdown_user(swap_subject)
    text = llm.vision(reference, instruction).strip()
    return {"reference": reference, "swap_subject": swap_subject, "prompt": text}


@mcp.tool()
def palette_from_image(image: str) -> dict:
    """Extract a HEX palette (dominant/secondary/accent) from a reference image.

    Feed the returned hex_palette into lock_campaign to lock a film's color DNA
    from a moodboard or still.
    """
    return llm.vision_json(image, prompts.PALETTE_SYSTEM)


@mcp.tool()
def cut(project: str) -> dict:
    """Concatenate the project's rendered clips into one mp4 (hard cuts, in plan order).

    Reads the shot order from plan.json, pulls each animated clip (assets/clip_N.json),
    and ffmpeg-concats them into <project>_cut.mp4. Local + free (no credits). Run
    after animating the shots. Music is added in post (clips are SFX-only by rule).
    """
    plan = state.load(project, "plan.json")
    if plan is None:
        raise ValueError(f"No plan for project {project!r}.")
    urls = []
    for s in plan["shots"]:
        clip = state.load(project, f"assets/clip_{s['id']}.json")
        if clip and clip.get("urls"):
            urls.append(clip["urls"][0])
    if not urls:
        raise ValueError("No rendered clips found. Run animate on the shots first.")
    out = str(state.project_dir(project) / f"{project}_cut.mp4")
    render.concat_clips(urls, out)
    return {"project": project, "clips": len(urls), "cut": out}


@mcp.tool()
def upscale(media: str, kind: str = "image", model: str = "") -> dict:
    """Final-polish upscale of an image or video via Higgsfield.

    Args:
        media: local path or URL of the image/video to upscale.
        kind: "image" or "video".
        model: upscale model (defaults: image=bytedance_image_upscale,
            video=topaz_video). Use list_models to see options.

    Requires: `higgsfield auth login`. Costs credits.
    """
    is_video = kind == "video"
    use_model = model or (
        os.environ.get("STUDIO_UPSCALE_VIDEO_MODEL", "topaz_video") if is_video
        else os.environ.get("STUDIO_UPSCALE_IMAGE_MODEL", "bytedance_image_upscale")
    )
    result = render.upscale(use_model, media, is_video=is_video)
    return {"media": media, "kind": kind, "model": use_model, "urls": result["urls"]}


@mcp.tool()
def craft_lookup(question: str, top_k: int = 4) -> dict:
    """Query the creative-rag craft knowledge base for grounded, cited guidance.

    Pulls from your documented craft corpus (stocks, lenses, lighting, prompt
    structure) with citations + a verification verdict — use it while planning or
    locking a shot so prompts are grounded in your real library, not generic
    knowledge. Returns {answer, sources, verification}.

    Requires creative-rag running. Set CRAG_URL (default http://127.0.0.1:8000)
    and CRAG_API_KEY if the service is auth-gated.
    """
    base = os.environ.get("CRAG_URL", "http://127.0.0.1:8000").rstrip("/")
    headers = {"Content-Type": "application/json"}
    if os.environ.get("CRAG_API_KEY"):
        headers["X-API-Key"] = os.environ["CRAG_API_KEY"]
    resp = httpx.post(
        f"{base}/query",
        headers=headers,
        json={"query": question, "top_k": top_k},
        timeout=120,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"creative-rag {resp.status_code}: {resp.text[:300]}")
    return resp.json()


@mcp.tool()
def list_models(kind: str = "image") -> dict:
    """List available Higgsfield models so you can pick one for gen_still/animate.

    Args:
        kind: "image" (for gen_still) or "video" (for animate).

    Returns the model job_set_types + names. Playbook routing: stills →
    "soul_cinematic" (Soul Cinema) or "text2image_soul_v2" (Soul V2); video →
    "kling3_0_turbo"/"kling3_0" (daily driver ~85%) or "seedance_2_0" (hero,
    zero morph, lip-sync). Pass the chosen job_set_type as the `model` arg.

    Requires: `higgsfield auth login`.
    """
    models = render.list_models("video" if kind == "video" else "image")
    return {
        "kind": kind,
        "current_default": (render.video_model_or_none() if kind == "video"
                            else render.image_model_or_none()),
        "models": models,
    }


def main() -> None:
    parser = argparse.ArgumentParser(prog="studio-mcp")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="stdio for local MCP clients; streamable-http for the web console",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8321)
    args = parser.parse_args()
    if args.transport == "streamable-http":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
