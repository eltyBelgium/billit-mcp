/**
 * Runtime-agnostic configuration. Works from Node `process.env` (stdio) or a
 * Cloudflare Worker `env` object — both are just string maps.
 *
 * Sandbox is the default base URL; opt into production explicitly by setting
 * BILLIT_BASE_URL=https://api.billit.be.
 */

export const SANDBOX_BASE_URL = "https://api.sandbox.billit.be";
export const PRODUCTION_BASE_URL = "https://api.billit.be";

export type AuthMode = "apikey" | "bearer";

export interface BillitConfig {
  apiKey?: string;
  partyId?: string;
  baseUrl: string;
  authMode: AuthMode;
  bearerToken?: string;
  timeoutMs: number;
  maxRetries: number;
}

export type EnvLike = Record<string, string | undefined>;

export function configFromEnv(env: EnvLike): BillitConfig {
  const baseUrl = (env.BILLIT_BASE_URL ?? SANDBOX_BASE_URL).replace(/\/+$/, "");
  const authMode: AuthMode = env.BILLIT_AUTH_MODE === "bearer" ? "bearer" : "apikey";
  return {
    // trim(): pasted secrets often carry a stray trailing newline/space,
    // which Billit rejects as an invalid key.
    apiKey: env.BILLIT_API_KEY?.trim(),
    partyId: env.BILLIT_PARTY_ID?.trim(),
    baseUrl,
    authMode,
    bearerToken: (env.BILLIT_OAUTH_ACCESS_TOKEN ?? env.BILLIT_BEARER_TOKEN)?.trim(),
    timeoutMs: Number(env.BILLIT_TIMEOUT_MS ?? 30000),
    maxRetries: Number(env.BILLIT_MAX_RETRIES ?? 3),
  };
}

export function isProduction(cfg: BillitConfig): boolean {
  return cfg.baseUrl === PRODUCTION_BASE_URL;
}

/** Throws a helpful error if required credentials are missing. */
export function assertConfigured(cfg: BillitConfig): void {
  if (cfg.authMode === "bearer") {
    if (!cfg.bearerToken) {
      throw new Error(
        "BILLIT_AUTH_MODE=bearer requires BILLIT_OAUTH_ACCESS_TOKEN (or BILLIT_BEARER_TOKEN).",
      );
    }
    return;
  }
  if (!cfg.apiKey) {
    throw new Error(
      "BILLIT_API_KEY is required. Get one from https://my.sandbox.billit.be → My Profile.",
    );
  }
  if (!cfg.partyId) {
    throw new Error(
      "BILLIT_PARTY_ID is required — every Billit call needs the partyID header. " +
        "See https://docs.billit.be/docs/partyid-and-key",
    );
  }
}
