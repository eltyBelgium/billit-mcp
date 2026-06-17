# Billit MCP

A Model Context Protocol server for [Billit](https://www.billit.be/) — the Belgian
e-invoicing platform. Works with **Claude** (Desktop, Code, API), **Gemini** (CLI,
Code Assist), and **ChatGPT** (Desktop Developer Mode, Responses API).

## What you get

- ~28 tools covering Orders (invoices · credit notes · offers), Parties (customers ·
  suppliers), Products, Documents, Files, Reports, Peppol (incl. participant lookup),
  inbound OCR queue, and account info.
- Both **stdio** and **Streamable HTTP** transports from one binary.
- Sandbox by default. Explicit opt-in to production.
- ChatGPT Apps SDK-compatible `search` and `fetch` tools for Deep Research.

## Install

Pick the path that matches your client.

### One-click — Claude Desktop (recommended)

Download `billit-mcp.dxt` from the [latest release](https://github.com/elty/billit-mcp/releases/latest)
and **double-click**. Claude Desktop will install it and prompt you for your Billit
API key and PartyID in a form. Done.

### One command — Claude Code, Gemini CLI, IDEs

```bash
uvx billit-mcp --help
```

Then register it with your client (see [`docs/GUIDE.md`](docs/GUIDE.md) for exact
config snippets).

### Hosted HTTP — ChatGPT, Responses API, remote agents

```bash
docker run --rm -p 8000:8000 \
  -e BILLIT_API_KEY=... -e BILLIT_PARTY_ID=12345 \
  ghcr.io/elty/billit-mcp:latest
```

Expose `https://your-host/mcp` publicly and register it as a custom connector in
ChatGPT (Developer Mode) or pass `server_url` to the OpenAI Responses API.

## Get credentials

- **API key (personal use only):** Log in to
  [my.sandbox.billit.be](https://my.sandbox.billit.be) → My Profile. Copy the
  `ApiKey` and `PartyID`. Repeat on [my.billit.be](https://my.billit.be) for
  production.
- **OAuth (commercial / shared deployments):** Email `support@billit.eu` with your
  PartyID, app name, redirect URI, and environment. You'll receive a `client_id` +
  `client_secret`. See [`docs/GUIDE.md`](docs/GUIDE.md#oauth-mode) for the flow.

> [!IMPORTANT]
> Billit's API-key mode is officially **non-commercial only**. Any MCP server
> distributed to other users (or hosted multi-tenant) must use OAuth.

## Next steps

- [`docs/GUIDE.md`](docs/GUIDE.md) — per-client setup, env vars, troubleshooting.
- [`docs/tools.md`](docs/tools.md) — reference for every tool the server exposes.
- [Billit API docs](https://docs.billit.be/) · [Swagger UI](https://api.billit.be/swagger/ui/index)

## Develop

```bash
git clone https://github.com/elty/billit-mcp
cd billit-mcp
uv sync --extra dev
uv run pytest
uv run billit-mcp --transport stdio   # smoke test
npx -y @modelcontextprotocol/inspector uv run billit-mcp   # interactive
```

## License

MIT — see [`LICENSE`](LICENSE).
