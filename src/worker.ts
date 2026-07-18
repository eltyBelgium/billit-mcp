/**
 * Cloudflare Worker entrypoint — a STATELESS remote MCP server over
 * Streamable HTTP at /mcp, via `createMcpHandler` from the Agents SDK.
 * No Durable Objects, no migrations: `wrangler deploy` and done.
 *
 * Secrets (wrangler secret put): BILLIT_API_KEY, BILLIT_PARTY_ID,
 * and optionally MCP_AUTH_TOKEN to require a bearer token from MCP clients.
 */

import { createMcpHandler } from "agents/mcp";

import { assertConfigured, configFromEnv, isProduction } from "./config.js";
import { buildServer } from "./server.js";

interface Env {
  BILLIT_API_KEY?: string;
  BILLIT_PARTY_ID?: string;
  BILLIT_BASE_URL?: string;
  BILLIT_AUTH_MODE?: string;
  BILLIT_OAUTH_ACCESS_TOKEN?: string;
  MCP_AUTH_TOKEN?: string;
}

function unauthorized(): Response {
  return new Response(JSON.stringify({ error: "unauthorized" }), {
    status: 401,
    headers: {
      "Content-Type": "application/json",
      "WWW-Authenticate": 'Bearer realm="billit-mcp"',
    },
  });
}

export default {
  async fetch(request: Request, env: Env, ctx: unknown): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/" || url.pathname === "/health") {
      const cfg = configFromEnv(env as Record<string, string | undefined>);
      let configured = true;
      try {
        assertConfigured(cfg);
      } catch {
        configured = false;
      }
      return Response.json({
        name: "billit-mcp",
        endpoint: "/mcp",
        transport: "streamable-http",
        environment: isProduction(cfg) ? "PRODUCTION" : "sandbox",
        configured,
        auth_required: Boolean(env.MCP_AUTH_TOKEN),
      });
    }

    if (url.pathname === "/mcp") {
      // Optional shared-secret gate: if MCP_AUTH_TOKEN is set, clients must
      // send `Authorization: Bearer <token>` (ChatGPT's "API key" connector
      // auth, Claude custom-connector headers, etc. all support this).
      if (env.MCP_AUTH_TOKEN) {
        const auth = request.headers.get("Authorization") ?? "";
        if (auth !== `Bearer ${env.MCP_AUTH_TOKEN}`) return unauthorized();
      }

      const cfg = configFromEnv(env as Record<string, string | undefined>);
      try {
        assertConfigured(cfg);
      } catch (err) {
        return Response.json(
          { error: "server_not_configured", detail: (err as Error).message },
          { status: 500 },
        );
      }

      // Stateless: fresh server per request; createMcpHandler speaks
      // Streamable HTTP.
      const { server } = buildServer(cfg);
      return createMcpHandler(server, { route: "/mcp" })(
        request as never,
        env as never,
        ctx as never,
      ) as Promise<Response>;
    }

    return Response.json({ error: "not_found", hint: "MCP endpoint is at /mcp" }, { status: 404 });
  },
};
