# Billit MCP — Setup Guide

This guide walks you through connecting **Billit** to **Claude**, **Gemini**,
and **ChatGPT** via the Model Context Protocol.

> [!NOTE]
> Default base URL is `https://api.sandbox.billit.be`. Real invoices are only
> created if you set `BILLIT_BASE_URL=https://api.billit.be` **and** pass
> `--allow-production` on the CLI. Practice in sandbox first.

## Contents

1. [Get your credentials](#1-get-your-credentials)
2. [Install the server](#2-install-the-server)
3. [Wire it up — per client](#3-wire-it-up--per-client)
   - [Claude Desktop (DXT one-click)](#claude-desktop-one-click-dxt)
   - [Claude Desktop (manual JSON)](#claude-desktop-manual-json)
   - [Claude Code](#claude-code)
   - [Gemini CLI](#gemini-cli)
   - [Gemini Code Assist (VS Code)](#gemini-code-assist-vs-code)
   - [ChatGPT Desktop (Developer Mode)](#chatgpt-desktop-developer-mode)
   - [OpenAI Responses API](#openai-responses-api)
   - [Anthropic Messages API (MCP connector)](#anthropic-messages-api-mcp-connector)
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
3. Repeat at [my.billit.be](https://my.billit.be) to get production credentials
   when you're ready.

### Distributed / multi-tenant → OAuth

Email `support@billit.eu` with:

- Your sandbox PartyID
- App name
- Redirect URI (must not be `localhost`)
- Environment (sandbox first; production after approval)

You'll receive a `client_id` and `client_secret`. See
[OAuth mode](#4-oauth-mode-multi-tenant--commercial).

> [!WARNING]
> Billit's terms say API-key mode is **personal use only**. If you host the
> MCP server for other users — or your team — switch to OAuth.

---

## 2. Install the server

### One-click — Claude Desktop only

Download `billit-mcp.dxt` from [Releases](https://github.com/eltyBelgium/billit-mcp/releases/latest)
and double-click. Skip to [Claude Desktop (DXT)](#claude-desktop-one-click-dxt).

### One command — everything else

> [!NOTE]
> The PyPI package `billit-mcp-server` is not published yet. Until it is, install
> from source (`git clone` + `uv run`, see [Develop in the README](../README.md#develop))
> or use the `.dxt`. Do **not** `uvx billit-mcp` — that bare name is an unrelated
> project on PyPI.

```bash
uvx billit-mcp-server --help   # downloads & runs without polluting your global Python
# or, persistent install:
pipx install billit-mcp-server
```

### Docker — for hosted HTTP

```bash
docker pull ghcr.io/eltybelgium/billit-mcp:latest
docker run --rm -p 8000:8000 \
  -e BILLIT_API_KEY=... -e BILLIT_PARTY_ID=12345 \
  ghcr.io/eltybelgium/billit-mcp:latest
# → http://localhost:8000/mcp (Streamable HTTP)
```

---

## 3. Wire it up — per client

### Claude Desktop (one-click DXT)

**Prerequisite:** [`uv`](https://docs.astral.sh/uv/) must be installed — the DXT
launches the server with `uvx`. Install it with
`curl -LsSf https://astral.sh/uv/install.sh | sh` (macOS/Linux) or
`powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
(Windows).

1. Download `billit-mcp.dxt`.
2. Double-click → Claude Desktop pops a form.
3. Paste **API key** and **PartyID**. Leave **base URL** at sandbox.
4. Click Install.

The DXT is a thin, cross-platform launcher (it runs
`uvx --from git+https://github.com/eltyBelgium/billit-mcp@v0.1.0 billit-mcp-server`),
so the same file works on macOS, Windows, and Linux.

The Billit tools appear under the 🔨 icon in any chat. To toggle to production
later, open **Settings → Connectors → Billit** and edit the form.

### Claude Desktop (manual JSON)

Path:

- **macOS** — `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows** — `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "billit": {
      "command": "uvx",
      "args": ["billit-mcp-server"],
      "env": {
        "BILLIT_API_KEY": "sk_...",
        "BILLIT_PARTY_ID": "12345",
        "BILLIT_BASE_URL": "https://api.sandbox.billit.be"
      }
    }
  }
}
```

Fully quit Claude Desktop (Cmd-Q on macOS, exit tray on Windows) and reopen.

### Claude Code

Project-scoped (commit `.mcp.json` at the repo root):

```bash
claude mcp add --transport stdio \
  --env BILLIT_API_KEY=sk_... \
  --env BILLIT_PARTY_ID=12345 \
  --env BILLIT_BASE_URL=https://api.sandbox.billit.be \
  billit -- uvx billit-mcp-server
```

Or check `.mcp.json` into git so teammates get it for free:

```json
{
  "mcpServers": {
    "billit": {
      "type": "stdio",
      "command": "uvx",
      "args": ["billit-mcp-server"],
      "env": {
        "BILLIT_API_KEY": "${BILLIT_API_KEY}",
        "BILLIT_PARTY_ID": "${BILLIT_PARTY_ID:-12345}",
        "BILLIT_BASE_URL": "${BILLIT_BASE_URL:-https://api.sandbox.billit.be}"
      }
    }
  }
}
```

### Gemini CLI

Path: `~/.gemini/settings.json` (global) or `.gemini/settings.json` in a project.

```json
{
  "mcpServers": {
    "billit": {
      "command": "uvx",
      "args": ["billit-mcp-server"],
      "env": {
        "BILLIT_API_KEY": "$BILLIT_API_KEY",
        "BILLIT_PARTY_ID": "12345",
        "BILLIT_BASE_URL": "https://api.sandbox.billit.be"
      },
      "timeout": 30000,
      "trust": false
    }
  }
}
```

> [!IMPORTANT]
> Server name **cannot contain underscores** — Gemini parses tools as
> `mcp_{server}_{tool}`. Use `billit`, not `billit_mcp`.

Verify with `gemini mcp list` then `/mcp` inside the CLI.

### Gemini Code Assist (VS Code)

Gemini Code Assist reads the same `~/.gemini/settings.json` as the CLI in
agent mode. Requires Standard or Enterprise tier (free tier dropped MCP
support in June 2026).

### ChatGPT Desktop (Developer Mode)

ChatGPT only consumes MCP over **public HTTPS** — it can't spawn a local
process. Two paths:

#### Local dev with a tunnel

```bash
# Terminal 1 — start the server in HTTP mode
BILLIT_API_KEY=... BILLIT_PARTY_ID=12345 \
  uvx billit-mcp-server --transport http --port 8000

# Terminal 2 — expose it publicly
cloudflared tunnel --url http://localhost:8000
# → https://random-words.trycloudflare.com
```

#### Production hosting

```bash
docker run -d --restart unless-stopped -p 8000:8000 \
  -e BILLIT_API_KEY=... -e BILLIT_PARTY_ID=12345 \
  --name billit-mcp ghcr.io/eltybelgium/billit-mcp:latest
# Front with a TLS-terminating reverse proxy (Caddy / nginx / Traefik).
```

Then in ChatGPT:

1. **Settings → Apps & Connectors → Advanced → enable Developer Mode**.
   (Plus, Pro, Business, or Enterprise tier required.)
2. **Settings → Connectors → Add custom connector**.
3. URL: `https://your-host/mcp`. Pick **OAuth** or **API key** as the auth
   mode you implemented.
4. Complete the auth flow. Tools appear in any chat.

> [!NOTE]
> For full Deep Research compatibility, ChatGPT looks for the `search` and
> `fetch` tools — this server ships both out of the box.

### OpenAI Responses API

```python
from openai import OpenAI

client = OpenAI()
resp = client.responses.create(
    model="gpt-5",
    input="What invoices are unpaid past their due date?",
    tools=[{
        "type": "mcp",
        "server_label": "billit",
        "server_url": "https://your-host/mcp",
        "authorization": f"Bearer {billit_oauth_token}",  # or omit for apikey mode
        "require_approval": "never",
        "allowed_tools": ["list_orders", "get_order"],
    }],
)
print(resp.output_text)
```

The Responses API runs the MCP client from OpenAI's edge — your server must be
on public HTTPS. Headers (including `authorization`) are stripped from logs but
must be re-sent on every call.

### Anthropic Messages API (MCP connector)

```python
import anthropic

client = anthropic.Anthropic()
resp = client.messages.create(
    model="claude-opus-4-8",
    max_tokens=1024,
    extra_headers={"anthropic-beta": "mcp-client-2025-11-20"},
    messages=[{"role": "user", "content": "Send invoice 4321 via Peppol."}],
    extra_body={
        "mcp_servers": [{
            "type": "url",
            "url": "https://your-host/mcp",
            "name": "billit",
            "authorization_token": billit_oauth_token,
        }],
        "tools": [{
            "type": "mcp_toolset",
            "mcp_server_name": "billit",
            "default_config": {"enabled": True},
        }],
    },
)
```

Available on the Anthropic API and AWS Foundry. **Not** on Bedrock or Vertex.

---

## 4. OAuth mode (multi-tenant / commercial)

When the MCP server is shared by multiple users — hosted on the public
internet, or used inside an organization — switch from `apikey` to `oauth`:

```bash
export BILLIT_AUTH_MODE=oauth
export BILLIT_OAUTH_CLIENT_ID=...
export BILLIT_OAUTH_CLIENT_SECRET=...
export BILLIT_OAUTH_REFRESH_TOKEN=...
```

The authorization-code dance happens **outside** this MCP server — your app
shepherds the user to:

```
https://my.billit.be/Account/Logon
  ?client_id=<id>
  &redirect_uri=<your-callback>
  &state=<csrf>
```

Then POSTs the returned code to `/OAuth2/token` to receive an access token
(1 h TTL) plus a refresh token. **Refresh tokens are single-use** — store the
new one each time. This MCP rotates them automatically and logs the new value
at INFO level; persist it in your secret store.

---

## 5. Verify with MCP Inspector

```bash
npx -y @modelcontextprotocol/inspector \
  uvx billit-mcp-server
```

A browser opens at <http://localhost:6274>. Try:

- `get_account_info` — confirms auth + base URL.
- `lookup_peppol_participant` with `BE0563846944` — works even without auth.
- `list_orders` with `top=5`.

If those return data you're good to wire into a client.

---

## 6. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Hammer 🔨 icon missing in Claude Desktop | JSON syntax error or non-absolute path | Validate the JSON; use absolute paths for `command` if `uvx` isn't on PATH |
| `spawn ENOENT` on Windows | npm/uvx not on PATH | Install `uv` globally; restart Claude Desktop after install |
| `401 Auth failed` from any tool | `apikey` + `partyID` mismatch with `BILLIT_BASE_URL` | Sandbox creds ≠ production creds. Double-check which environment you're hitting |
| ChatGPT: "Unsafe URL" | You pointed it at `localhost` | Tunnel via Cloudflare/ngrok or host on public HTTPS |
| Gemini doesn't see tools | Underscore in server name, or `*KEY*`-pattern env vars stripped | Rename `billit_mcp` → `billit`. Re-declare API key under `env` in settings.json |
| `400 Bad Request` from Claude Code on tool registration | Top-level `oneOf`/`anyOf` in input schema | This server avoids those by design; report the tool if you see it |
| `delete_order` returns success but order still listed | Soft delete — still visible via `list_deleted_orders` | Working as designed |
| Production refused to start | Safety: production needs `--allow-production` | Pass the CLI flag explicitly when you're sure |
| OAuth refresh fails after rotation | Refresh token already used | Persist the new refresh token logged at INFO each refresh |

For anything else, check the server logs:

- **Claude Desktop** — `~/Library/Logs/Claude/mcp-server-billit.log` (macOS)
  or `%APPDATA%\Claude\logs\mcp-server-billit.log` (Windows).
- **Claude Code** — run with `--debug` to see MCP frames inline.
- **Direct** — set `LOG_LEVEL=DEBUG` and run the server in a terminal.
