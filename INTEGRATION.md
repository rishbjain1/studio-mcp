# The studio trio — how the three pieces interlock

The AI film pipeline is one system in three layers: a **method**, the **tools** that
execute it, and a **knowledge base** that grounds it.

```
            ai-content-pipeline skill            (METHOD — how to think the pipeline)
                      │  invokes
                      ▼
                 studio-mcp                       (TOOLS — 14 MCP tools that execute it)
              plan_shots · lock_campaign
              gen_still · qc_still · animate
              cut · assemble · …
                      │  craft_lookup() HTTP POST /query
                      ▼
                 creative-rag                      (KNOWLEDGE — cited, verified craft KB)
        hybrid retrieval → rerank → grounded gen → citation-verify
```

## The three layers

| Layer | Repo / path | Role |
|---|---|---|
| **ai-content-pipeline skill** | `~/.claude/skills/ai-content-pipeline/` | The *method*. Block-method plan → lock → stills → animate → cut. Maps each stage to the studio-mcp tool that runs it, and calls `craft_lookup` to ground prompt choices. |
| **studio-mcp** | this repo · `github.com/rishbjain1/studio-mcp` | The *tools*. 14 MCP tools an agent calls to execute the method. |
| **creative-rag** | `~/creative-rag/` · `github.com/rishbjain1/creative-rag` | The *knowledge*. Answers craft questions with citations + a verification verdict over the real corpus. |

## The wires

1. **skill → studio-mcp** — the skill's `EXECUTION MODES` section maps every pipeline
   stage to its `mcp__studio-mcp__*` tool. The skill guides; the tools execute.
2. **studio-mcp → creative-rag** — `craft_lookup(question, top_k)` (`studio_mcp/server.py`)
   HTTP-POSTs `creative-rag /query` at `CRAG_URL` (default `http://127.0.0.1:8000`,
   optional `CRAG_API_KEY`). Returns `{answer, sources, verification}`.
3. **skill → creative-rag (via the tool)** — the skill's grounding rule says: before
   writing prompts or locking a stock/lens, call `craft_lookup` so choices trace to the
   documented library, not generic model averages.

## Prerequisites

- studio-mcp registered as an MCP server (user scope) → its 14 tools appear as
  `mcp__studio-mcp__*` in a Claude session.
- creative-rag running on `:8000` for `craft_lookup`:
  `cd ~/creative-rag && .venv/bin/python -m uvicorn creative_rag.api:app --port 8000`
- Higgsfield auth for render/animate/upscale; `STUDIO_LLM_API_KEY` for LLM-backed tools.

## Verify the chain

```bash
python scripts/smoke_chain.py     # skill method → craft_lookup → creative-rag → CHAIN OK
```

Asserts a grounded, cited, `supported: true` answer comes back through the full path.
