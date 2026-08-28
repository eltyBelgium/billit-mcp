/**
 * Billit as the upstream OAuth provider for the multi-tenant Worker
 * (src/worker-oauth.ts). Each connecting user logs into *their own* Billit
 * account; the server never uses a shared API key on their behalf.
 *
 * Flow: MCP client -> our /authorize -> Billit login -> our /callback ->
 * exchange code -> store Billit tokens in BILLIT_TOKENS KV -> complete the
 * MCP-level grant with just a reference id in `props` (never the tokens
 * themselves, so they're never baked into a long-lived grant record).
 *
 * Billit issues single-use rotating refresh tokens (docs/GUIDE.md §4), so
 * every refresh must overwrite the KV record before use. Two concurrent
 * requests racing a refresh at the same instant can still both try to spend
 * the same refresh token; see the retry-once fallback in
 * getValidBillitAccessToken. Acceptable at this scale — access tokens last
 * 1h, so the race window is rare — but a real fix would need a Durable
 * Object to serialize refreshes per user, which this stateless design
 * deliberately avoids.
 */

import { oauthBaseUrlFor, type BillitConfig } from "./config.js";

export interface BillitTokenRecord {
  accessToken: string;
  refreshToken: string;
  /** ms since epoch */
  expiresAt: number;
}

interface BillitTokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in?: number;
  token_type?: string;
}

const NONCE_COOKIE = "billit_oauth_nonce";
const REFRESH_SKEW_MS = 60_000;

export function billitAuthorizeUrl(cfg: BillitConfig, params: Record<string, string>): string {
  const url = new URL("/Account/Logon", oauthBaseUrlFor(cfg));
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v);
  return url.toString();
}

function billitTokenUrl(cfg: BillitConfig): string {
  return new URL("/OAuth2/token", oauthBaseUrlFor(cfg)).toString();
}

async function requestBillitToken(
  cfg: BillitConfig,
  clientId: string,
  clientSecret: string,
  body: Record<string, string>,
): Promise<BillitTokenResponse> {
  const res = await fetch(billitTokenUrl(cfg), {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ client_id: clientId, client_secret: clientSecret, ...body }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Billit token endpoint returned ${res.status}: ${detail.slice(0, 500)}`);
  }
  return (await res.json()) as BillitTokenResponse;
}

export async function exchangeBillitCode(
  cfg: BillitConfig,
  clientId: string,
  clientSecret: string,
  code: string,
  redirectUri: string,
): Promise<BillitTokenRecord> {
  const tokens = await requestBillitToken(cfg, clientId, clientSecret, {
    grant_type: "authorization_code",
    code,
    redirect_uri: redirectUri,
  });
  return toRecord(tokens);
}

async function refreshBillitToken(
  cfg: BillitConfig,
  clientId: string,
  clientSecret: string,
  refreshToken: string,
): Promise<BillitTokenRecord> {
  const tokens = await requestBillitToken(cfg, clientId, clientSecret, {
    grant_type: "refresh_token",
    refresh_token: refreshToken,
  });
  return toRecord(tokens);
}

function toRecord(tokens: BillitTokenResponse): BillitTokenRecord {
  return {
    accessToken: tokens.access_token,
    refreshToken: tokens.refresh_token,
    expiresAt: Date.now() + (tokens.expires_in ?? 3600) * 1000,
  };
}

export interface TokenKv {
  get(key: string): Promise<string | null>;
  put(key: string, value: string): Promise<void>;
  delete(key: string): Promise<void>;
}

/**
 * Returns a valid Billit access token for this connection, refreshing (and
 * persisting the rotated refresh token) if it's near expiry. Throws if the
 * stored session is gone or Billit rejects the refresh outright.
 */
export async function getValidBillitAccessToken(
  cfg: BillitConfig,
  kv: TokenKv,
  billitTokenId: string,
  clientId: string,
  clientSecret: string,
): Promise<string> {
  const raw = await kv.get(billitTokenId);
  if (!raw) throw new Error("Billit session not found — reconnect this connector.");
  const record: BillitTokenRecord = JSON.parse(raw);
  if (record.expiresAt - Date.now() > REFRESH_SKEW_MS) return record.accessToken;

  try {
    const refreshed = await refreshBillitToken(cfg, clientId, clientSecret, record.refreshToken);
    await kv.put(billitTokenId, JSON.stringify(refreshed));
    return refreshed.accessToken;
  } catch (err) {
    // Single-use refresh tokens mean a concurrent request may have already
    // rotated this one. Re-read once in case that request already won.
    const retryRaw = await kv.get(billitTokenId);
    if (retryRaw) {
      const retryRecord: BillitTokenRecord = JSON.parse(retryRaw);
      if (retryRecord.refreshToken !== record.refreshToken && retryRecord.expiresAt > Date.now()) {
        return retryRecord.accessToken;
      }
    }
    throw new Error(
      `Billit session expired and could not be refreshed — reconnect this connector. (${(err as Error).message})`,
    );
  }
}

/** Cookie binding the browser that started /authorize to the one completing /callback (login CSRF defense). */
export function setNonceCookie(headers: Headers, nonce: string): void {
  headers.append(
    "Set-Cookie",
    `${NONCE_COOKIE}=${nonce}; HttpOnly; Secure; SameSite=Lax; Max-Age=600; Path=/callback`,
  );
}

export function clearNonceCookie(headers: Headers): void {
  headers.append("Set-Cookie", `${NONCE_COOKIE}=; HttpOnly; Secure; SameSite=Lax; Max-Age=0; Path=/callback`);
}

export function readNonceCookie(request: Request): string | null {
  const cookie = request.headers.get("Cookie") ?? "";
  const match = cookie.match(new RegExp(`(?:^|;\\s*)${NONCE_COOKIE}=([^;]+)`));
  return match ? (match[1] ?? null) : null;
}
