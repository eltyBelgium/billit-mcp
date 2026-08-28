/**
 * Multi-tenant Cloudflare Worker entrypoint. Every connecting user logs into
 * their OWN Billit account through Billit's OAuth login — the server never
 * uses a shared API key on anyone's behalf. This is what Billit's terms
 * require once you host the server for people other than yourself
 * (docs/GUIDE.md §4, README "Distribute for others").
 *
 * Deploy separately from the simple single-tenant src/worker.ts:
 *   npm run deploy:oauth   (uses wrangler.oauth.jsonc)
 *
 * Required secrets (wrangler secret put -c wrangler.oauth.jsonc):
 *   BILLIT_OAUTH_CLIENT_ID, BILLIT_OAUTH_CLIENT_SECRET — from Billit support
 *
 * Required bindings (already provisioned, see wrangler.oauth.jsonc):
 *   OAUTH_KV       — grants/clients/tokens for this Worker's own OAuth layer
 *   BILLIT_TOKENS  — per-connection Billit access/refresh token pairs
 */

import OAuthProvider from "@cloudflare/workers-oauth-provider";
import { createMcpHandler } from "agents/mcp";

import {
  billitAuthorizeUrl,
  clearNonceCookie,
  exchangeBillitCode,
  getValidBillitAccessToken,
  readNonceCookie,
  setNonceCookie,
  type TokenKv,
} from "./billit-oauth.js";
import { configFromEnv, type BillitConfig } from "./config.js";
import { buildServer } from "./server.js";

interface Env {
  BILLIT_BASE_URL?: string;
  BILLIT_OAUTH_CLIENT_ID: string;
  BILLIT_OAUTH_CLIENT_SECRET: string;
  OAUTH_KV: TokenKv;
  BILLIT_TOKENS: TokenKv;
  OAUTH_PROVIDER: {
    parseAuthRequest(request: Request): Promise<AuthRequest>;
    completeAuthorization(
      opts: CompleteAuthorizationOptions,
    ): Promise<{ redirectTo: string }>;
  };
}

interface AuthRequest {
  responseType: string;
  clientId: string;
  redirectUri: string;
  scope: string[];
  state: string;
  codeChallenge?: string;
  codeChallengeMethod?: string;
  resource?: string | string[];
}

interface CompleteAuthorizationOptions {
  request: AuthRequest;
  userId: string;
  metadata: Record<string, unknown>;
  scope: string[];
  props: BillitOAuthProps;
}

interface BillitOAuthProps {
  billitTokenId: string;
}

function baseConfig(env: Env): BillitConfig {
  return configFromEnv(env as unknown as Record<string, string | undefined>);
}

function callbackUrl(request: Request): string {
  return new URL("/callback", request.url).toString();
}

async function handleAuthorize(request: Request, env: Env): Promise<Response> {
  const oauthReqInfo = await env.OAUTH_PROVIDER.parseAuthRequest(request);
  const nonce = crypto.randomUUID();
  const state = btoa(JSON.stringify({ nonce, oauthReqInfo }));

  const location = billitAuthorizeUrl(baseConfig(env), {
    client_id: env.BILLIT_OAUTH_CLIENT_ID,
    redirect_uri: callbackUrl(request),
    response_type: "code",
    state,
  });

  const headers = new Headers({ Location: location });
  setNonceCookie(headers, nonce);
  return new Response(null, { status: 302, headers });
}

async function handleCallback(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const stateParam = url.searchParams.get("state");
  if (!code || !stateParam) {
    return new Response("Missing code or state from Billit.", { status: 400 });
  }

  let nonce: string;
  let oauthReqInfo: AuthRequest;
  try {
    const parsed = JSON.parse(atob(stateParam)) as { nonce: string; oauthReqInfo: AuthRequest };
    nonce = parsed.nonce;
    oauthReqInfo = parsed.oauthReqInfo;
  } catch {
    return new Response("Invalid state parameter.", { status: 400 });
  }

  const cookieNonce = readNonceCookie(request);
  if (!cookieNonce || cookieNonce !== nonce) {
    return new Response(
      "Login session mismatch — please restart the connection from your MCP client.",
      { status: 400 },
    );
  }

  const cfg = baseConfig(env);
  let tokens;
  try {
    tokens = await exchangeBillitCode(
      cfg,
      env.BILLIT_OAUTH_CLIENT_ID,
      env.BILLIT_OAUTH_CLIENT_SECRET,
      code,
      callbackUrl(request),
    );
  } catch (err) {
    return new Response(`Billit login failed: ${(err as Error).message}`, { status: 502 });
  }

  const billitTokenId = crypto.randomUUID();
  await env.BILLIT_TOKENS.put(billitTokenId, JSON.stringify(tokens));

  const { redirectTo } = await env.OAUTH_PROVIDER.completeAuthorization({
    request: oauthReqInfo,
    // No stable Billit account identifier is fetched yet (would need an
    // extra Billit API call whose partyID-scoping we haven't confirmed) —
    // each login mints a fresh grant rather than consolidating repeats by
    // the same Billit user.
    userId: billitTokenId,
    metadata: { label: "Billit account" },
    scope: oauthReqInfo.scope,
    props: { billitTokenId },
  });

  const headers = new Headers({ Location: redirectTo });
  clearNonceCookie(headers);
  return new Response(null, { status: 302, headers });
}

const defaultHandler = {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname === "/authorize") return handleAuthorize(request, env);
    if (url.pathname === "/callback") return handleCallback(request, env);
    if (url.pathname === "/" || url.pathname === "/health") {
      return Response.json({
        name: "billit-mcp",
        endpoint: "/mcp",
        transport: "streamable-http",
        mode: "multi-tenant-oauth",
        auth: "Each connection authenticates with its own Billit account via OAuth.",
      });
    }
    return Response.json({ error: "not_found" }, { status: 404 });
  },
};

const mcpApiHandler = {
  async fetch(request: Request, env: Env, rawCtx: unknown): Promise<Response> {
    const ctx = rawCtx as { props: BillitOAuthProps };
    const { billitTokenId } = ctx.props;
    if (!billitTokenId) {
      return Response.json({ error: "unauthorized" }, { status: 401 });
    }

    const cfg = baseConfig(env);
    let bearerToken: string;
    try {
      bearerToken = await getValidBillitAccessToken(
        cfg,
        env.BILLIT_TOKENS,
        billitTokenId,
        env.BILLIT_OAUTH_CLIENT_ID,
        env.BILLIT_OAUTH_CLIENT_SECRET,
      );
    } catch (err) {
      return Response.json(
        { error: "billit_session_expired", detail: (err as Error).message },
        { status: 401 },
      );
    }

    const { server } = buildServer({ ...cfg, authMode: "bearer", bearerToken });
    return createMcpHandler(server, { route: "/mcp" })(
      request as never,
      env as never,
      ctx as never,
    ) as Promise<Response>;
  },
};

export default new OAuthProvider<Env>({
  apiRoute: "/mcp",
  apiHandler: mcpApiHandler,
  defaultHandler,
  authorizeEndpoint: "/authorize",
  tokenEndpoint: "/token",
  clientRegistrationEndpoint: "/register",
});
