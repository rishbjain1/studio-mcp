"use client";

import { useCallback, useEffect, useState } from "react";

import InvokeForm from "@/components/InvokeForm";
import { extractCostUsd, prettify, resultToText } from "@/lib/result";
import type { McpTool, RunRecord } from "@/lib/types";

const HISTORY_KEY = "studio-mcp-console:history";

type RunResult = {
  ok: boolean;
  error?: string;
  latencyMs?: number;
  costUsd?: number;
  text: string;
};

export default function ConsolePage() {
  const [tools, setTools] = useState<McpTool[]>([]);
  const [connectError, setConnectError] = useState<string>();
  const [selected, setSelected] = useState<McpTool>();
  const [running, setRunning] = useState(false);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [result, setResult] = useState<RunResult>();
  const [history, setHistory] = useState<RunRecord[]>([]);

  useEffect(() => {
    fetch("/api/mcp", {
      method: "POST",
      body: JSON.stringify({ action: "list" }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.ok) setTools(data.tools);
        else setConnectError(data.error);
      })
      .catch((err) => setConnectError(String(err)));
    try {
      setHistory(JSON.parse(localStorage.getItem(HISTORY_KEY) ?? "[]"));
    } catch {
      // corrupted history is disposable
    }
  }, []);

  const pushHistory = useCallback((record: RunRecord) => {
    setHistory((prev) => {
      const next = [record, ...prev].slice(0, 50);
      localStorage.setItem(HISTORY_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  const invoke = useCallback(
    async (args: Record<string, unknown>) => {
      if (!selected) return;
      setRunning(true);
      setElapsedMs(0);
      setResult(undefined);
      try {
        // Streaming call: NDJSON status heartbeats while long tools
        // (gen_still / animate / assemble) run, then the final result line.
        const res = await fetch("/api/mcp", {
          method: "POST",
          body: JSON.stringify({ action: "call-stream", name: selected.name, args }),
        });
        if (!res.body) throw new Error("no response stream");
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let final:
          | { ok: boolean; error?: string; latencyMs?: number; result?: unknown }
          | undefined;
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";
          for (const line of lines) {
            if (!line.trim()) continue;
            const event = JSON.parse(line);
            if (event.type === "status" && typeof event.elapsedMs === "number") {
              setElapsedMs(event.elapsedMs);
            } else if (event.type === "result") {
              final = { ok: true, result: event.result, latencyMs: event.latencyMs };
            } else if (event.type === "error") {
              final = { ok: false, error: event.error };
            }
          }
        }
        if (!final) throw new Error("stream ended without a result");
        const text = final.ok
          ? prettify(resultToText(final.result))
          : (final.error ?? "error");
        const costUsd = final.ok ? extractCostUsd(final.result) : undefined;
        setResult({ ok: final.ok, error: final.error, latencyMs: final.latencyMs, costUsd, text });
        pushHistory({
          id: crypto.randomUUID(),
          tool: selected.name,
          args,
          ok: final.ok,
          latencyMs: final.latencyMs,
          costUsd,
          resultPreview: text.slice(0, 400),
          at: new Date().toISOString(),
        });
      } catch (err) {
        setResult({ ok: false, error: String(err), text: String(err) });
      } finally {
        setRunning(false);
      }
    },
    [selected, pushHistory],
  );

  return (
    <main className="flex h-screen">
      {/* Tool browser */}
      <aside className="w-64 shrink-0 overflow-y-auto border-r border-zinc-800 p-3">
        <h1 className="mb-3 text-sm font-semibold tracking-wide text-zinc-400">
          studio-mcp console
        </h1>
        {connectError && (
          <p className="mb-2 rounded bg-red-950 p-2 text-xs text-red-300">
            MCP server unreachable: {connectError}
          </p>
        )}
        <ul className="space-y-1">
          {tools.map((t) => (
            <li key={t.name}>
              <button
                onClick={() => {
                  setSelected(t);
                  setResult(undefined);
                }}
                className={`w-full rounded px-2 py-1.5 text-left text-sm hover:bg-zinc-800 ${
                  selected?.name === t.name ? "bg-zinc-800 text-indigo-300" : ""
                }`}
              >
                {t.name}
              </button>
            </li>
          ))}
        </ul>
      </aside>

      {/* Invoke + result */}
      <section className="flex-1 overflow-y-auto p-6">
        {selected ? (
          <>
            <h2 className="text-lg font-semibold">{selected.name}</h2>
            {selected.description && (
              <p className="mt-1 mb-4 max-w-2xl whitespace-pre-wrap text-sm text-zinc-400">
                {selected.description.split("\n\n")[0]}
              </p>
            )}
            <InvokeForm tool={selected} running={running} onInvoke={invoke} />
            {running && elapsedMs > 0 && (
              <p className="mt-3 text-xs text-zinc-500">
                running… {(elapsedMs / 1000).toFixed(0)}s elapsed
              </p>
            )}
            {result && (
              <div className="mt-6">
                <div className="mb-2 flex items-center gap-4 text-xs text-zinc-400">
                  <span className={result.ok ? "text-emerald-400" : "text-red-400"}>
                    {result.ok ? "OK" : "ERROR"}
                  </span>
                  {result.latencyMs !== undefined && <span>{result.latencyMs} ms</span>}
                  {result.costUsd !== undefined && (
                    <span>${result.costUsd.toFixed(4)} LLM cost</span>
                  )}
                </div>
                <pre className="max-h-[50vh] overflow-auto rounded border border-zinc-800 bg-zinc-900 p-3 text-xs leading-relaxed">
                  {result.text}
                </pre>
              </div>
            )}
          </>
        ) : (
          <p className="text-sm text-zinc-500">
            Pick a tool on the left. Start the server with{" "}
            <code className="rounded bg-zinc-900 px-1">
              studio-mcp --transport streamable-http
            </code>
            .
          </p>
        )}
      </section>

      {/* Run history */}
      <aside className="w-72 shrink-0 overflow-y-auto border-l border-zinc-800 p-3">
        <h3 className="mb-2 text-sm font-semibold text-zinc-400">Run history</h3>
        {history.length === 0 && <p className="text-xs text-zinc-600">No runs yet.</p>}
        <ul className="space-y-2">
          {history.map((h) => (
            <li
              key={h.id}
              className="rounded border border-zinc-800 p-2 text-xs"
              title={JSON.stringify(h.args, null, 2)}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium">{h.tool}</span>
                <span className={h.ok ? "text-emerald-400" : "text-red-400"}>
                  {h.ok ? "ok" : "err"}
                </span>
              </div>
              <div className="mt-1 flex gap-3 text-zinc-500">
                <span>{new Date(h.at).toLocaleTimeString()}</span>
                {h.latencyMs !== undefined && <span>{h.latencyMs} ms</span>}
                {h.costUsd !== undefined && <span>${h.costUsd.toFixed(4)}</span>}
              </div>
            </li>
          ))}
        </ul>
      </aside>
    </main>
  );
}
