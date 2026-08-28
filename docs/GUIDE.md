# Billit MCP — Setup Guide

This guide walks you through connecting **Billit** to **Claude**, **Gemini**,
and **ChatGPT** via the Model Context Protocol.

> [!NOTE]
> Default base URL is `https://api.sandbox.billit.be`. Real invoices are only
> created if you point at `https://api.billit.be` **and** explicitly allow
> production. Practice in sandbox first.

## Contents

1. [Get your credentials](#1-get-your-credentials)
2. [Run the server](#2-run-the-server)
3. [Wire it up — per client](#3-wire-it-up--per-client)
4. [OAuth mode (multi-tenant / commercial)](#4-oauth-mode-multi-tenant--commercial)
5. [Verify with MCP Inspector](#5-verify-with-mcp-inspector)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Get your credentials

### Personal use → API key

1. Sign up at [my.sandbox.billit.be/Account/Register](https://my.sandbox.billit.be/Account/Register).
2. Log in → **My Profile**. Copy:
   - `ApiKey` (the long secret)
   - `PartyID` (the integer next to your company)
3. Repeat at [my.billit.be](https://my.billit.be) for production credentials
   when you're ready. **Sandbox and production credentials are separate.**

### Distributed / multi-tenant → OAuth

Email `support@billit.eu` with your sandbox PartyID, app name, redirect URI
(not `localhost`), and environment. You'll receive a `client_id` and
`client_secret`. See [OAuth mode](#4-oauth-mode-multi-tenant--commercial).

> [!WARNING]
> Billit's terms say API-key mode is **personal use only**. If you host the
> MCP server for other users — or your team — switch to OAuth.

---

## 2. Run the server

### Option A — Cloudflare Worker (recommended for remote clients)

```bash
npm install
npx wrangler login                       # once, opens browser
npm run deploy                           # → https://billit-mcp.<subdomain>.workers.dev
npx wrangler secret put BILLIT_API_KEY   # paste your key at the prompt
npx wrangler secret put BILLIT_PARTY_ID
```

Check `https://billit-mcp.<subdomain>.workers.dev/` — it returns a JSON
status with `"configured": true` when the secrets are in place. The MCP
endpoint is `/mcp`.

To later target production, edit `wrangler.jsonc` → `vars.BILLIT_BASE_URL`
to `https://api.billit.be`, **secure the endpoint first** (see the README),
and redeploy.

### Option B — Local stdio (Claude Desktop / Claude Code / Gemini CLI)

```bash
npm install && npm run build             # → dist/stdio.js
```

The server reads env vars:

| Variable | Required | Notes |
|---|---|---|
| `BILLIT_API_KEY` | yes | from MyBillit → My Profile |
| `BILLIT_PARTY_ID` | yes | company context for every call |
| `BILLIT_BASE_URL` | no | defaults to sandbox |
| `BILLIT_ALLOW_PRODUCTION` | no | must be `true` to start against production |

### Option C — One-click DXT (Claude Desktop)

Download `billit-mcp.dxt` from the
[latest release](https://github.com/eltyBelgium/billit-mcp/releases/latest),
double-click, and fill in the credentials form. Self-contained — Claude
Desktop runs it with its own Node runtime.

---

## 3. Wire it up — per client

### claude.ai / Claude Desktop — remote connector

Settings → **Connectors** → **Add custom connector** → paste
`https://billit-mcp.<subdomain>.workers.dev/mcp`. Tools appear under the 🔨
icon in any chat.

### Claude Desktop — manual local JSON

Path:

- **macOS** — `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows** — `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "billit": {
      "command": "node",
      "args": ["/ABSOLUTE/PATH/TO/billit-mcp/dist/stdio.js"],
      "env": {
        "BILLIT_API_KEY": "sk_...",
        "BILLIT_PARTY_ID": "12345",
        "BILLIT_BASE_URL": "https://api.sandbox.billit.be"
      }
    }
  }
}
```

Fully quit Claude Desktop (Cmd-Q / exit tray) and reopen.

### Claude Code

```bash
# Remote (Worker)
claude mcp add --transport http billit https://billit-mcp.<subdomain>.workers.dev/mcp

# Remote with bearer gate (if MCP_AUTH_TOKEN is set on the Worker)
claude mcp add --transport http billit https://billit-mcp.<subdomain>.workers.dev/mcp \
  --header "Authorization: Bearer <token>"

# Local stdio
claude mcp add --transport stdio \
  --env BILLIT_API_KEY=sk_... \
  --env BILLIT_PARTY_ID=12345 \
  billit -- node /path/to/billit-mcp/dist/stdio.js
```

Or commit `.mcp.json` at a project root so teammates get it for free:

```json
{
  "mcpServers": {
    "billit": {
      "type": "http",
      "url": "https://billit-mcp.<subdomain>.workers.dev/mcp"
    }
  }
}
```

### Gemini CLI

`~/.gemini/settings.json` (global) or `.gemini/settings.json` per project:

```json
{
  "mcpServers": {
    "billit": {
      "httpUrl": "https://billit-mcp.<subdomain>.workers.dev/mcp",
      "timeout": 30000
    }
  }
}
```

Local stdio variant:

```json
{
  "mcpServers": {
    "billit": {
      "command": "node",
      "args": ["/path/to/billit-mcp/dist/stdio.js"],
      "env": {
        "BILLIT_API_KEY": "$BILLIT_API_KEY",
        "BILLIT_PARTY_ID": "12345"
      }
    }
  }
}
```

> [!IMPORTANT]
> Gemini exposes tools as `mcp_{server}_{tool}` and parses on underscores —
> the server name **cannot contain underscores**. Use `billit`. Note that
> Gemini strips `*KEY*`/`*TOKEN*`-pattern env vars from the inherited
> environment; re-declare them under `env`.

Verify with `gemini mcp list` then `/mcp` inside the CLI. Gemini Code Assist
(VS Code, Standard/Enterprise tier) reads the same settings file.

### ChatGPT (Developer Mode)

1. **Settings → Apps & Connectors → Advanced → enable Developer Mode**
   (Plus/Pro/Business/Enterprise).
2. **Settings → Connectors → Add custom connector** →
   `https://billit-mcp.<subdomain>.workers.dev/mcp`.
3. Pick **No auth** (open endpoint) or **API key** (sends
   `Authorization: Bearer …` — pair with `MCP_AUTH_TOKEN` on the Worker).

ChatGPT requires a **public HTTPS** URL — it cannot spawn local processes.
The `search`/`fetch` tools ChatGPT expects for Deep Research ship built-in.

### OpenAI Responses API

```js
import OpenAI from "openai";

const client = new OpenAI();
const resp = await client.responses.create({
  model: "gpt-5",
  input: "What invoices are unpaid past their due date?",
  tools: [{
    type: "mcp",
    server_label: "billit",
    server_url: "https://billit-mcp.<subdomain>.workers.dev/mcp",
    authorization: "Bearer <MCP_AUTH_TOKEN>",   // only if you set the gate
    require_approval: "never",
  }],
});
console.log(resp.output_text);
```

### Anthropic Messages API (MCP connector)

```js
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();
const resp = await client.messages.create(
  {
    model: "claude-opus-4-8",
    max_tokens: 1024,
    messages: [{ role: "user", content: "Send invoice 4321 via Peppol." }],
    mcp_servers: [{
      type: "url",
      url: "https://billit-mcp.<subdomain>.workers.dev/mcp",
      name: "billit",
    }],
    tools: [{ type: "mcp_toolset", mcp_server_name: "billit",
              default_config: { enabled: true } }],
  },
  { headers: { "anthropic-beta": "mcp-client-2025-11-20" } },
);
```

Available on the Anthropic API and AWS Foundry — not Bedrock or Vertex.

---

## 4. OAuth mode (multi-tenant / commercial)

When the server is shared by multiple users, Billit requires OAuth: each
connecting user logs into *their own* Billit account instead of the server
using one shared API key. There are two ways to run this, depending on the
client.

### A single client you control: manual token

Point one app at a token you obtained yourself. The authorization-code dance
happens outside this server — send the user to:

```
https://my.billit.be/Account/Logon?client_id=<id>&redirect_uri=<cb>&state=<csrf>
```

then exchange the code at `/OAuth2/token` for an access token (1 h TTL) and
a **single-use** refresh token — store the new refresh token on every
refresh. Run the server with:

```bash
BILLIT_AUTH_MODE=bearer BILLIT_OAUTH_ACCESS_TOKEN=<token> node dist/stdio.js
```

Token refresh management is up to your surrounding app.

### Multiple, unknown users (e.g. a public claude.ai connector): `src/worker-oauth.ts`

For a Worker that people self-serve into — like adding it as a custom
connector in claude.ai — the server itself needs to run the OAuth dance per
connection and keep each person's tokens separate. This repo ships that as a
**separate** deploy target from the simple `wrangler.jsonc`/`src/worker.ts`,
so personal single-key deployments are unaffected.

It's built on Cloudflare's [`workers-oauth-provider`](https://github.com/cloudflare/workers-oauth-provider):
the Worker acts as an MCP OAuth authorization server, and its `/authorize`
handler redirects to Billit's own login instead of showing its own
consent screen. Billit's login *is* the consent step. On `/callback` the
code is exchanged and the resulting Billit token pair is stored in a
`BILLIT_TOKENS` KV entry, keyed by a random id that's the *only* thing
placed in the MCP grant's `props` — the tokens themselves are never baked
into a long-lived grant record. Every `/mcp` request resolves that id back
to a live access token, refreshing it first if it's within 60s of expiring
(see `src/billit-oauth.ts` for the refresh-race handling forced by Billit's
single-use refresh tokens).

Setup:

1. **Get credentials from Billit.** Email `support@billit.eu` with your
   sandbox PartyID, app name, environment, and the redirect URI
   `https://billit-mcp.<your-subdomain>.workers.dev/callback` (must match
   the hostname of the Worker you're deploying this to — **not**
   `localhost`). They reply with a `client_id`/`client_secret`.
2. **Provision KV** (once):
   ```bash
   npx wrangler kv namespace create OAUTH_KV        # workers-oauth-provider's own storage
   npx wrangler kv namespace create BILLIT_TOKENS   # per-connection Billit token pairs
   ```
   Copy both ids into the `kv_namespaces` block of `wrangler.oauth.jsonc`.
3. **Set secrets:**
   ```bash
   npx wrangler secret put BILLIT_OAUTH_CLIENT_ID -c wrangler.oauth.jsonc
   npx wrangler secret put BILLIT_OAUTH_CLIENT_SECRET -c wrangler.oauth.jsonc
   ```
4. **Deploy:**
   ```bash
   npm run deploy:oauth
   ```
   This uses the **same Worker name** as `wrangler.jsonc`, so it replaces
   whatever's currently live at that hostname — don't run it until step 3
   is done, or `/authorize` will fail for every user.
5. Add the connector in claude.ai as a normal OAuth connector (no headers):
   Settings → **Connectors** → **Add custom connector** →
   `https://billit-mcp.<your-subdomain>.workers.dev/mcp`.

Known limitation: each Billit login mints a fresh grant rather than being
recognized as "the same person logging in again" — the callback doesn't yet
fetch a stable Billit account identifier to key off of (that needs an extra
`account/accountInformation` call whose partyID-scoping under an OAuth token
isn't confirmed yet). Not a security issue, just means repeat logins from
the same person show up as separate connector grants.

---

## 5. Verify with MCP Inspector

```bash
npm run inspect
```

A browser opens. Try:

- `get_account_info` — confirms auth + base URL.
- `lookup_peppol_participant` with `BE0563846944` — works even without auth.
- `list_orders` with `top=5`.

For the deployed Worker: `curl https://billit-mcp.<subdomain>.workers.dev/`
should report `"configured": true`.

---

## 6. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Hammer 🔨 icon missing in Claude Desktop | JSON syntax error or non-absolute path | Validate the JSON; use an absolute path to `dist/stdio.js` |
| `401 ApiKeyNotValid` | Wrong environment or whitespace in the pasted secret | Sandbox creds ≠ production creds. Re-run `wrangler secret put` and paste carefully |
| ChatGPT: "Unsafe URL" | Pointing it at `localhost` | Deploy the Worker (or tunnel) — ChatGPT needs public HTTPS |
| Gemini doesn't see tools | Underscore in server name, or env vars stripped | Rename to `billit`; re-declare `*KEY*` vars under `env` |
| Worker returns `server_not_configured` | Secrets not set | `npx wrangler secret put BILLIT_API_KEY` / `BILLIT_PARTY_ID` |
| Requests get a 302 to `*.cloudflareaccess.com` | Worker is behind Cloudflare Access | Send `CF-Access-Client-Id`/`CF-Access-Client-Secret` service-token headers, or use the Access-OIDC OAuth route for claude.ai — see the README's "Securing a public endpoint" |
| Server refuses to start locally | Production URL without opt-in | Pass `--allow-production` or `BILLIT_ALLOW_PRODUCTION=true` |
| `delete_order` succeeded but order still listed | Soft delete | It's in `list_deleted_orders` — working as designed |

Logs:

- **Worker** — `npx wrangler tail`
- **Claude Desktop (local stdio)** — `~/Library/Logs/Claude/mcp-server-billit.log`
  (macOS) or `%APPDATA%\Claude\logs\` (Windows)
- **Anywhere** — the server logs to stderr; run `node dist/stdio.js` in a
  terminal to see startup errors directly
