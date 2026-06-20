# studio-mcp

**The block-method film pipeline as agent-callable MCP tools.**

An MCP server that lets an LLM agent drive a full `brief → shots → render → QC → cut`
workflow by calling tools — instead of clicking through generation UIs by hand.
Plan-then-generate, never reverse: every shot is planned (type, move, duration)
before any pixel is made, and every still is QC'd against a locked look so the
piece stays on-model.

## Why

Single-tool MCP servers (one model, one call) are common. This is the layer above:
it **orchestrates** across your generation stack with a block-method planner and a
style-drift QC gate — the part nobody ships.

## Tools (v1)

| Tool | What it does |
|------|--------------|
| `plan_shots(brief, project, n_shots)` | brief → structured shot plan (type · camera move · duration · action) |
| `lock_campaign(project, aspect, stock, hex_palette, elements, audio)` | lock the look so every shot stays on-model |
| `qc_still(project, image, shot_id, threshold)` | vision **style-drift QC** — scores a still vs shot intent + locked look, pass/fail + fix |
| `assemble(project, clips)` | cut manifest — shot order, durations, audio/lip-sync notes |
| `project_status(project)` | what stages exist for a project |

**v1.1 (render phase, via [Higgsfield CLI](https://higgsfield.ai/cli)):**
`train_character` (soul-id self-clone) · `gen_still` (Soul) · `animate` (Seedance/Kling).

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
