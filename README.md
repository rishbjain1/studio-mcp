# studio-mcp

[![CI](https://github.com/rishbjain1/studio-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/rishbjain1/studio-mcp/actions/workflows/ci.yml)

**The block-method film pipeline as agent-callable MCP tools.**

An MCP server that lets an LLM agent drive a full `brief → shots → render → QC → cut`
workflow by calling tools — instead of clicking through generation UIs by hand.
Plan-then-generate, never reverse: every shot is planned (type, move, duration)
before any pixel is made, and every still is QC'd against a locked look so the
piece stays on-model.

![MARÉA shot 1 — Higgsfield Soul Cinema, 21:9, QC-passed](docs/marea_shot1.png)

> *Above: one shot from the brief "MARÉA — wordless coastal slow-burn" — planned,
> rendered on Higgsfield Soul Cinema at 21:9, and passed by the style-drift QC
> (intent 80 / look 84 / character 90). The agent re-rolls anything that fails.*

## Why

Single-tool MCP servers (one model, one call) are common. This is the layer above:
it **orchestrates** across your generation stack with a block-method planner and a
style-drift QC gate — the part nobody ships.

## Tools (13)

**Plan & lock**
| Tool | What it does |
|------|--------------|
| `plan_shots(brief, project, n_shots)` | brief → block-method shot plan (type · move · duration · lighting · lens · time · hold · vibe) |
| `lock_campaign(project, aspect, camera, day_stock, hex_palette, elements, …)` | lock the look once — every shot's prompt inherits it |
| `palette_from_image(image)` | extract a HEX palette (dominant/secondary/accent) from a moodboard/still |
| `reference_prompt(reference, swap_subject)` | break a reference image into a ready 6-layer prompt (build *from* a ref) |

**Render & QC** *(via [Higgsfield CLI](https://higgsfield.ai/cli))*
| Tool | What it does |
|------|--------------|
| `gen_still(project, shot_id, note, model)` | 6-layer Soul prompt → render; `note` re-rolls with a QC fix; per-shot `model` |
| `qc_still(project, image, shot_id, threshold)` | vision **style-drift QC** vs shot intent + lock; pass/fail + fix_suggestion |
| `animate(project, shot_id, still, model, direct, hero)` | img2vid — `direct` = DP persona reads the frame & directs the move; `hero` = full Seedance timecoded/lip-sync prompt |
| `train_character(project, name, photos)` | soul-id self-clone from 3–5 photos |
| `upscale(media, kind, model)` | final-polish image/video upscale |

**Assemble & utility**
| Tool | What it does |
|------|--------------|
| `cut(project)` | ffmpeg-concat the rendered clips into one `<project>_cut.mp4` (offline, free) |
| `assemble(project, clips)` | cut manifest — order, durations, diegetic-audio notes |
| `list_models(kind)` | list available image/video models so an agent can route per shot |
| `project_status(project)` | what stages exist for a project |

## Provider-agnostic

The LLM layer talks to **any OpenAI-compatible endpoint** — Anthropic, OpenRouter,
OpenAI, or a local server — chosen entirely through env config. No provider is
hard-coded.

```bash
cp .env.example .env   # set STUDIO_LLM_BASE_URL / _MODEL / _API_KEY
```

## Install

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Run

```bash
studio-mcp        # stdio MCP server
```

Register with an MCP client (e.g. Claude Code / Claude Desktop):

```json
{
  "mcpServers": {
    "studio": {
      "command": "/path/to/studio-mcp/.venv/bin/studio-mcp",
      "env": { "STUDIO_LLM_API_KEY": "sk-..." }
    }
  }
}
```

## Example flow

```
plan_shots("MARÉA — wordless coastal slow-burn, 90s", project="marea")
lock_campaign("marea", aspect="2.39:1", stock="Kodak 500T, soft handheld",
              hex_palette=["#1b2a3a","#c8a15a"], elements=["the woman in grey"],
              audio="diegetic SFX only, no music")
# render a still (v1.1) → then:
qc_still("marea", image="assets/shot1.png", shot_id=1)   # pass/fail + fix
assemble("marea")                                         # cut manifest
```

State lives under `STUDIO_ROOT` (default `~/studio-projects/<project>/`) as plain
JSON — human-inspectable, and a clean contract a future console can read.

## License

MIT
