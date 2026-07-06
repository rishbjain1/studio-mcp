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
    <label className="block text-sm font-medium text-zinc-300">
      {name}
      {required && <span className="text-red-400"> *</span>}
      {s.description && (
        <span className="ml-2 font-normal text-zinc-500">{s.description}</span>
      )}
    </label>
  );

  if (s.enum) {
    return (
      <div className="space-y-1">
        {label}
        <select
          className="w-full rounded border border-zinc-700 bg-zinc-900 px-2 py-1.5 text-sm"
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
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={value === "true"}
          onChange={(e) => onChange(e.target.checked ? "true" : "false")}
        />
        {label}
      </div>
    );
  }

  if (s.type === "object" || s.type === "array") {
    return (
      <div className="space-y-1">
        {label}
        <textarea
          className="h-24 w-full rounded border border-zinc-700 bg-zinc-900 px-2 py-1.5 font-mono text-sm"
          placeholder={s.type === "array" ? "[…] JSON" : "{…} JSON"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {label}
      <input
        className="w-full rounded border border-zinc-700 bg-zinc-900 px-2 py-1.5 text-sm"
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
    <form onSubmit={submit} className="space-y-3">
      {props.length === 0 && (
        <p className="text-sm text-zinc-500">No parameters.</p>
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
      {error && <p className="text-sm text-red-400">{error}</p>}
      <button
        type="submit"
        disabled={running}
        className="rounded bg-indigo-600 px-4 py-1.5 text-sm font-medium hover:bg-indigo-500 disabled:opacity-50"
      >
        {running ? "Running…" : "Invoke"}
      </button>
    </form>
  );
}
