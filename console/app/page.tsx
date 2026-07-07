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

  const num = (i: number) => String(i + 1).padStart(2, "0");

  return (
    <main className="relative z-10 flex h-screen flex-col">
      <div className="desk-top h-px w-full shrink-0" />

      {/* Masthead */}
      <header className="flex shrink-0 items-baseline justify-between border-b border-line px-6 py-3">
        <div className="flex items-baseline gap-3">
          <span className="serif text-2xl leading-none text-ink">studio·mcp</span>
          <span className="slate-label">grading bay</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="slate-label">
            {tools.length} instruments{" "}
            <span className="text-brass-dim">·</span>{" "}
            {history.length} takes
          </span>
          <span
            className={`flex items-center gap-1.5 slate-label ${
              connectError ? "text-bad" : "text-ok"
            }`}
          >
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-current" />
            {connectError ? "offline" : "live"}
          </span>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        {/* Instrument rail */}
        <aside className="flex w-64 shrink-0 flex-col overflow-y-auto border-r border-line px-3 py-4">
          <p className="slate-label mb-3 px-1">Instruments</p>
          {connectError && (
            <p className="mb-3 rounded-sm border border-bad/30 bg-bad/10 p-2 text-[11px] leading-relaxed text-bad">
              server unreachable — {connectError}
            </p>
          )}
          <ul>
            {tools.map((t, i) => {
              const active = selected?.name === t.name;
              return (
                <li key={t.name} className="rise" style={{ animationDelay: `${i * 32}ms` }}>
                  <button
                    onClick={() => {
                      setSelected(t);
                      setResult(undefined);
                    }}
                    className={`group flex w-full items-baseline gap-2 border-l-2 py-1.5 pl-3 pr-2 text-left text-[13px] transition-colors ${
                      active
                        ? "border-brass bg-brass/5 text-brass"
                        : "border-transparent text-ink-dim hover:border-line-2 hover:text-ink"
                    }`}
                  >
                    <span className={`text-[10px] tabular-nums ${active ? "text-brass-dim" : "text-ink-faint"}`}>
                      {num(i)}
                    </span>
                    <span>{t.name}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </aside>

        {/* The bay */}
        <section className="min-w-0 flex-1 overflow-y-auto px-8 py-7">
          {selected ? (
            <>
              <p className="slate-label">Instrument · {selected.name}</p>
              <h2 className="serif mt-1 text-4xl leading-tight text-ink">
                {selected.name.replace(/_/g, " ")}
              </h2>
              {selected.description && (
                <p className="mt-3 mb-7 max-w-xl text-[13px] leading-relaxed text-ink-dim">
                  {selected.description.split("\n\n")[0]}
                </p>
              )}
              <InvokeForm tool={selected} running={running} onInvoke={invoke} />

              {running && elapsedMs > 0 && (
                <p className="mt-4 flex items-center gap-2 text-[11px] text-brass">
                  <span className="rec-dot inline-block h-2 w-2 rounded-full bg-bad" />
                  rolling · {(elapsedMs / 1000).toFixed(0)}s
                </p>
              )}

              {result && (
                <div className="mt-8">
                  <div className="mb-2 flex items-center gap-5 slate-label">
                    <span className={result.ok ? "text-ok" : "text-bad"}>
                      {result.ok ? "● printed" : "● no good"}
                    </span>
                    {result.latencyMs !== undefined && (
                      <span className="text-ink-faint">{result.latencyMs}ms</span>
                    )}
                    {result.costUsd !== undefined && (
                      <span className="text-brass-dim">${result.costUsd.toFixed(4)}</span>
                    )}
                  </div>
                  <pre className="max-h-[52vh] overflow-auto rounded-sm border border-line bg-film-2 p-4 text-[12px] leading-relaxed text-ink-dim">
                    {result.text}
                  </pre>
                </div>
              )}
            </>
          ) : (
            <div className="flex h-full max-w-md flex-col justify-center">
              <p className="slate-label mb-3">No instrument loaded</p>
              <p className="serif text-3xl leading-snug text-ink">
                Pick an instrument to compose a take.
              </p>
              <p className="mt-4 text-[13px] leading-relaxed text-ink-dim">
                The bay speaks to the pipeline over{" "}
                <code className="rounded-sm bg-film-2 px-1.5 py-0.5 text-brass">
                  studio-mcp --transport streamable-http
                </code>
                . Every take is timed, priced, and logged to the reel.
              </p>
            </div>
          )}
        </section>

        {/* The reel — run history */}
        <aside className="flex w-72 shrink-0 flex-col overflow-y-auto border-l border-line px-3 py-4">
          <p className="slate-label mb-3 px-1">Takes</p>
          {history.length === 0 && (
            <p className="px-1 text-[11px] text-ink-faint">Reel empty.</p>
          )}
          <ul className="space-y-1.5">
            {history.map((h, i) => (
              <li
                key={h.id}
                className="group rounded-sm border border-line bg-film-2/60 p-2.5 text-[11px] transition-colors hover:border-line-2"
                title={JSON.stringify(h.args, null, 2)}
              >
                <div className="flex items-baseline justify-between">
                  <span className="flex items-baseline gap-1.5 text-ink">
                    <span className="text-ink-faint tabular-nums">
                      T{num(history.length - 1 - i)}
                    </span>
                    {h.tool}
                  </span>
                  <span className={h.ok ? "text-ok" : "text-bad"}>
                    {h.ok ? "●" : "○"}
                  </span>
                </div>
                <div className="mt-1.5 flex gap-3 text-ink-faint tabular-nums">
                  <span>{new Date(h.at).toLocaleTimeString()}</span>
                  {h.latencyMs !== undefined && <span>{h.latencyMs}ms</span>}
                  {h.costUsd !== undefined && (
                    <span className="text-brass-dim">${h.costUsd.toFixed(4)}</span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </main>
  );
}
