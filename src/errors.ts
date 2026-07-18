/** Billit API error, surfaced to MCP tool callers with a clear message. */
export class BillitError extends Error {
  readonly status: number;
  readonly body: unknown;
  readonly hint?: string;

  constructor(message: string, opts: { status: number; body?: unknown; hint?: string }) {
    super(message);
    this.name = "BillitError";
    this.status = opts.status;
    this.body = opts.body;
    this.hint = opts.hint;
  }

  toDisplay(): string {
    const parts = [`Billit API ${this.status}: ${this.message}`];
    if (this.hint) parts.push(`Hint: ${this.hint}`);
    if (this.body !== undefined && this.body !== null) {
      parts.push(`Body: ${typeof this.body === "string" ? this.body : JSON.stringify(this.body)}`);
    }
    return parts.join(" | ");
  }
}

/** Map an HTTP status + parsed body to a BillitError with a useful hint. */
export function billitErrorFrom(status: number, body: unknown): BillitError {
  const env = (body && typeof body === "object" ? (body as Record<string, unknown>) : {}) as Record<
    string,
    unknown
  >;
  const message =
    (env.ErrorMessage as string) ||
    (env.DefaultText as string) ||
    (env.Message as string) ||
    (typeof body === "string" ? body.slice(0, 500) : `HTTP ${status}`);

  if (status === 401 || status === 403) {
    return new BillitError(message, {
      status,
      body: env,
      hint:
        "Check that apikey + partyID headers are both set, that they match the " +
        "sandbox vs production base URL, and that the user behind the apikey has " +
        "access to this PartyID. See https://docs.billit.be/docs/partyid-and-key",
    });
  }
  return new BillitError(message, { status, body: env });
}
