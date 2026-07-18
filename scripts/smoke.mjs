/**
 * CI smoke test: boot the built stdio server with dummy credentials and
 * verify the MCP handshake + tools/list over an in-process transport.
 * Usage: node scripts/smoke.mjs   (after `npm run build`)
 */

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const transport = new StdioClientTransport({
  command: process.execPath,
  args: ["dist/stdio.js"],
  env: {
    ...process.env,
    BILLIT_API_KEY: "smoke-test-dummy",
    BILLIT_PARTY_ID: "1",
  },
});

const client = new Client({ name: "smoke", version: "0" });
await client.connect(transport);

const { tools } = await client.listTools();
if (tools.length < 30) {
  console.error(`FAIL: expected >=30 tools, got ${tools.length}`);
  process.exit(1);
}
console.log(`smoke OK — handshake completed, ${tools.length} tools listed`);
await client.close();
