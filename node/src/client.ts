/**
 * Fetch-based Billit API client. Runs unchanged on Node 20+ and the Cloudflare
 * Workers runtime — both provide `fetch`, `crypto.randomUUID`, `URL`, and
 * `AbortSignal.timeout`.
 */

import type { BillitConfig } from "./config.js";
import { billitErrorFrom } from "./errors.js";

const RETRY_STATUS = new Set([429, 500, 502, 503, 504]);

export interface RequestOptions {
  params?: Record<string, string | number | boolean | undefined | null>;
  body?: unknown;
  partyId?: string;
  idempotentKey?: string;
  extraHeaders?: Record<string, string>;
}

export class BillitClient {
  constructor(private readonly cfg: BillitConfig) {}

  get config(): BillitConfig {
    return this.cfg;
  }

  private authHeaders(partyId?: string): Record<string, string> {
    const h: Record<string, string> = { Accept: "application/json" };
    if (this.cfg.authMode === "bearer" && this.cfg.bearerToken) {
      h["Authorization"] = `Bearer ${this.cfg.bearerToken}`;
    } else if (this.cfg.apiKey) {
      h["apikey"] = this.cfg.apiKey;
    }
    const pid = partyId ?? this.cfg.partyId;
    if (pid) h["partyID"] = pid;
    return h;
  }

  async request(method: string, path: string, opts: RequestOptions = {}): Promise<unknown> {
    const base = path.startsWith("http")
      ? path
      : `${this.cfg.baseUrl}/v1/${path.replace(/^\/+/, "")}`;
    const url = new URL(base);
    if (opts.params) {
      for (const [k, v] of Object.entries(opts.params)) {
        if (v !== undefined && v !== null) url.searchParams.set(k, String(v));
      }
    }

    const headers = this.authHeaders(opts.partyId);
    if (opts.body !== undefined) headers["Content-Type"] = "application/json";
    if (["POST", "PUT", "PATCH"].includes(method.toUpperCase())) {
      headers["Idempotent-Key"] = opts.idempotentKey ?? crypto.randomUUID();
    }
    if (opts.extraHeaders) Object.assign(headers, opts.extraHeaders);

    let attempt = 0;
    // eslint-disable-next-line no-constant-condition
    while (true) {
      attempt++;
      const res = await fetch(url, {
        method,
        headers,
        body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
        signal: AbortSignal.timeout(this.cfg.timeoutMs),
      });

      if (res.ok) return parse(res);

      if (RETRY_STATUS.has(res.status) && attempt <= this.cfg.maxRetries) {
        const backoffMs = Math.min(2 ** (attempt - 1), 8) * 1000;
        await sleep(backoffMs);
        continue;
      }
      throw billitErrorFrom(res.status, await parse(res));
    }
  }

  get(path: string, opts?: RequestOptions) {
    return this.request("GET", path, opts);
  }
  post(path: string, opts?: RequestOptions) {
    return this.request("POST", path, opts);
  }
  patch(path: string, opts?: RequestOptions) {
    return this.request("PATCH", path, opts);
  }
  put(path: string, opts?: RequestOptions) {
    return this.request("PUT", path, opts);
  }
  delete(path: string, opts?: RequestOptions) {
    return this.request("DELETE", path, opts);
  }

  /** Fetch a binary resource (e.g. /v1/files/{uuid}) and return it as base64. */
  async getBinary(
    path: string,
    opts: { partyId?: string } = {},
  ): Promise<{ base64: string; contentType: string | null; bytes: number }> {
    const url = path.startsWith("http")
      ? path
      : `${this.cfg.baseUrl}/v1/${path.replace(/^\/+/, "")}`;
    const res = await fetch(url, {
      method: "GET",
      headers: this.authHeaders(opts.partyId),
      signal: AbortSignal.timeout(this.cfg.timeoutMs),
    });
    if (!res.ok) throw billitErrorFrom(res.status, await parse(res));
    const buf = await res.arrayBuffer();
    return {
      base64: Buffer.from(buf).toString("base64"),
      contentType: res.headers.get("content-type"),
      bytes: buf.byteLength,
    };
  }

  /** Drain a Billit list endpoint, following `NextPageLink`, up to `maxItems`. */
  async collect(
    path: string,
    opts: { params?: RequestOptions["params"]; pageSize?: number; maxItems?: number } = {},
  ): Promise<unknown[]> {
    const pageSize = opts.pageSize ?? 50;
    const maxItems = opts.maxItems ?? 200;
    const out: unknown[] = [];
    let url: string | null = path;
    let first = true;
    while (url && out.length < maxItems) {
      const resp: unknown = await this.get(url, first ? { params: { $top: pageSize, ...opts.params } } : undefined);
      first = false;
      const items = Array.isArray(resp)
        ? resp
        : ((resp as Record<string, unknown>)?.Items as unknown[] | undefined) ?? [];
      for (const item of items) {
        out.push(item);
        if (out.length >= maxItems) break;
      }
      const next = (resp as Record<string, unknown>)?.NextPageLink;
      url = typeof next === "string" && next ? next : null;
    }
    return out;
  }
}

async function parse(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return null;
  const ctype = res.headers.get("content-type") ?? "";
  if (ctype.includes("json")) {
    try {
      return JSON.parse(text);
    } catch {
      return text;
    }
  }
  return text;
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}
