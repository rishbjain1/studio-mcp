"""Prompt templates — the block method + 6-layer image prompt, codified.

From the ai-content-pipeline method:
- Plan the shot, THEN generate (block method). Never reverse.
- Every image prompt has 6 layers in order: VIBE, SUBJECT, LIGHTING, CAMERA,
  FILM/FINISH, TOOL NOTES. Blanks make the model fill with "average of
  everything" = generic.
- If a character reference (soul-id) is loaded, the SUBJECT layer does NOT
  describe the face — the ref handles it; it gets SHORTER (outfit/env/action).
- "Fine Film not Clean Digital" + grain/halation/shallow DOF = imperfection on
  purpose. End every prompt "no digital grading, untreated photographic look."
"""

# Aspect ratios across Higgsfield image models. Cinematic Studio models add
# 21:9 / 9:21 (cinemascope — closest to 2.39:1). The chosen model still validates
# its own supported set at generate time. No true 2.39:1 — use 21:9, crop in post.
ASPECT_RATIOS = {
    "1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3",
    "5:4", "4:5", "21:9", "9:21",
}

PLAN_SYSTEM = """You are a cinematographer planning a shot list using the block method.
Break the brief into distinct shots. Plan each shot FULLY before any generation.

Rules:
- Each shot stands alone and reads in ~15s or less. Vary shot types for rhythm.
- Camera moves are concrete (static, slow push-in, handheld follow, pan L/R, tilt, dolly, crash zoom).
- "lighting" describes direction + quality + time (e.g. "low backlight, soft, dusk").
- "time" is "day" or "night" (drives film-stock choice downstream).
- "lens_hint" suggests a focal length intent: "wide" / "natural" / "face" / "macro".
- Durations are integers in seconds, summing roughly to the brief's target length.

Return ONLY a JSON object:
{
  "title": "<short title>",
  "vibe": "<one line: feeling, era, references — the soul layer>",
  "shots": [
    {"id": 1, "type": "wide|medium|close-up|insert|over-shoulder",
     "camera_move": "...", "camera_position": "<eye-level / low / high / OTS>",
     "duration_s": 0, "hold": "<what holds at the end>",
     "time": "day|night", "subject": "<who/what + outfit + environment>",
     "action": "<one vivid sentence of what happens in frame>",
     "lighting": "<direction + quality + time>",
     "lens_hint": "wide|natural|face|macro"}
  ]
}"""

QC_SYSTEM = """You are a style-drift QC reviewer for an AI film pipeline.
Score a generated still against (a) the shot's creative intent and (b) the locked
campaign look. Be strict — catch drift early.

Score each 0-100:
- intent: does the image depict the shot's subject + action + framing + lens intent?
- look:   does it match the locked aspect/film-stock/HEX palette/grade/mood? Flag
          any on-frame text artifacts, digital-clean plastic look, or wrong ratio.
- character: do recurring locked elements/characters stay consistent? (100 if none apply)

Pass requires every score >= the threshold.

Return ONLY a JSON object:
{
  "scores": {"intent": 0, "look": 0, "character": 0},
  "pass": true,
  "notes": "<what works / what drifts>",
  "fix_suggestion": "<one concrete prompt or param tweak to re-roll, or empty if pass>"
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


# --- Default lens map (focal + aperture per intent) — overridable per lock ---
DEFAULT_LENS_MAP = {
    "wide": "14mm f/8, deep focus",
    "natural": "35mm f/2.8",
    "face": "75mm f/1.4, shallow depth of field",
    "macro": "100mm macro f/4",
}


def _stock(shot: dict, lock: dict) -> str:
    """Pick day or night stock from the lock based on the shot's time."""
    if shot.get("time") == "night" and lock.get("night_stock"):
        return lock["night_stock"]
    return lock.get("day_stock") or lock.get("stock") or "Kodak Vision3 250D"


def _lens(shot: dict, lock: dict) -> str:
    lens_map = {**DEFAULT_LENS_MAP, **(lock.get("lens_map") or {})}
    return lens_map.get(shot.get("lens_hint", "natural"), lens_map["natural"])


def image_prompt(shot: dict, lock: dict, has_ref: bool = False) -> str:
    """Build a 6-layer Soul prompt from a shot + the campaign lock.

    has_ref=True (a soul-id/character ref is passed separately) => the SUBJECT
    layer omits the face description; the reference handles identity.
    """
    action = shot["action"].rstrip(". ")
    subject = shot.get("subject", "").rstrip(". ")

    # 1. VIBE
    vibe = (lock.get("vibe") or "cinematic, intimate, filmic").rstrip(". ")
    # 2. SUBJECT (shorter when a face ref is loaded)
    if has_ref:
        subj_line = f"{action}. {subject} — frame the referenced character into the scene; do not describe the face."
    else:
        subj_line = f"{action}. {subject}."
    if lock.get("elements"):
        subj_line += " Featuring: " + ", ".join(lock["elements"]) + "."
    # 3. LIGHTING
    lighting = shot.get("lighting") or "natural practical light, soft"
    # 4. CAMERA
    camera = (
        f"{shot['type']} shot, {_lens(shot, lock)}, "
        f"{shot.get('camera_position', 'eye-level')}, {shot['camera_move']}"
    )
    # 5. FILM / FINISH
    finish = (
        f"shot on {_stock(shot, lock)}; Fine Film not Clean Digital; "
        "fine grain, gentle halation in highlights, shallow depth of field"
    )
    if lock.get("hex_palette"):
        finish += "; dominant colors: " + ", ".join(lock["hex_palette"])
    # 6. TOOL NOTES
    tool = "no digital grading, no LUT, untreated photographic look"
    if lock.get("style_header"):
        tool = lock["style_header"] + ". " + tool

    return (
        f"VIBE: {vibe}. "
        f"SUBJECT: {subj_line} "
        f"LIGHTING: {lighting}. "
        f"CAMERA: {camera}. "
        f"FILM: {finish}. "
        f"{tool}."
    )


# --- Vision motion-director persona (reads the actual frame, decides the move) ---
DP_SYSTEM = """You are a Director of Photography, film director, and creative director.
Your job is to animate a still image cinematically.
You read the scene — composition, subject, environment, mood, light — and decide the
single most cinematic way to bring it to life through camera movement and motion.
You think in shots, not effects. Every movement has a reason: a slow push on a face is
tension; a handheld drift on a street is presence and energy; a static wide on a
landscape is weight and atmosphere. Never move for the sake of moving.

Defaults:
- The camera always feels operated by a human, never automated.
- Handheld with organic micro-movement unless the scene calls for otherwise.
- No unmotivated zooms.
- Motion serves the emotion of the image.
- Every shot has a point of view."""


def direct_motion_user(shot: dict) -> str:
    return (
        "Read the attached frame — composition, subject, light, mood, point of view. "
        f"Shot intent: {shot['action'].rstrip('. ')} "
        f"(planned as {shot['type']}, {shot['camera_move']}, ~{shot['duration_s']}s). "
        "Decide the single most cinematic camera movement to bring THIS frame to life. "
        "Give a tight motion direction (2-4 sentences): the move, its motivation "
        "(what emotion/POV it serves), and how a human operator executes it — hands, "
        "weight, reaction timing. Do not describe effects; describe an operated camera."
    )


def motion_tech(shot: dict) -> str:
    """The technical layer appended under any motion direction — keeps it rendering clean."""
    return (
        f"Single uninterrupted take, ~{shot['duration_s']}s. "
        "Allow micro-life (blinks, breath, gaze shifts); lock identity. "
        "Negative: smooth/mechanical zoom, gimbal-stabilized, locked tripod, "
        "plastic skin, warped face, extra fingers, subject moving when only the "
        "camera should, clean/static ending."
    )


# --- Reference-breakdown: build a prompt FROM a reference image ---
REF_BREAKDOWN_SYSTEM = """You break a reference image down into its ingredients so a
new image can be built in the same world — references are for understanding, not
copying. Read the attached image in extreme detail and extract: vibe (feeling/era/
references), lighting (direction, quality, time, sources), camera (shot type, lens
mm, aperture, depth of field, angle), and film/finish (stock, grain, halation,
color science). Then output a single ready-to-use prompt in the 6-layer form:
VIBE / SUBJECT / LIGHTING / CAMERA / FILM / TOOL NOTES, ending "no digital grading,
untreated photographic look". Be specific enough that the prompt could only describe
this look — no vague filler."""


def ref_breakdown_user(swap_subject: str) -> str:
    if swap_subject:
        return (
            f"Keep the lighting, camera, finish, and vibe of the attached image, but "
            f"SWAP THE SUBJECT to: {swap_subject}. Everything else stays locked."
        )
    return "Break down the attached image and output the 6-layer prompt for its look."


# --- HEX-from-image: extract a palette ---
PALETTE_SYSTEM = """You are a colorist. Read the attached image and extract its color
DNA as HEX codes. Return ONLY a JSON object:
{"dominant": "#......", "secondary": "#......", "accent": "#......",
 "hex_palette": ["#......", "#......", "#......"]}"""


# --- Seedance hero path: timecoded beats, lip-sync, liveness (per seedance-prompt-structure) ---
SEEDANCE_PREFIX = """Style: 8K cinematic. Photorealistic — no 3D render, no game engine.
Cinematography: naturalistic master cinematography. Lighting: natural light only —
contre-jour backlight, camera on shadow side, atmospheric haze. Color: 60:30:10
dominant/secondary/accent. Camera: physical cine lens, 180° shutter motion blur.
Skin: pore-level realism — vellus hair, capillary flush. Acting: top-tier — micro-pauses
before reactions, precise eye-line, wet living eyes with catch-lights, visible breath and
chest rise. Physics: gravity and inertia respected. Composition: rule of thirds + golden
ratio, every person moving from frame one. Continuity: identical across cuts, no identity
drift. Technical: 24fps, 8K, no jitter. Audio: environmental SFX only, no music, no subtitles."""


def seedance_hero_user(shot: dict, lock: dict) -> str:
    return (
        "Read the attached frame and write ONE Seedance hero video prompt for this "
        f"~{shot['duration_s']}s shot, using EXACTLY this structure and starting with the "
        "full style prefix verbatim:\n\n"
        f"{SEEDANCE_PREFIX}\n\n"
        "SUBJECT — who's in frame (each recurring element 'matches input 100%'), the goal + "
        "emotional beat. MULTISHOT.\n"
        "LOCATION — style reference only, not a fixed keyframe; subject moves through space.\n"
        "ACTION — one line of intent, then split the duration into timecoded SHOT 1/2/3 "
        "(0:00–0:0X …), each a beat, hard cut.\n"
        "CAMERA — per shot: angle, height, lens feel, movement, motivation (human-operated).\n"
        "STYLE — Dominant 60% / Secondary 30% / Accent 10% for this shot.\n"
        "CONSTRAINTS — 16:9; lip-sync any dialogue; force EVERY character alive (negative: "
        "non-speaker frozen/statue/passive); no eye glow; no slow-mo unless ramped.\n\n"
        f"Shot intent: {shot['action'].rstrip('. ')}. "
        f"Lock look: {lock.get('day_stock') or lock.get('stock', '')}, "
        f"palette {lock.get('hex_palette', [])}. Output ONLY the prompt."
    )


def motion_prompt(shot: dict) -> str:
    """Template motion prompt (fallback when not directing from the frame)."""
    return (
        f"Camera: {shot['camera_move']} — the operator's hands, slight breathing and "
        f"reframe wobble, no stabilization, no gimbal. "
        f"Action: {shot['action'].rstrip('. ')}. "
        f"Hold: {shot.get('hold', 'settle on the subject')}. " + motion_tech(shot)
    )
