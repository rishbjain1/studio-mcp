# Console build plan

## Checklist

- [ ] Scaffold Next.js App Router + TypeScript + Tailwind
- [ ] MCP proxy API route (`/api/mcp/[...]`) — connect to studio-mcp server, expose `tools/list` + `tools/call`
- [ ] Tool browser page — fetch tool list, render name + description + schema
- [ ] Schema-driven invoke form (json-schema → form fields)
- [ ] Result panel — output + latency + cost (reuse the per-call tracing already in `studio_mcp/llm.py`)
- [ ] Run history (local persistence first, then optional server store)
- [ ] Live output streaming for long tools (gen_still / animate / assemble)
- [ ] Deploy (Vercel) + link from repo README

## Notes

- The server already emits per-LLM-call cost + latency (see main branch obs commit) — surface those in the result panel.
- Keep the proxy server-side so API keys never reach the browser.
