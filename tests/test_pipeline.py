"""Offline unit tests — pure logic, no network/API."""
import os
import tempfile

import pytest

os.environ["STUDIO_ROOT"] = tempfile.mkdtemp()

from studio_mcp import llm, prompts, render, state
from studio_mcp import server

# tool functions (FastMCP keeps the original callable on .fn)
_assemble = getattr(server.assemble, "fn", server.assemble)
_lock = getattr(server.lock_campaign, "fn", server.lock_campaign)


# --- llm._extract_json: tolerant JSON parsing ---
def test_extract_bare_json():
    assert llm._extract_json('{"a": 1}') == {"a": 1}


def test_extract_fenced_json():
    assert llm._extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_with_prose():
    assert llm._extract_json('Here it is: {"a": 1} done') == {"a": 1}


def test_extract_invalid_returns_none():
    assert llm._extract_json("not json at all") is None


def test_data_url_reads_local_file(tmp_path):
    image = tmp_path / "image.png"
    image.write_bytes(b"small image")

    result = llm._data_url(str(image))

    assert result.startswith("data:image/png;base64,")


# --- render helpers ---
def test_urls_walks_nested():
    obj = {"x": [{"url": "https://a.png"}, {"y": "https://b.mp4"}], "z": "no"}
    assert render._urls(obj) == ["https://a.png", "https://b.mp4"]


def test_urls_dedups():
    assert render._urls(["https://a.png", "https://a.png"]) == ["https://a.png"]


def test_local_path_passthrough_for_non_url():
    assert render._local_path("/tmp/x.png") == "/tmp/x.png"


# --- state ---
def test_state_slug():
    assert state._slug("MARÉA Spot!") == "mar-a-spot"


def test_state_save_load_roundtrip():
    state.save("t1", "x.json", {"k": "v"})
    assert state.load("t1", "x.json") == {"k": "v"}


def test_state_load_missing_returns_none():
    assert state.load("nope", "missing.json") is None


# --- prompts: 6-layer image prompt ---
def test_image_prompt_has_six_layers():
    shot = {"type": "wide", "camera_move": "static", "action": "she walks.",
            "subject": "a woman", "lens_hint": "wide", "time": "day"}
    lock = {"vibe": "filmic", "day_stock": "Portra 400", "hex_palette": ["#111"]}
    p = prompts.image_prompt(shot, lock)
    for layer in ("VIBE:", "SUBJECT:", "LIGHTING:", "CAMERA:", "FILM:"):
        assert layer in p
    assert "no digital grading" in p


def test_image_prompt_omits_face_with_ref():
    shot = {"type": "cu", "camera_move": "static", "action": "a beat",
            "subject": "a man", "lens_hint": "face", "time": "day"}
    p = prompts.image_prompt(shot, {}, has_ref=True)
    assert "do not describe the face" in p


# --- server.lock_campaign: aspect validation ---
def test_lock_rejects_unsupported_aspect():
    with pytest.raises(ValueError):
        _lock("t2", aspect="2.39:1", camera="35mm", day_stock="Portra",
              hex_palette=[], elements=[])


def test_lock_accepts_cinemascope():
    lk = _lock("t3", aspect="21:9", camera="35mm", day_stock="Portra",
               hex_palette=["#111"], elements=["@woman"])
    assert lk["aspect"] == "21:9" and lk["lock_id"]


# --- server.assemble: timeline + lip_sync ---
def test_assemble_totals_and_lipsync():
    state.save("t4", "plan.json", {"title": "T", "shots": [
        {"id": 1, "type": "wide", "duration_s": 4, "action": "waves roll"},
        {"id": 2, "type": "cu", "duration_s": 3, "action": 'she says "wait"'},
    ]})
    state.save("t4", "lock.json", {"audio": "diegetic SFX only"})
    m = _assemble("t4")
    assert m["total_duration_s"] == 7
    assert m["timeline"][1]["lip_sync"] is True
    assert m["timeline"][0]["lip_sync"] is False
