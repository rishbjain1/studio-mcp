import { NextRequest, NextResponse } from "next/server";

import { withMcpClient } from "@/lib/mcp-client";

export const dynamic = "force-dynamic";

type Body =
  | { action: "list" }
  | { action: "call"; name: string; args: Record<string, unknown> }
  | { action: "call-stream"; name: string; args: Record<string, unknown> };

// NDJSON stream: {type:"status"} heartbeats while the tool runs (long renders
// block server-side), then one {type:"result"} or {type:"error"} line.
function streamCall(name: string, args: Record<string, unknown>): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      const send = (obj: unknown) =>
        controller.enqueue(encoder.encode(JSON.stringify(obj) + "\n"));
      const started = performance.now();
      const heartbeat = setInterval(
        () =>
          send({
            type: "status",
            state: "running",
            elapsedMs: Math.round(performance.now() - started),
          }),
        1000,
      );
      send({ type: "status", state: "started", tool: name });
      try {
        const result = await withMcpClient((c) =>
          c.callTool({ name, arguments: args ?? {} }),
        );
        send({ type: "result", result, latencyMs: Math.round(performance.now() - started) });
      } catch (err) {
        send({ type: "error", error: err instanceof Error ? err.message : String(err) });
      } finally {
        clearInterval(heartbeat);
        controller.close();
      }
    },
  });
  return new Response(stream, {
    headers: { "Content-Type": "application/x-ndjson", "Cache-Control": "no-store" },
  });
}

export async function POST(req: NextRequest) {
  let body: Body;
  try {
    body = (await req.json()) as Body;
  } catch {
    return NextResponse.json({ ok: false, error: "invalid JSON body" }, { status: 400 });
  }

  try {
    if (body.action === "list") {
      const tools = await withMcpClient(async (c) => (await c.listTools()).tools);
      return NextResponse.json({ ok: true, tools });
    }

    if (body.action === "call-stream") {
      return streamCall(body.name, body.args);
    }

    if (body.action === "call") {
      const { name, args } = body;
      const started = performance.now();
      const result = await withMcpClient((c) =>
        c.callTool({ name, arguments: args ?? {} }),
      );
      const latencyMs = Math.round(performance.now() - started);
      return NextResponse.json({ ok: true, result, latencyMs });
    }

    return NextResponse.json({ ok: false, error: "unknown action" }, { status: 400 });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ ok: false, error: message }, { status: 502 });
  }
}
