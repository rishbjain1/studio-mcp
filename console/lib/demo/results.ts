// Canned tool results for demo mode (STUDIO_DEMO=1) — lets the console run on
// Vercel with no MCP server behind it. Shapes mirror real studio-mcp output.

const text = (obj: unknown) => ({
  content: [{ type: "text", text: JSON.stringify(obj, null, 2) }],
  isError: false,
});

export const DEMO_RESULTS: Record<string, unknown> = {
  project_status: text({
    project: "marea",
    dir: "/studio-projects/marea",
    has_plan: true,
    shots: 3,
    has_lock: true,
    qc_done: [1],
    has_manifest: false,
  }),
  plan_shots: text({
    title: "MARÉA — dawn swim",
    project: "marea",
    shots: [
      { id: 1, type: "wide", camera_move: "slow push-in", duration_s: 4,
        action: "empty dawn beach, tide receding, one towel on the sand" },
      { id: 2, type: "medium", camera_move: "handheld follow", duration_s: 3,
        action: "she walks toward the water, robe drops out of frame" },
      { id: 3, type: "close", camera_move: "static", duration_s: 3,
        action: "breath held; she dips under, surface stills" },
    ],
  }),
  lock_campaign: text({
    project: "marea",
    aspect: "16:9",
    camera: "35mm film",
    day_stock: "Kodak Vision3 250D",
    hex_palette: ["#1b2a3a", "#c8a15a"],
    elements: ["MARÉA woman", "dawn beach"],
    audio: "diegetic SFX only, no music",
    lock_id: "demo000000",
  }),
  qc_still: text({
    scores: { intent: 88, look: 91, character: 86 },
    pass: true,
    fix_suggestion: "",
    shot_id: 1,
    image: "https://demo.invalid/still_1.png",
  }),
  list_models: text({
    kind: "image",
    current_default: "soul_cinematic",
    models: ["soul_cinematic", "text2image_soul_v2"],
  }),
};

export function demoResult(name: string): unknown {
  return (
    DEMO_RESULTS[name] ??
    text({
      demo: true,
      note: `'${name}' needs a live studio-mcp server — this deployment runs in demo mode. ` +
        "Run `studio-mcp --transport streamable-http` locally and start the console " +
        "without STUDIO_DEMO to invoke it for real.",
    })
  );
}
