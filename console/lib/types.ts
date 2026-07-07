export type JsonSchema = {
  type?: string;
  title?: string;
  description?: string;
  enum?: (string | number)[];
  default?: unknown;
  properties?: Record<string, JsonSchema>;
  required?: string[];
  items?: JsonSchema;
  anyOf?: JsonSchema[];
};

export type McpTool = {
  name: string;
  description?: string;
  inputSchema: JsonSchema;
};

export type RunRecord = {
  id: string;
  tool: string;
  args: Record<string, unknown>;
  ok: boolean;
  latencyMs?: number;
  costUsd?: number;
  resultPreview: string;
  at: string; // ISO timestamp
};
