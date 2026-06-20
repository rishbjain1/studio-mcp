"""Local JSON project state.

One folder per project under STUDIO_ROOT (default ~/studio-projects/):

    <project>/
        plan.json      shot plan
        lock.json      campaign look lock
        qc/<shot>.json  per-shot QC verdicts
        manifest.json  assembled cut
        assets/        rendered stills/clips (v1.1)

Human-inspectable, git-ignorable, and a clean contract a future console/DB
can read without touching this server.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path


def root() -> Path:
    return Path(os.environ.get("STUDIO_ROOT", str(Path.home() / "studio-projects"))).expanduser()


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9-]+", "-", name.strip().lower()).strip("-")
    if not s:
        raise ValueError(f"Invalid project name: {name!r}")
    return s


def project_dir(name: str, create: bool = True) -> Path:
    d = root() / _slug(name)
    if create:
        (d / "qc").mkdir(parents=True, exist_ok=True)
        (d / "assets").mkdir(parents=True, exist_ok=True)
    return d


def save(name: str, filename: str, data: dict) -> Path:
    path = project_dir(name) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
    return path


def load(name: str, filename: str) -> dict | None:
    path = project_dir(name, create=False) / filename
    if not path.exists():
        return None
    return json.loads(path.read_text())
