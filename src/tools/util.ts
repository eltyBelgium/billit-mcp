/** Shared helpers for tool modules. */

import { BillitError } from "../errors.js";

export interface ToolResult {
  [key: string]: unknown;
  content: { type: "text"; text: string }[];
  structuredContent?: Record<string, unknown>;
  isError?: boolean;
}

/** Wrap arbitrary JSON data as a successful MCP text result. */
export function ok(data: unknown): ToolResult {
  const text = data === undefined ? "null" : JSON.stringify(data, null, 2);
  return { content: [{ type: "text", text }] };
}

/** Run a tool body, mapping thrown errors to MCP tool-execution errors. */
export async function run(fn: () => Promise<unknown>): Promise<ToolResult> {
  try {
    return ok(await fn());
  } catch (err) {
    const text =
      err instanceof BillitError
        ? err.toDisplay()
        : err instanceof Error
          ? `${err.name}: ${err.message}`
          : String(err);
    return { isError: true, content: [{ type: "text", text }] };
  }
}

/** Build OData-style query params for Billit list endpoints. */
export function odataParams(opts: {
  top?: number;
  skip?: number;
  filter?: string;
  orderby?: string;
  select?: string;
  fullTextSearch?: string;
}): Record<string, string | number | undefined> {
  return {
    $top: opts.top,
    $skip: opts.skip,
    $filter: opts.filter || undefined,
    $orderby: opts.orderby || undefined,
    $select: opts.select || undefined,
    fullTextSearch: opts.fullTextSearch || undefined,
  };
}

/** Copy of `obj` without undefined/null values — Billit rejects explicit nulls. */
export function dropNone<T extends Record<string, unknown>>(obj: T): Partial<T> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(obj)) {
    if (v !== undefined && v !== null) out[k] = v;
  }
  return out as Partial<T>;
}
