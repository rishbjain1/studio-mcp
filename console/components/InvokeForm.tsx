"use client";

import { useMemo, useState } from "react";

import type { JsonSchema, McpTool } from "@/lib/types";

// Resolve `anyOf` (FastMCP emits these for Optional[...] params) to the first
// non-null variant so we can pick a widget.
function resolve(schema: JsonSchema): JsonSchema {
  if (schema.anyOf) {
    const variant = schema.anyOf.find((s) => s.type !== "null");
    if (variant) return { ...variant, description: schema.description ?? variant.description };
  }
  return schema;
}

function Field({
  name,
  schema,
  required,
  value,
  onChange,
}: {
  name: string;
  schema: JsonSchema;
  required: boolean;
  value: string;
  onChange: (v: string) => void;
}) {
  const s = resolve(schema);
  const label = (
    <label className="flex items-baseline gap-2">
      <span className="slate-label text-ink-dim">{name}</span>
      {required && <span className="text-[9px] text-brass">req</span>}
      {s.description && (
        <span className="text-[11px] font-normal normal-case tracking-normal text-ink-faint">
          {s.description}
        </span>
      )}
    </label>
  );

  if (s.enum) {
    return (
      <div className="space-y-1.5">
        {label}
        <select
          className="field w-full px-2.5 py-2 text-[13px] text-ink"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        >
          <option value="">—</option>
          {s.enum.map((opt) => (
            <option key={String(opt)} value={String(opt)}>
              {String(opt)}
            </option>
          ))}
        </select>
      </div>
    );
  }

  if (s.type === "boolean") {
    return (
      <label className="flex cursor-pointer items-center gap-2.5">
        <input
          type="checkbox"
          className="h-3.5 w-3.5 accent-[var(--color-brass)]"
          checked={value === "true"}
          onChange={(e) => onChange(e.target.checked ? "true" : "false")}
        />
        <span className="slate-label text-ink-dim">{name}</span>
        {s.description && (
          <span className="text-[11px] normal-case tracking-normal text-ink-faint">
            {s.description}
          </span>
        )}
      </label>
    );
  }

  if (s.type === "object" || s.type === "array") {
    return (
      <div className="space-y-1.5">
        {label}
        <textarea
          className="field h-24 w-full px-2.5 py-2 text-[12px] text-ink"
          placeholder={s.type === "array" ? "[ … ]" : "{ … }"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      {label}
      <input
        className="field w-full px-2.5 py-2 text-[13px] text-ink"
        type={s.type === "number" || s.type === "integer" ? "number" : "text"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

function coerce(raw: string, schema: JsonSchema): unknown {
  const s = resolve(schema);
  if (raw === "") return undefined;
  if (s.type === "number") return Number(raw);
  if (s.type === "integer") return parseInt(raw, 10);
  if (s.type === "boolean") return raw === "true";
  if (s.type === "object" || s.type === "array") return JSON.parse(raw);
  return raw;
}

export default function InvokeForm({
  tool,
  running,
  onInvoke,
}: {
  tool: McpTool;
  running: boolean;
  onInvoke: (args: Record<string, unknown>) => void;
}) {
  const props = useMemo(
    () => Object.entries(tool.inputSchema.properties ?? {}),
    [tool],
  );
  const required = new Set(tool.inputSchema.required ?? []);
  const [values, setValues] = useState<Record<string, string>>({});
  const [error, setError] = useState<string>();

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(undefined);
    const args: Record<string, unknown> = {};
    try {
      for (const [name, schema] of props) {
        const v = coerce(values[name] ?? "", schema);
        if (v !== undefined) args[name] = v;
      }
    } catch (err) {
      setError(`invalid JSON in a field: ${err instanceof Error ? err.message : err}`);
      return;
    }
    for (const name of required) {
      if (!(name in args)) {
        setError(`missing required field: ${name}`);
        return;
      }
    }
    onInvoke(args);
  };

  return (
    <form onSubmit={submit} className="max-w-xl space-y-4">
      {props.length === 0 && (
        <p className="text-[12px] text-ink-faint">No parameters.</p>
      )}
      {props.map(([name, schema]) => (
        <Field
          key={`${tool.name}:${name}`}
          name={name}
          schema={schema}
          required={required.has(name)}
          value={values[name] ?? ""}
          onChange={(v) => setValues((prev) => ({ ...prev, [name]: v }))}
        />
      ))}
      {error && <p className="text-[12px] text-bad">{error}</p>}
      <button
        type="submit"
        disabled={running}
        className="group mt-1 inline-flex items-center gap-2 rounded-sm border border-brass-dim bg-brass/10 px-5 py-2 text-[11px] uppercase tracking-[0.2em] text-brass transition-colors hover:bg-brass/20 disabled:opacity-40"
      >
        <span className="inline-block h-1.5 w-1.5 rounded-full bg-brass" />
        {running ? "rolling" : "roll take"}
      </button>
    </form>
  );
}
