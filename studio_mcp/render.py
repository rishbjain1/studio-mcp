"""Render backend — shells out to the Higgsfield CLI.

Decision (plan-interrogate 2026-06-20): CLI now, REST adapter in v2. This module
is the CLIRenderer; a future rest.py implements the same three primitives
(`upload`, `generate`, `train_soul`) so the server tools don't change.

Auth: `higgsfield auth login` once (device OAuth, no key). Models are picked by
the dev via env — run `higgsfield model list` to see options:
    STUDIO_IMAGE_MODEL   Soul image model (gen_still)
    STUDIO_VIDEO_MODEL   img2vid model (animate)
"""
from __future__ import annotations

import json
import os
import subprocess

CLI = "higgsfield"


def _run(args: list[str]) -> dict:
    """Run a higgsfield command with --json and return parsed output."""
    proc = subprocess.run(
        [CLI, *args, "--json"],
        capture_output=True,
        text=True,
        timeout=1800,  # renders are slow; --wait blocks
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"higgsfield {' '.join(args)} failed ({proc.returncode}): "
            f"{(proc.stderr or proc.stdout)[:600]}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"raw": proc.stdout}


def _model(env_var: str, kind: str) -> str:
    m = os.environ.get(env_var)
    if not m:
        raise RuntimeError(
            f"Set {env_var} to a Higgsfield {kind} model "
            f"(run `higgsfield model list` to see options)."
        )
    return m


def _urls(obj) -> list[str]:
    """Walk arbitrary JSON for http(s) result URLs."""
    found: list[str] = []

    def walk(o):
        if isinstance(o, str) and o.startswith("http"):
            found.append(o)
        elif isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(obj)
    # de-dup, keep order
    seen, out = set(), []
    for u in found:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def upload(path: str) -> str:
    """Upload a local media file, return its upload id."""
    out = _run(["upload", "create", path])
    uid = out.get("id") or out.get("upload_id")
    if not uid:
        # fall back: first id-looking value
        for k, v in (out.items() if isinstance(out, dict) else []):
            if "id" in k.lower() and isinstance(v, str):
                return v
        raise RuntimeError(f"No upload id in response: {str(out)[:300]}")
    return uid


def generate(
    model: str, prompt: str, image: str | None = None, params: dict | None = None
) -> dict:
    """Run an image or video generation job, blocking until done.

    `image` may be a local path or an upload id (paths auto-upload). `params` are
    extra model flags (e.g. {"aspect_ratio": "16:9", "quality": "2k"}). Returns
    {"urls": [...], "raw": <parsed json>}.
    """
    args = ["generate", "create", model, "--prompt", prompt, "--wait"]
    if image:
        args += ["--image", image]
    for k, v in (params or {}).items():
        if v is not None and v != "":
            args += [f"--{k}", str(v)]
    out = _run(args)
    return {"urls": _urls(out), "raw": out}


def train_soul(name: str, image_ids: list[str], soul2: bool = True) -> dict:
    """Train a Soul character reference from 3-5 uploaded image ids."""
    if not 3 <= len(image_ids) <= 5:
        raise ValueError("Soul training needs 3-5 images.")
    args = ["soul-id", "create", "--name", name]
    if soul2:
        args.append("--soul-2")
    for i in image_ids:
        args += ["--image", i]
    out = _run(args)
    soul_id = out.get("id") or out.get("soul_id")
    return {"soul_id": soul_id, "raw": out}


def image_model() -> str:
    return _model("STUDIO_IMAGE_MODEL", "Soul image")


def video_model() -> str:
    return _model("STUDIO_VIDEO_MODEL", "img2vid")
