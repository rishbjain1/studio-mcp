"""Provider-agnostic LLM layer.

One code path over any OpenAI-compatible Chat Completions endpoint, so the dev
picks the provider — Anthropic, OpenRouter, OpenAI, or a local server — purely
through env config. No provider is hard-coded.

Config (env):
    STUDIO_LLM_BASE_URL    default https://api.anthropic.com/v1
    STUDIO_LLM_MODEL       default claude-opus-4-8
    STUDIO_LLM_VISION_MODEL defaults to STUDIO_LLM_MODEL (must accept images)
    STUDIO_LLM_API_KEY     falls back to ANTHROPIC_API_KEY

Defaults target Anthropic's OpenAI-compatible endpoint (Bearer auth, accepts
image_url). Point the three vars at any other OpenAI-compatible provider —
OpenRouter, OpenAI, a local server — to switch, no code change.
"""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import re

import httpx

DEFAULT_BASE_URL = "https://api.anthropic.com/v1"
DEFAULT_MODEL = "claude-opus-4-8"


def _load_key() -> str:
    key = os.environ.get("STUDIO_LLM_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key.strip()
    raise RuntimeError(
        "No LLM API key. Set STUDIO_LLM_API_KEY (or ANTHROPIC_API_KEY)."
    )


def _cfg() -> dict:
    return {
        "base_url": os.environ.get("STUDIO_LLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
        "model": os.environ.get("STUDIO_LLM_MODEL", DEFAULT_MODEL),
        "vision_model": os.environ.get("STUDIO_LLM_VISION_MODEL")
        or os.environ.get("STUDIO_LLM_MODEL", DEFAULT_MODEL),
        "key": _load_key(),
    }


def _post(messages: list[dict], model: str, temperature: float) -> str:
    cfg = _cfg()
    resp = httpx.post(
        f"{cfg['base_url']}/chat/completions",
        headers={
            "Authorization": f"Bearer {cfg['key']}",
            "Content-Type": "application/json",
        },
        json={"model": model, "messages": messages, "temperature": temperature},
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def chat(messages: list[dict], model: str | None = None, temperature: float = 0.7) -> str:
    """Plain text completion."""
    return _post(messages, model or _cfg()["model"], temperature)


def chat_json(messages: list[dict], model: str | None = None, temperature: float = 0.4) -> dict:
    """Completion that must return JSON. Retries once with a stricter nudge."""
    text = _post(messages, model or _cfg()["model"], temperature)
    parsed = _extract_json(text)
    if parsed is not None:
        return parsed
    retry = messages + [
        {"role": "assistant", "content": text},
        {"role": "user", "content": "That was not valid JSON. Return ONLY the JSON object, no prose, no code fences."},
    ]
    text = _post(retry, model or _cfg()["model"], 0.0)
    parsed = _extract_json(text)
    if parsed is None:
        raise ValueError(f"Model did not return valid JSON:\n{text[:500]}")
    return parsed


def vision(image: str, prompt: str, model: str | None = None, temperature: float = 0.2) -> str:
    """Ask a vision model about an image (local path or http URL)."""
    url = image if image.startswith("http") else _data_url(image)
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": url}},
            ],
        }
    ]
    return _post(messages, model or _cfg()["vision_model"], temperature)


def vision_json(image: str, prompt: str, model: str | None = None) -> dict:
    text = vision(image, prompt + "\n\nReturn ONLY a JSON object.", model)
    parsed = _extract_json(text)
    if parsed is None:
        raise ValueError(f"Vision model did not return valid JSON:\n{text[:500]}")
    return parsed


def _data_url(path: str) -> str:
    p = Path(path).expanduser()
    if not p.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    mime = mimetypes.guess_type(str(p))[0] or "image/png"
    b64 = base64.b64encode(p.read_bytes()).decode()
    return f"data:{mime};base64,{b64}"


def _extract_json(text: str) -> dict | None:
    """Tolerant JSON extraction — handles bare JSON or ```json fenced blocks."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
    candidate = fence.group(1) if fence else text
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        # Grab the outermost {...} as a fallback.
        m = re.search(r"\{.*\}", candidate, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
    return None
