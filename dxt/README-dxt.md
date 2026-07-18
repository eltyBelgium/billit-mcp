# Billit DXT (Desktop Extension)

Source assets for the one-click `.dxt` installer for **Claude Desktop**.

## How it works

The DXT is a **self-contained Node bundle**. At release time, esbuild compiles
`src/stdio.ts` and its pure-JS dependencies into a single `server/index.js`;
Claude Desktop runs it with its **own bundled Node runtime**, so users install
nothing — no Node, no Python, no uv. Works on macOS, Windows, and Linux from
one file.

When a user double-clicks `billit-mcp.dxt`, Claude Desktop renders the
`user_config` block from `manifest.json` as a form (API key, PartyID, base
URL, and a production safety switch), injects the values as env vars, and
starts the server on stdio.

## Build locally

```bash
npm ci
npm run build:dxt                          # → dxt/bundle/server/index.js
cp dxt/manifest.json dxt/icon.png dxt/bundle/
npx -y @anthropic-ai/dxt pack ./dxt/bundle billit-mcp.dxt
```

CI does the same on every GitHub Release and attaches `billit-mcp.dxt` as an
asset (`.github/workflows/publish-dxt.yml`).

## Updating

Bump `version` in `dxt/manifest.json` in lockstep with `package.json` when
cutting a release — Claude Desktop uses it for update checks.

## Icon

`icon.png` is a 256×256 PNG. Replace with real branding anytime.
