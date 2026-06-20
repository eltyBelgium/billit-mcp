"""CLI entrypoint. Picks the transport and runs the FastMCP server."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from . import __version__
from . import settings as settings_mod
from .server import build_server

log = logging.getLogger(__name__)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="billit-mcp",
        description="Billit MCP server — Belgian e-invoicing for MCP-aware clients.",
    )
    p.add_argument("--version", action="version", version=f"billit-mcp {__version__}")
    p.add_argument(
        "--transport",
        choices=("stdio", "http"),
        default=None,
        help="Transport. Defaults to MCP_TRANSPORT env var or 'stdio'.",
    )
    p.add_argument("--host", default=None, help="HTTP bind host (default MCP_HOST or 127.0.0.1).")
    p.add_argument("--port", type=int, default=None, help="HTTP port (default MCP_PORT or 8000).")
    p.add_argument(
        "--allow-production",
        action="store_true",
        help="Required when BILLIT_BASE_URL points at api.billit.be (real invoices).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        cfg = settings_mod.load()
    except Exception as exc:
        print(f"billit-mcp: configuration error\n  {exc}", file=sys.stderr)
        return 2

    if args.transport:
        cfg.transport = args.transport
    if args.host:
        cfg.host = args.host
    if args.port:
        cfg.port = args.port

    if cfg.is_production and not args.allow_production:
        print(
            "billit-mcp: refusing to start against PRODUCTION without --allow-production.\n"
            "  Real invoices would be created. Add the flag if that's what you want.",
            file=sys.stderr,
        )
        return 3

    asyncio.run(_run(cfg))
    return 0


async def _run(cfg: settings_mod.Settings) -> None:
    mcp, client = build_server(cfg)
    try:
        if cfg.transport == "stdio":
            await mcp.run_async(transport="stdio")
        else:
            await mcp.run_async(
                transport="http",
                host=cfg.host,
                port=cfg.port,
            )
    finally:
        await client.aclose()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
