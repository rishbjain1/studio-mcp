import Anthropic from "@anthropic-ai/sdk";
import { NextRequest } from "next/server";

import { withMcpClient } from "@/lib/mcp-client";

export const dynamic = "force-dynamic";
export const maxDuration = 300;

/*
  The Director: an LLM that drives the pipeline's instruments.
  POST { messages: [{role: "user"|"assistant", content: string}] }
  → NDJSON stream: {type:"text"|"tool_call"|"tool_result"|"done"|"error", ...}

  Guardrails: bounded tool steps per turn, bounded output tokens per call,
  and a clean error (not a crash) when no API key is configured.
*/

const MODEL = process.env.DIRECTOR_MODEL ?? "claude-sonnet-4-6";
const MAX_STEPS = 8;
const MAX_TOKENS = 1024;

const SYSTEM = `You are the Director of a film pipeline, operating its
instruments (MCP tools) from a grading bay. Block method: plan_shots first,
lock_campaign once, qc_still against the lock, assemble last.
Rules:
- Be terse and concrete, like a director on set. No filler.
- Prefer read-only instruments (project_status, reference_prompt, list_models)
  to inspect state before changing anything.
- gen_still / animate / upscale / train_character spend render credits —
  only call them when the user explicitly asks you to render.
- If a tool errors, read the error and adapt; don't retry blindly.
- End with a one-line summary of what you did and what's next.`;

type ChatMessage = { role: "user" | "assistant"; content: string };

function ndjson(controller: ReadableStreamDefaultController, obj: unknown) {
  controller.enqueue(new TextEncoder().encode(JSON.stringify(obj) + "\n"));
}

export async function POST(req: NextRequest) {
  if (process.env.STUDIO_DEMO === "1") {
    return demoStream();
  }

  const apiKey =
    process.env.STUDIO_LLM_API_KEY ?? process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    return new Response(
      JSON.stringify({
        type: "error",
        error:
          "No API key for the Director. Set ANTHROPIC_API_KEY (or STUDIO_LLM_API_KEY) in the console's environment.",
      }) + "\n",
      { headers: { "Content-Type": "application/x-ndjson" } },
    );
  }

  let body: { messages: ChatMessage[] };
  try {
    body = await req.json();
  } catch {
    return new Response(JSON.stringify({ type: "error", error: "bad body" }) + "\n", {
      status: 400,
      headers: { "Content-Type": "application/x-ndjson" },
    });
  }

  const anthropic = new Anthropic({ apiKey });

  const stream = new ReadableStream({
    async start(controller) {
      try {
        // Instruments → Anthropic tool definitions (schemas pass through).
        const tools = await withMcpClient(async (c) => (await c.listTools()).tools);
        const toolDefs = tools.map((t) => ({
          name: t.name,
          description: (t.description ?? "").slice(0, 1000),
          input_schema: t.inputSchema as Anthropic.Tool.InputSchema,
        }));

        const messages: Anthropic.MessageParam[] = body.messages.map((m) => ({
          role: m.role,
          content: m.content,
        }));

        for (let step = 0; step < MAX_STEPS; step++) {
          const response = await anthropic.messages.create({
            model: MODEL,
            max_tokens: MAX_TOKENS,
            system: SYSTEM,
            tools: toolDefs,
            messages,
          });

          const toolUses = response.content.filter(
            (b): b is Anthropic.ToolUseBlock => b.type === "tool_use",
          );
          for (const block of response.content) {
            if (block.type === "text" && block.text.trim()) {
              ndjson(controller, { type: "text", text: block.text });
            }
          }

          if (response.stop_reason !== "tool_use" || toolUses.length === 0) {
            break;
          }

          messages.push({ role: "assistant", content: response.content });
          const results: Anthropic.ToolResultBlockParam[] = [];
          for (const use of toolUses) {
            ndjson(controller, { type: "tool_call", name: use.name, args: use.input });
            const started = performance.now();
            let text: string;
            let isError = false;
            try {
              const result = await withMcpClient((c) =>
                c.callTool({ name: use.name, arguments: use.input as Record<string, unknown> }),
              );
              const content = (result as { content?: { type: string; text?: string }[] }).content;
              text = (content ?? [])
                .map((c) => (c.type === "text" ? (c.text ?? "") : `[${c.type}]`))
                .join("\n");
              isError = Boolean((result as { isError?: boolean }).isError);
            } catch (err) {
              text = err instanceof Error ? err.message : String(err);
              isError = true;
            }
            const latencyMs = Math.round(performance.now() - started);
            ndjson(controller, {
              type: "tool_result",
              name: use.name,
              ok: !isError,
              latencyMs,
              preview: text.slice(0, 300),
            });
            results.push({
              type: "tool_result",
              tool_use_id: use.id,
              content: text.slice(0, 4000),
              is_error: isError,
            });
          }
          messages.push({ role: "user", content: results });
        }

        ndjson(controller, { type: "done" });
      } catch (err) {
        ndjson(controller, {
          type: "error",
          error: err instanceof Error ? err.message : String(err),
        });
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: { "Content-Type": "application/x-ndjson", "Cache-Control": "no-store" },
  });
}

// Demo mode: a scripted direction session so the deployed demo shows the full
// arc — the director inspects, QCs a shot, and assembles the cut. Mirrors what
// a live run produces; instruments return the MARÉA fixtures.
function demoStream(): Response {
  const script = [
    { type: "text", text: "Let me see where MARÉA stands before deciding what to shoot." },
    { type: "tool_call", name: "project_status", args: { project: "marea" } },
    {
      type: "tool_result",
      name: "project_status",
      ok: true,
      latencyMs: 42,
      preview:
        '{"project": "marea", "has_plan": true, "shots": 3, "has_lock": true, "qc_done": [1,2,3], "has_manifest": true}',
    },
    {
      type: "text",
      text: "All three shots are QC'd. Let me confirm shot 2 held against the locked look.",
    },
    { type: "tool_call", name: "qc_still", args: { project: "marea", shot_id: 2 } },
    {
      type: "tool_result",
      name: "qc_still",
      ok: true,
      latencyMs: 1180,
      preview: '{"scores": {"intent": 89, "look": 92, "character": 86}, "pass": true}',
    },
    {
      type: "text",
      text: "Passed — look 92, on-palette. Everything's clean, so I'll build the cut.",
    },
    { type: "tool_call", name: "assemble", args: { project: "marea" } },
    {
      type: "tool_result",
      name: "assemble",
      ok: true,
      latencyMs: 63,
      preview: '{"title": "MARÉA — dawn swim", "total_duration_s": 10, "timeline": "3 shots"}',
    },
    {
      type: "text",
      text:
        "Cut assembled — MARÉA · dawn swim, 3 shots, 10s, diegetic sound only, " +
        "ready to render finals or hand to the NLE. (Demo mode: instruments " +
        "returned sample data from the MARÉA project.)",
    },
    { type: "done" },
  ];
  const stream = new ReadableStream({
    async start(controller) {
      for (const line of script) {
        ndjson(controller, line);
        await new Promise((r) => setTimeout(r, 350));
      }
      controller.close();
    },
  });
  return new Response(stream, {
    headers: { "Content-Type": "application/x-ndjson" },
  });
}
