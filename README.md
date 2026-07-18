# Billit MCP Server

[![CI](https://github.com/eltyBelgium/billit-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/eltyBelgium/billit-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/protocol-MCP-8A2BE2)](https://modelcontextprotocol.io)
[![Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-EA4AAA?logo=githubsponsors)](https://github.com/sponsors/eltyBelgium)

A [Model Context Protocol](https://modelcontextprotocol.io) server for
[Billit](https://www.billit.be/) — the Belgian e-invoicing and Peppol platform.
Let Claude, Gemini, or ChatGPT create and send invoices, manage customers,
look up Peppol participants, and process inbound documents — by asking in
plain language.

```
"Create an invoice for Acme BV: 3 days of consulting at €650/day, due in 30 days.
 Then send it via Peppol."
```

TypeScript, one codebase, two ways to run:

- **Cloudflare Worker** — a remote Streamable-HTTP endpoint at `/mcp` for
  claude.ai, ChatGPT, and the OpenAI/Anthropic APIs. Stateless; deploys in
  one command on the free tier.
- **stdio** — a local process for Claude Desktop, Claude Code, and Gemini CLI.

## ⚡ One-click deploy

[![Deploy to Cloudflare](https://deploy.workers.cloudflare.com/button)](https://deploy.workers.cloudflare.com/?url=https://github.com/eltyBelgium/billit-mcp)

This deploys the Worker to **your** Cloudflare account. After it's live, add
your Billit credentials:

```bash
npx wrangler secret put BILLIT_API_KEY    # from my.sandbox.billit.be → My Profile
npx wrangler secret put BILLIT_PARTY_ID
```

Your MCP endpoint: `https://billit-mcp.<your-subdomain>.workers.dev/mcp` —
`GET /` shows a health/config status.

## Features

- **34 tools** across the full Billit surface:

  | Area | Tools |
  |---|---|
  | Orders | list · get · create invoice / credit note / offer · update · delete · send (email/Peppol/letter/SDI/…) · record payment |
  | Parties | list · get · find by VAT · create/upsert · update |
  | Products | list · get · upsert by SKU |
  | Documents & files | list · get · upload · download (base64) |
  | Peppol | participant lookup (no auth!) · inbox list/accept/refuse · register |
  | Inbound OCR | submit supplier PDF · list queue |
  | Reports & account | list/get reports · account info |
  | ChatGPT compat | `search` + `fetch` with the Apps SDK / Deep Research shape |

- **Sandbox by default** — production requires an explicit opt-in
  (`--allow-production` / `BILLIT_ALLOW_PRODUCTION=true` locally; deliberate
  config on the Worker).
- **Idempotent writes** — every create/send call carries an `Idempotent-Key`,
  so retries never duplicate an invoice.
- **Tool annotations** — reads marked read-only, deletes destructive, so
  clients auto-approve safely and prompt on writes.

## Get Billit credentials

1. Register a **sandbox** account: [my.sandbox.billit.be/Account/Register](https://my.sandbox.billit.be/Account/Register)
   (needs a valid VAT number + email).
2. Log in → **My Profile** → copy your `ApiKey` and `PartyID`.
3. Production credentials come from [my.billit.be](https://my.billit.be) — they
   are **separate** from sandbox. Practice in sandbox first: production calls
   create real invoices.

> [!IMPORTANT]
> Billit's terms allow API-key auth for **personal, non-commercial use only**.
> If you distribute or host this for other users, Billit requires OAuth —
> email `support@billit.eu` for a client ID/secret. See
> [`docs/GUIDE.md`](docs/GUIDE.md).

## Connect your AI client

Full walkthroughs with troubleshooting live in [`docs/GUIDE.md`](docs/GUIDE.md).
The short version:

### claude.ai / Claude Desktop (remote connector)

Settings → **Connectors** → **Add custom connector** →
`https://billit-mcp.<your-subdomain>.workers.dev/mcp`

### Claude Desktop (one-click DXT, local)

Download `billit-mcp.dxt` from the
[latest release](https://github.com/eltyBelgium/billit-mcp/releases/latest) and
double-click — Claude Desktop prompts for your credentials in a form. The
bundle is self-contained: nothing else to install.

### Claude Code

```bash
# Remote (Worker):
claude mcp add --transport http billit https://billit-mcp.<your-subdomain>.workers.dev/mcp

# Or local (stdio), after `npm install && npm run build`:
claude mcp add --transport stdio \
  --env BILLIT_API_KEY=sk_... --env BILLIT_PARTY_ID=12345 \
  billit -- node /path/to/billit-mcp/dist/stdio.js
```

### Gemini CLI

`~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "billit": {
      "httpUrl": "https://billit-mcp.<your-subdomain>.workers.dev/mcp"
    }
  }
}
```

(Or a stdio entry with `command: "node"`, `args: [".../dist/stdio.js"]` and an
`env` block. Server name must not contain underscores.)

### ChatGPT (Developer Mode)

Settings → **Apps & Connectors** → enable **Developer Mode** → add custom
connector with your Worker URL. The server ships the `search`/`fetch` tool
pair ChatGPT expects for Deep Research.

### OpenAI Responses API / Anthropic Messages API

```python
# OpenAI
tools=[{"type": "mcp", "server_label": "billit",
        "server_url": "https://billit-mcp.<sub>.workers.dev/mcp",
        "require_approval": "never"}]

# Anthropic (header: anthropic-beta: mcp-client-2025-11-20)
mcp_servers=[{"type": "url", "name": "billit",
              "url": "https://billit-mcp.<sub>.workers.dev/mcp"}]
```

## Deploying & publishing your own instance

### Manual deploy

```bash
npm install
npx wrangler login
npm run deploy          # → https://billit-mcp.<your-subdomain>.workers.dev
npx wrangler secret put BILLIT_API_KEY
npx wrangler secret put BILLIT_PARTY_ID
```

### Continuous deploy from GitHub

Fork this repo, then add two repository secrets
(Settings → Secrets and variables → Actions):

- `CLOUDFLARE_API_TOKEN` — [create here](https://dash.cloudflare.com/profile/api-tokens)
  with the *Edit Cloudflare Workers* template
- `CLOUDFLARE_ACCOUNT_ID` — shown on your Workers dashboard

Every push to `main` that touches the server now auto-deploys
([workflow](.github/workflows/deploy-worker.yml)). Without the secrets the
workflow skips cleanly, so plain forks stay green.

### Securing a public endpoint

An unauthenticated Worker exposes *your* Billit account to anyone with the
URL. Acceptable for sandbox experiments; **not for production**. Cheapest
gate — a shared bearer token:

```bash
openssl rand -hex 32 | npx wrangler secret put MCP_AUTH_TOKEN
```

Clients must then send `Authorization: Bearer <token>` (supported by Claude
Code `--header`, ChatGPT's API-key connector auth, and both vendor APIs —
but **not** by claude.ai's connector UI, which needs OAuth or an open
endpoint).

## Development

```bash
npm install
npx tsc --noEmit            # typecheck
npm run build && npm run smoke   # build stdio + MCP handshake test
npm run inspect             # MCP Inspector against the stdio server
cp .dev.vars.example .dev.vars && npm run dev   # local Worker at :8787/mcp
```

## Repository layout

```
├── src/
│   ├── config.ts        # env → config, sandbox default, credential checks
│   ├── errors.ts        # BillitError + status→hint mapping
│   ├── client.ts        # fetch client: retries, Idempotent-Key, pagination
│   ├── server.ts        # buildServer(): McpServer + all tool modules
│   ├── stdio.ts         # local entrypoint (Claude/Gemini)
│   ├── worker.ts        # Cloudflare Worker entrypoint (/mcp)
│   └── tools/           # orders · parties · products · documents · peppol
│                        # misc (reports/inbox/account) · searchFetch
├── wrangler.jsonc       # Worker config (stateless — no Durable Objects)
├── dxt/                 # Claude Desktop one-click bundle assets
├── docs/                # GUIDE.md (per-client setup) · tools.md (reference)
├── scripts/smoke.mjs    # CI handshake test
└── .github/workflows/   # CI · Worker deploy · DXT release
```

## Useful links

- [Billit API docs](https://docs.billit.be/) · [Swagger](https://api.billit.be/swagger/ui/index)
- [Model Context Protocol](https://modelcontextprotocol.io)
- [Cloudflare Agents SDK — MCP](https://developers.cloudflare.com/agents/model-context-protocol/)

## Support this project

If this server saves you time, consider
[**sponsoring on GitHub**](https://github.com/sponsors/eltyBelgium) ❤ —
sponsorship funds maintenance, Billit API-change tracking, and new tools.

## License

MIT — see [LICENSE](LICENSE). Not affiliated with Billit NV; "Billit" is a
trademark of its owner. Use at your own risk — always validate in sandbox
before touching production.
