# Billit MCP — Node/TypeScript

TypeScript implementation of the Billit MCP server. Same ~30 tools as the
Python version in the repo root, two ways to run:

- **stdio** — for Claude Desktop, Claude Code, Gemini CLI (local process).
- **Cloudflare Workers** — a remote Streamable-HTTP server at `/mcp`, for
  claude.ai custom connectors, ChatGPT, and the OpenAI/Anthropic APIs.
  Stateless (`createMcpHandler`) — no Durable Objects, deploys in one command.

## Setup

```bash
cd node
npm install
```

## Run locally in Claude (stdio)

Build once, then point your client at the compiled entrypoint:

```bash
npm run build   # emits dist/stdio.js
```

**Claude Desktop** — `~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "billit": {
      "command": "node",
      "args": ["/ABSOLUTE/PATH/TO/billit-mcp/node/dist/stdio.js"],
      "env": {
        "BILLIT_API_KEY": "sk_...",
        "BILLIT_PARTY_ID": "12345",
        "BILLIT_BASE_URL": "https://api.sandbox.billit.be"
      }
    }
  }
}
```

**Claude Code** (from the repo root):

```bash
claude mcp add --transport stdio \
  --env BILLIT_API_KEY=sk_... \
  --env BILLIT_PARTY_ID=12345 \
  billit -- node ./node/dist/stdio.js
```

**Dev loop without building** — `npm run dev:stdio` (runs via tsx), or
`npm run inspect` to open the MCP Inspector against the server.

### Production guard

The server refuses to start against `https://api.billit.be` unless you pass
`--allow-production` or set `BILLIT_ALLOW_PRODUCTION=true`. Sandbox is the
default; real invoices need explicit opt-in.

## Deploy to Cloudflare Workers

Three commands from `node/`:

```bash
npx wrangler login                       # once, opens browser
npx wrangler secret put BILLIT_API_KEY   # paste your key
npx wrangler secret put BILLIT_PARTY_ID  # paste your PartyID
npm run deploy
```

Your MCP endpoint is live at:

```
https://billit-mcp.<your-subdomain>.workers.dev/mcp
```

`GET /` returns a small health/status JSON so you can check configuration.

### Protect the endpoint (recommended)

Anyone who can reach the Worker can use **your** Billit credentials, so gate it:

```bash
openssl rand -hex 32 | npx wrangler secret put MCP_AUTH_TOKEN
```

With `MCP_AUTH_TOKEN` set, clients must send `Authorization: Bearer <token>`:

- **claude.ai / Claude Desktop custom connector**: add the header in the
  connector's advanced settings, or use a client that supports custom headers.
- **ChatGPT Developer Mode**: choose "API key" auth when adding the connector.
- **OpenAI Responses API**: pass `"authorization": "Bearer <token>"` on the
  `mcp` tool entry.
- **Claude Code**: `claude mcp add --transport http billit-remote \
  https://…workers.dev/mcp --header "Authorization: Bearer <token>"`.

### Point it at production

Edit `wrangler.jsonc` → `vars.BILLIT_BASE_URL` to `https://api.billit.be`
and redeploy. The Worker trusts your explicit config (there is no interactive
flag in a deployed service) — flip it only when you mean it.

### Local Worker dev

```bash
cp .dev.vars.example .dev.vars   # fill in sandbox credentials
npm run dev                      # wrangler dev → http://localhost:8787/mcp
```

## Connect the deployed server

- **claude.ai (web/desktop)**: Settings → Connectors → Add custom connector →
  `https://billit-mcp.<subdomain>.workers.dev/mcp`.
- **ChatGPT**: Settings → Apps & Connectors → Developer Mode → Add custom
  connector → same URL.
- **OpenAI Responses API**:

  ```python
  tools=[{
      "type": "mcp",
      "server_label": "billit",
      "server_url": "https://billit-mcp.<subdomain>.workers.dev/mcp",
      "authorization": "Bearer <MCP_AUTH_TOKEN>",
      "require_approval": "never",
  }]
  ```

- **Anthropic Messages API** (`anthropic-beta: mcp-client-2025-11-20`):

  ```python
  mcp_servers=[{
      "type": "url",
      "url": "https://billit-mcp.<subdomain>.workers.dev/mcp",
      "name": "billit",
      "authorization_token": "<MCP_AUTH_TOKEN>",
  }]
  ```

## Layout

```
node/
├── src/
│   ├── config.ts        # env → config, sandbox default, credential checks
│   ├── errors.ts        # BillitError + status→hint mapping
│   ├── client.ts        # fetch client: retries, Idempotent-Key, pagination
│   ├── server.ts        # buildServer(): McpServer + all tool modules
│   ├── stdio.ts         # local entrypoint (Claude/Gemini)
│   ├── worker.ts        # Cloudflare Worker entrypoint (/mcp)
│   └── tools/           # orders, parties, products, documents, peppol,
│                        # misc (reports/inbox/account), searchFetch, util
├── wrangler.jsonc       # Worker config (stateless — no Durable Objects)
└── package.json
```

## Caveats

- The multi-tenant story is one-credential-per-deployment: the Worker uses the
  Billit key you set as a secret. For per-user Billit accounts you'd add an
  OAuth layer (see `docs/GUIDE.md` in the repo root).
- `BILLIT_AUTH_MODE=bearer` + `BILLIT_OAUTH_ACCESS_TOKEN` lets the server use
  a Billit OAuth access token instead of an API key, but token refresh is up
  to you (Billit tokens expire hourly).
