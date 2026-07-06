# studio-mcp console

A React / Next.js web console over the studio-mcp Model Context Protocol server.

## Goal

Give the MCP tool platform a browser UI: list the available tools, invoke any tool
with a form built from its input schema, stream live output, and keep a run history.
Turns the CLI/MCP-client-only pipeline into something a non-terminal user can drive.

## Planned surface

- **Tool browser** — read the MCP server's `tools/list`, render each tool with its schema.
- **Invoke panel** — schema-driven form per tool, submit to a Node/Next API route that
  proxies to the MCP server, show result + latency + cost.
- **Run history** — persist past invocations (tool, args, output, timing) for replay.
- **Live output** — stream long-running tool output (gen/animate/assemble) to the UI.

## Stack

- Next.js (App Router) + React + TypeScript
- Tailwind for styling
- Server-side API routes as the MCP proxy (Node)

## Status

🚧 In progress — scaffolding. See `PLAN.md` for the build checklist.
