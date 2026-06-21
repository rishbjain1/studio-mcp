# studio-mcp — Roadmap

A living tool. The block-method film pipeline keeps deepening; studio-mcp grows
with it. Shipped tools cover the core loop (plan → lock → render → QC → assemble
+ soul-id). This is the backlog of richness still to wire in, drawn from the
production method.

## Shipped
- `plan_shots` — block-method shot plan (type · move · duration · lighting · lens · time · hold)
- `lock_campaign` — camera, day/night stock, HEX palette, lens map, style header, vibe, aspect
- `gen_still` — Higgsfield Soul, 6-layer prompt (VIBE/SUBJECT/LIGHTING/CAMERA/FILM/TOOL), aspect + ref + quality params
- `qc_still` — vision style-drift QC vs shot intent + lock (catches aspect drift, text artifacts, plastic look)
- `animate` — img2vid, operator-as-human motion prompt + AI-tell negatives
- `train_character` — soul-id self-clone (3–5 photos)
- `assemble` — cut manifest (order, durations, diegetic-audio rules)
- `project_status`

## Backlog — prompt depth
- [ ] HEX-from-image: lock palette from an uploaded reference (Soul `medias`)
- [ ] reference-breakdown: build a prompt *from* a reference image (extract vibe/light/finish, swap subject)
- [ ] fuller Cinematic_Prompt_Library import (stocks/lenses/lighting/angles vocab per shot)

## Backlog — new tools
- [ ] `swap_face` — NB-Pro/GPT-2 fixer: real-person face swap onto a finished Soul image ("keep everything identical")
- [ ] `layer_element` — build multi-element scenes one element per pass, each using the prior output as reference (no drift)
- [ ] `coverage` — one strong frame → 9-shot board in the same world
- [ ] `upscale` — Topaz / Higgsfield at the end

## Backlog — video (animate gets richer)
- [ ] seedance-prompt-structure skeleton for hero/dialogue (timestamped beats, lip-sync, two-character negatives)
- [ ] backend routing: Kling (daily ~85%) vs Seedance (hero) vs Agent One (bulk)
- [ ] motion-vocabulary mining: `/watch` a reference clip → named moves → timestamped prompt

## Backlog — workflow / output
- [ ] `<Project>_Storyboard.md` generation (the master doc per project)
- [ ] manual vs agent path toggle per project
- [ ] director-note re-roll loop formalized: QC fail → apply fix_suggestion → re-render, until pass

## Backlog — engineering (DevEx / portfolio)
- [ ] REST render adapter (async submit→poll) alongside the CLI renderer (v2)
- [ ] designed Next.js console over the pipeline (TS/React — the frontend artifact)
- [ ] CI (GitHub Actions) + unit tests
- [ ] publish to an MCP registry (real users)

## Principle
The user briefs in plain language and time; studio-mcp translates to prompt
structure. Every new capability keeps that contract — the user never touches
prompt syntax.
