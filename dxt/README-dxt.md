# Billit DXT (Desktop Extension)

This directory contains the manifest and assets for building a one-click
`.dxt` installer for **Claude Desktop**.

## What this is

A DXT file is a zip containing:

- `manifest.json` — declares the server, env vars to prompt the user for, and
  compatibility constraints.
- `icon.png` — 256×256 icon shown in Claude Desktop's connector list.
- The Python source tree (`src/billit_mcp/`).
- A bundled `server/lib/` with all Python deps installed (so users don't need
  to have FastMCP or httpx on their machine).

When a user double-clicks `billit-mcp.dxt`, Claude Desktop:

1. Validates the manifest.
2. Renders the `user_config` block as a form — the user pastes their API key,
   PartyID, and optionally toggles to production.
3. Installs the server and starts it on stdio.

No JSON-editing, no terminal.

## Build

You need [Node 20+](https://nodejs.org) for the DXT CLI.

```bash
# From the repo root
npx -y @anthropic-ai/dxt pack ./dxt billit-mcp.dxt
```

The CLI:

- Reads `dxt/manifest.json`.
- Pip-installs `pyproject.toml` deps into `dxt/server/lib/` (a vendored env).
- Zips everything into `billit-mcp.dxt`.

Attach `billit-mcp.dxt` to your GitHub Release for users to download.

## Update

Bump `version` in `dxt/manifest.json` and `pyproject.toml` in lockstep, then
re-run `dxt pack`. Claude Desktop checks the version field for updates.

## Icon

Replace `icon.png` with a 256×256 PNG. Transparent background renders well in
both light and dark themes.

## Why DXT is Claude-only

Gemini CLI and ChatGPT do not consume the DXT format. They install from PyPI
(`uvx billit-mcp`) or HTTP (`docker run …`). One source tree, three artefacts.
