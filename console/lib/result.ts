// Helpers to pull display info out of arbitrary MCP tool results.

// studio-mcp tools embed per-LLM-call tracing (cost + latency) in their JSON
// payloads; keys vary per tool, so scan the result for cost-shaped numbers.
export function extractCostUsd(value: unknown): number | undefined {
  let total = 0;
  let found = false;
  const walk = (v: unknown) => {
    if (Array.isArray(v)) return v.forEach(walk);
    if (v && typeof v === "object") {
      for (const [k, val] of Object.entries(v)) {
        if (typeof val === "number" && /(^|_)(cost|usd)(_|$)|cost_usd|usd_cost/i.test(k)) {
          total += val;
          found = true;
        } else {
          walk(val);
        }
      }
    }
  };
  walk(value);
  return found ? total : undefined;
}

export function resultToText(result: unknown): string {
  const r = result as { content?: { type: string; text?: string }[] } | undefined;
  if (r?.content?.length) {
    return r.content
      .map((c) => (c.type === "text" ? (c.text ?? "") : `[${c.type}]`))
      .join("\n");
  }
  return JSON.stringify(result, null, 2);
}

// Tool results are often JSON serialized into a text block — pretty-print when so.
export function prettify(text: string): string {
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    return text;
  }
}
