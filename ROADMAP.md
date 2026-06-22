# studio-mcp — Roadmap

A living tool. The block-method film pipeline keeps deepening; studio-mcp grows
with it. Shipped tools cover the core loop (plan → lock → render → QC → assemble
+ soul-id). This is the backlog of richness still to wire in, drawn from the
production method.

## Shipped
- `plan_shots` — block-method shot plan (type · move · duration · lighting · lens · time · hold · vibe)
- `lock_campaign` — camera, day/night stock, HEX palette, lens map, style header, vibe, aspect
- `gen_still` — Soul, 6-layer prompt; per-shot `model`; `note` re-roll (QC fix → re-render)
- `qc_still` — vision style-drift QC vs shot intent + lock (aspect drift, text artifacts, plastic look)
- `animate` — img2vid; `direct` = DP persona reads the frame & directs the move; `hero` = Seedance timecoded/lip-sync
- `train_character` — soul-id self-clone (3–5 photos)
- `reference_prompt` — break a reference image into a 6-layer prompt (build from a ref)
- `palette_from_image` — extract a HEX palette from a moodboard/still
- `cut` — ffmpeg-concat clips into one mp4 (manifest → real film)
- `upscale` — final-polish image/video upscale
- `list_models` — surface image/video models for per-shot routing
- `assemble` — cut manifest (order, durations, diegetic-audio rules)
- `project_status`

## Backlog — prompt depth
- [ ] fuller Cinematic_Prompt_Library import (stocks/lenses/lighting/angles vocab per shot)

## Backlog — new tools (when self-clone / multi-character arrives)
- [ ] `swap_face` — NB-Pro/GPT-2 fixer: real-person face swap onto a finished Soul image ("keep everything identical")
- [ ] `layer_element` — build multi-element scenes one element per pass, each using the prior output as reference (no drift)
- [ ] `coverage` — one strong frame → 9-shot board in the same world (volume)

## Backlog — video
- [ ] motion-vocabulary mining: `/watch` a reference clip → named moves → timestamped prompt

## Backlog — workflow / output
- [ ] `<Project>_Storyboard.md` generation (the master doc per project)

## Backlog — engineering (DevEx / portfolio)
- [ ] REST render adapter (async submit→poll) alongside the CLI renderer (v2)
- [ ] designed Next.js console over the pipeline (TS/React — the frontend artifact, last)
- [ ] publish to an MCP registry (real users)

## Parked
- Agent fleet (`studio-director`/`studio-qc`/`studio-continuity`) — volume-mode only; Claude-in-chat already orchestrates for hero/low-volume work.
- Agent One / Lovart bulk paths — volume.

## Done this round
6-layer prompt engine · per-shot model routing · `list_models` · re-roll loop · vision motion-director (`animate direct`) · Seedance `hero` · `reference_prompt` · `palette_from_image` · `cut` (ffmpeg) · `upscale` · pytest + CI.

## Principle
The user briefs in plain language and time; studio-mcp translates to prompt
structure. Every new capability keeps that contract — the user never touches
prompt syntax.
