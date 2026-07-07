"use client";

import { useCallback, useRef, useState } from "react";

/*
  The Director panel — brief an LLM, watch it drive the instruments.
  Renders the NDJSON stream from /api/director as a set transcript:
  director notes (text), instrument calls (chips), and results.
*/

type Event =
  | { type: "text"; text: string }
  | { type: "tool_call"; name: string; args: Record<string, unknown> }
  | { type: "tool_result"; name: string; ok: boolean; latencyMs: number; preview: string }
  | { type: "error"; error: string };

type Entry =
  | { kind: "user"; text: string }
  | { kind: "director"; text: string }
  | { kind: "call"; name: string; args: string }
  | { kind: "result"; name: string; ok: boolean; latencyMs: number; preview: string }
  | { kind: "error"; text: string };

export default function Director({
  onToolRun,
}: {
  onToolRun?: (name: string, ok: boolean, latencyMs: number, preview: string) => void;
}) {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [input, setInput] = useState("");
  const [rolling, setRolling] = useState(false);
  const historyRef = useRef<{ role: "user" | "assistant"; content: string }[]>([]);

  const send = useCallback(async () => {
    const brief = input.trim();
    if (!brief || rolling) return;
    setInput("");
    setRolling(true);
    setEntries((prev) => [...prev, { kind: "user", text: brief }]);
    historyRef.current.push({ role: "user", content: brief });

    const assistantChunks: string[] = [];
    try {
      const res = await fetch("/api/director", {
        method: "POST",
        body: JSON.stringify({ messages: historyRef.current }),
      });
      if (!res.body) throw new Error("no stream");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.trim()) continue;
          const event = JSON.parse(line) as Event;
          if (event.type === "text") {
            assistantChunks.push(event.text);
            setEntries((prev) => [...prev, { kind: "director", text: event.text }]);
          } else if (event.type === "tool_call") {
            setEntries((prev) => [
              ...prev,
              { kind: "call", name: event.name, args: JSON.stringify(event.args) },
            ]);
          } else if (event.type === "tool_result") {
            setEntries((prev) => [
              ...prev,
              {
                kind: "result",
                name: event.name,
                ok: event.ok,
                latencyMs: event.latencyMs,
                preview: event.preview,
              },
            ]);
            onToolRun?.(event.name, event.ok, event.latencyMs, event.preview);
          } else if (event.type === "error") {
            setEntries((prev) => [...prev, { kind: "error", text: event.error }]);
          }
        }
      }
    } catch (err) {
      setEntries((prev) => [...prev, { kind: "error", text: String(err) }]);
    } finally {
      if (assistantChunks.length) {
        historyRef.current.push({ role: "assistant", content: assistantChunks.join("\n") });
      }
      setRolling(false);
    }
  }, [input, rolling, onToolRun]);

  return (
    <div className="flex h-full max-w-2xl flex-col">
      <p className="slate-label">Director</p>
      <h2 className="serif mt-1 text-4xl leading-tight text-ink">Brief the director.</h2>
      <p className="mt-3 text-[13px] leading-relaxed text-ink-dim">
        Describe what you want; the director inspects the project and drives the
        instruments. Render calls cost credits — it will ask before rolling film.
      </p>

      <div className="mt-6 min-h-0 flex-1 space-y-3 overflow-y-auto pr-2">
        {entries.map((e, i) => {
          if (e.kind === "user") {
            return (
              <p key={i} className="border-l-2 border-line-2 pl-3 text-[13px] text-ink">
                {e.text}
              </p>
            );
          }
          if (e.kind === "director") {
            return (
              <p key={i} className="whitespace-pre-wrap text-[13px] leading-relaxed text-ink-dim">
                {e.text}
              </p>
            );
          }
          if (e.kind === "call") {
            return (
              <p key={i} className="flex items-baseline gap-2 text-[11px]" title={e.args}>
                <span className="rounded-sm border border-brass-dim/50 bg-brass/10 px-1.5 py-0.5 uppercase tracking-[0.15em] text-brass">
                  {e.name}
                </span>
                <span className="text-ink-faint">rolling…</span>
              </p>
            );
          }
          if (e.kind === "result") {
            return (
              <div key={i} className="text-[11px]">
                <p className="flex items-baseline gap-2">
                  <span className={e.ok ? "text-ok" : "text-bad"}>
                    {e.ok ? "● printed" : "● no good"}
                  </span>
                  <span className="text-ink-faint tabular-nums">
                    {e.name} · {e.latencyMs}ms
                  </span>
                </p>
                <pre className="mt-1 max-h-28 overflow-auto rounded-sm border border-line bg-film-2 p-2 text-[10px] leading-relaxed text-ink-faint">
                  {e.preview}
                </pre>
              </div>
            );
          }
          return (
            <p key={i} className="text-[12px] text-bad">
              {e.text}
            </p>
          );
        })}
        {rolling && (
          <p className="flex items-center gap-2 text-[11px] text-brass">
            <span className="rec-dot inline-block h-2 w-2 rounded-full bg-bad" />
            directing…
          </p>
        )}
      </div>

      <form
        className="mt-4 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
      >
        <input
          className="field flex-1 px-3 py-2.5 text-[13px] text-ink"
          placeholder="e.g. where does the marea project stand? what should we shoot next?"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={rolling}
        />
        <button
          type="submit"
          disabled={rolling || !input.trim()}
          className="rounded-sm border border-brass-dim bg-brass/10 px-4 py-2 text-[11px] uppercase tracking-[0.2em] text-brass transition-colors hover:bg-brass/20 disabled:opacity-40"
        >
          brief
        </button>
      </form>
    </div>
  );
}
