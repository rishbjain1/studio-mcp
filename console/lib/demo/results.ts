// Canned tool results for demo mode (STUDIO_DEMO=1) — lets the console run on
// Vercel with no MCP server behind it. Every one of the 14 tools returns a rich,
// coherent result from one project (MARÉA — "dawn swim"), so a visitor can click
// through the whole block-method pipeline and see believable output at each step.
// Shapes mirror real studio-mcp output.

const text = (obj: unknown) => ({
  content: [{ type: "text", text: JSON.stringify(obj, null, 2) }],
  isError: false,
});

const SHOTS = [
  {
    id: 1,
    type: "wide",
    camera_move: "slow push-in",
    duration_s: 4,
    action: "empty dawn beach, tide receding, one towel on the sand",
  },
  {
    id: 2,
    type: "medium",
    camera_move: "handheld follow",
    duration_s: 3,
    action: "she walks toward the water, robe drops out of frame",
  },
  {
    id: 3,
    type: "close",
    camera_move: "static",
    duration_s: 3,
    action: "breath held; she dips under the water, surface stills",
  },
];

const LOCK = {
  project: "marea",
  aspect: "16:9",
  camera: "35mm film",
  day_stock: "Kodak Vision3 250D",
  night_stock: "",
  hex_palette: ["#1b2a3a", "#c8a15a", "#e8e2d6"],
  elements: ["MARÉA woman", "dawn beach"],
  vibe: "slow-burn, pre-sunrise stillness, salt air",
  audio: "diegetic SFX only, no music; ocean + breath",
  lock_id: "9f3c1a7e02",
};

export const DEMO_RESULTS: Record<string, unknown> = {
  project_status: text({
    project: "marea",
    dir: "/studio-projects/marea",
    has_plan: true,
    shots: 3,
    has_lock: true,
    qc_done: [1, 2, 3],
    has_manifest: true,
  }),

  plan_shots: text({ title: "MARÉA — dawn swim", project: "marea", brief: "A woman swims alone at first light. Slow-burn, wordless.", shots: SHOTS }),

  lock_campaign: text(LOCK),

  reference_prompt: text({
    reference: "shot 2 — handheld follow",
    prompt:
      "MARÉA woman walking toward the sea on a dawn beach, 35mm film, Kodak " +
      "Vision3 250D, handheld follow, palette #1b2a3a/#c8a15a/#e8e2d6, soft " +
      "pre-sunrise light, grain, shallow depth of field, salt haze — diegetic " +
      "ocean + footsteps, no music.",
    grounded_in: ["day_stock", "hex_palette", "camera", "vibe"],
  }),

  palette_from_image: text({
    image: "refs/dawn_ocean.jpg",
    hex_palette: ["#1b2a3a", "#35506b", "#c8a15a", "#e8e2d6", "#0d1319"],
    note: "5-swatch palette extracted; slate + brass dominate, matches the lock.",
  }),

  gen_still: text({
    shot_id: 2,
    model: "soul_cinematic",
    prompt:
      "MARÉA woman walking toward the sea, dawn beach, 35mm film, handheld " +
      "follow, palette locked #1b2a3a/#c8a15a, salt haze, grain.",
    note: "",
    params: { aspect_ratio: "16:9", quality: "2k" },
    urls: ["https://cdn.studio.demo/marea/still_2_take1.png"],
  }),

  qc_still: text({
    shot_id: 2,
    scores: { intent: 89, look: 92, character: 86 },
    pass: true,
    fix_suggestion: "",
    image: "https://cdn.studio.demo/marea/still_2_take1.png",
    threshold: 75,
  }),

  animate: text({
    shot_id: 2,
    model: "img2vid_soul",
    prompt: "handheld follow as she walks to the water, robe drops out of frame",
    params: { duration_s: 3, aspect_ratio: "16:9", motion: "subtle" },
    urls: ["https://cdn.studio.demo/marea/clip_2.mp4"],
  }),

  upscale: text({
    media: "https://cdn.studio.demo/marea/clip_2.mp4",
    model: "topaz_video_2k",
    is_video: true,
    urls: ["https://cdn.studio.demo/marea/clip_2_2k.mp4"],
  }),

  train_character: text({
    soul_id: "soul_marea_v2_8f3c",
    name: "MARÉA woman",
    images_used: 4,
    soul2: true,
    note: "Character reference trained; pass custom_reference_id to gen_still to keep her consistent.",
  }),

  cut: text({
    project: "marea",
    clips: SHOTS.map((s) => ({
      shot_id: s.id,
      path: `https://cdn.studio.demo/marea/clip_${s.id}.mp4`,
      duration_s: s.duration_s,
    })),
    order: [1, 2, 3],
  }),

  assemble: text({
    project: "marea",
    title: "MARÉA — dawn swim",
    total_duration_s: 10,
    audio: LOCK.audio,
    timeline: SHOTS.map((s) => ({
      shot_id: s.id,
      type: s.type,
      duration_s: s.duration_s,
      action: s.action,
      clip: `https://cdn.studio.demo/marea/clip_${s.id}.mp4`,
      lip_sync: false,
    })),
  }),

  craft_lookup: text({
    question: "how do I keep dawn skin tones from going muddy on 250D?",
    answer:
      "Vision3 250D holds warmth well but dawn shade skews blue-green. Expose " +
      "+2/3 stop and warm the grade toward the locked #c8a15a; keep the key " +
      "soft and low so skin doesn't sink into the slate #1b2a3a shadows.",
    citations: [
      { source: "creative-rag: cinematography/film_stocks.md", score: 0.91 },
      { source: "creative-rag: grading/dawn_and_dusk.md", score: 0.87 },
    ],
    verified: true,
  }),

  list_models: text({
    kind: "image",
    current_default: "soul_cinematic",
    models: [
      { job_set_type: "soul_cinematic", name: "Soul Cinematic" },
      { job_set_type: "text2image_soul_v2", name: "Soul v2" },
      { job_set_type: "autosprite", name: "AutoSprite Animation" },
    ],
  }),
};

export function demoResult(name: string): unknown {
  return (
    DEMO_RESULTS[name] ??
    text({
      demo: true,
      note: `'${name}' has no fixture yet. This deployment runs in demo mode — run ` +
        "`studio-mcp --transport streamable-http` locally and start the console " +
        "without STUDIO_DEMO to invoke it for real.",
    })
  );
}
