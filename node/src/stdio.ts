#!/usr/bin/env node
/**
 * stdio entrypoint — what Claude Desktop / Claude Code / Gemini CLI spawn.
 *
 * stdout is reserved for JSON-RPC frames; ALL logging goes to stderr.
 */

import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

import { assertConfigured, configFromEnv, isProduction } from "./config.js";
import { buildServer } from "./server.js";

async function main(): Promise<void> {
  const cfg = configFromEnv(process.env);

  try {
    assertConfigured(cfg);
  } catch (err) {
    console.error(`billit-mcp: configuration error\n  ${(err as Error).message}`);
    process.exit(2);
  }

  const allowProduction =
    process.argv.includes("--allow-production") ||
    process.env.BILLIT_ALLOW_PRODUCTION === "true";
  if (isProduction(cfg) && !allowProduction) {
    console.error(
      "billit-mcp: refusing to start against PRODUCTION without --allow-production\n" +
        "  (or BILLIT_ALLOW_PRODUCTION=true). Real invoices would be created.",
    );
    process.exit(3);
  }

  const { server } = buildServer(cfg);
  await server.connect(new StdioServerTransport());
  console.error(
    `billit-mcp ${isProduction(cfg) ? "[PRODUCTION]" : "[sandbox]"} running on stdio — ${cfg.baseUrl}`,
  );
}

main().catch((err) => {
  console.error("billit-mcp: fatal:", err);
  process.exit(1);
});
