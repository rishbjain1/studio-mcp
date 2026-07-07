# studio-mcp console

A React / Next.js web console over the studio-mcp Model Context Protocol server.
Turns the CLI/MCP-client-only pipeline into something a non-terminal user can drive.

**Live demo:** https://console-pied-eight.vercel.app (demo mode — fixtures, no
server behind it). Run it against a real server locally for live tool calls.

## Features

- **The Director** — brief an LLM in plain language and it drives the
  instruments for you: inspects project state, picks tools, calls them over an
  agentic loop, and asks before spending render credits.

- **Tool browser** — reads the server's `tools/list`, renders all 14 tools.
- **Invoke panel** — schema-driven form per tool (enum/boolean/number/JSON widgets,
  required-field checks), submitted through a server-side proxy.
- **Result panel** — output plus wall latency and per-call LLM cost pulled from the
  server's tracing payloads.
- **Live streaming** — long tools (`gen_still` / `animate` / `assemble`) stream
  NDJSON status heartbeats so the UI shows elapsed time while the render blocks.
- **Run history** — last 50 invocations persisted to localStorage, survives reload.
- **Demo mode** — `STUDIO_DEMO=1` serves captured fixtures with no MCP server
  behind it (for Vercel-style deployments).

## Run it

```bash
# 1. the MCP server, over HTTP (repo root)
studio-mcp --transport streamable-http          # 127.0.0.1:8321

# 2. the console
cd console
npm install
npm run dev                                     # http://localhost:3000
```

`STUDIO_MCP_URL` overrides the server URL (default `http://127.0.0.1:8321/mcp`).

## Architecture

- Next.js 15 App Router + React 19 + TypeScript + Tailwind v4.
- `app/api/mcp/route.ts` — the only path that touches the MCP server
  (TypeScript MCP SDK over streamable HTTP), so keys and the server stay
  off the browser. Actions: `list`, `call`, `call-stream` (NDJSON).
- `components/InvokeForm.tsx` — JSON Schema → form fields, including FastMCP's
  `anyOf` optionals.

See `PLAN.md` for the build checklist and what's still open.
