import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

// Server-side only: the browser never talks to the MCP server directly,
// so credentials and the server URL stay off the client.
const SERVER_URL = process.env.STUDIO_MCP_URL ?? "http://127.0.0.1:8321/mcp";

export async function withMcpClient<T>(
  fn: (client: Client) => Promise<T>,
): Promise<T> {
  const client = new Client({ name: "studio-mcp-console", version: "0.0.0" });
  const transport = new StreamableHTTPClientTransport(new URL(SERVER_URL));
  await client.connect(transport);
  try {
    return await fn(client);
  } finally {
    await client.close();
  }
}
