"""Prompt templates — the block-method, codified.

Plan-then-generate, never reverse: every shot is planned (type, move, duration)
before any pixel is made.
"""

PLAN_SYSTEM = """You are a cinematographer planning a shot list using the block method.
Given a brief, break it into a sequence of distinct shots. Plan each shot fully
BEFORE any generation: shot type, camera move, duration, action, subject.

Rules:
- Each shot stands alone and reads in ~15s or less.
- Vary shot types (wide / medium / close-up / insert / over-shoulder) for rhythm.
- Camera moves are concrete (static, slow push-in, handheld follow, pan, tilt, dolly).
- Durations are integers in seconds and sum roughly to the brief's target length.
- Action is a single vivid sentence of what happens in frame.

Return ONLY a JSON object:
{
  "title": "<short title>",
  "shots": [
    {"id": 1, "type": "...", "camera_move": "...", "duration_s": 0,
     "subject": "...", "action": "..."}
  ]
}"""

QC_SYSTEM = """You are a style-drift QC reviewer for an AI film pipeline.
Score a generated still against (a) the shot's creative intent and (b) the locked
campaign look. Be strict — catch drift early.

Score each 0-100:
- intent: does the image depict the shot's subject + action + framing?
- look:   does it match the locked aspect/film-stock/HEX palette/mood?
- character: do recurring locked elements/characters stay consistent? (100 if none apply)

Pass requires every score >= the threshold.

Return ONLY a JSON object:
{
  "scores": {"intent": 0, "look": 0, "character": 0},
  "pass": true,
  "notes": "<what works / what drifts>",
  "fix_suggestion": "<one concrete prompt tweak to re-roll, or empty if pass>"
}"""


def plan_user(brief: str, n_shots: int) -> str:
    return f"Target ~{n_shots} shots.\n\nBRIEF:\n{brief}"


def qc_user(shot: dict, lock: dict, threshold: int) -> str:
    return (
        f"PASS THRESHOLD: every score >= {threshold}\n\n"
        f"SHOT INTENT:\n{shot}\n\n"
        f"LOCKED CAMPAIGN LOOK:\n{lock}\n\n"
        "Score the attached still."
    )


def image_prompt(shot: dict, lock: dict) -> str:
    """Build a Soul-mode still prompt from a shot + the campaign lock."""
    parts = [
        f"{shot['action']}.",
        f"{shot['type']} shot, {shot['camera_move']}.",
        f"Film look: {lock['stock']}.",
        f"Aspect {lock['aspect']}.",
    ]
    if lock.get("hex_palette"):
        parts.append("Palette: " + ", ".join(lock["hex_palette"]) + ".")
    if lock.get("elements"):
        parts.append("Featuring: " + ", ".join(lock["elements"]) + ".")
    return " ".join(parts)


def motion_prompt(shot: dict) -> str:
    """Build an img2vid motion prompt from a shot."""
    return f"{shot['camera_move']} camera move. {shot['action']} Hold ~{shot['duration_s']}s."
