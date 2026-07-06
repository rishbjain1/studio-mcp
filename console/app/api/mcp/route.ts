import { NextRequest, NextResponse } from "next/server";

import { withMcpClient } from "@/lib/mcp-client";

export const dynamic = "force-dynamic";

type Body =
  | { action: "list" }
  | { action: "call"; name: string; args: Record<string, unknown> };

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
