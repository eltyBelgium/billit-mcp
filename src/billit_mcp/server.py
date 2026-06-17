"""FastMCP server bootstrap. Imports tool modules and wires them up."""

from __future__ import annotations

import logging
import sys

from fastmcp import FastMCP

from . import settings as settings_mod
from .client import BillitClient
from .tools import (
    account,
    documents,
    files,
    inbox,
    orders,
    parties,
    peppol,
    products,
    reports,
    search_fetch,
)

log = logging.getLogger(__name__)

INSTRUCTIONS = """\
Billit MCP — manage Belgian e-invoices (Orders), customers/suppliers (Parties),
products, documents, Peppol participants, and inbound OCR.

Key concepts:
- Every API call is scoped to a Billit company via PartyID; the server's
  PartyID is configured at startup but can be overridden per call.
- Orders is one resource for invoices, credit notes and offers — discriminate
  by `order_type` ("Invoice" | "CreditNote" | "Offer") and `order_direction`
  ("Income" for sales / "Cost" for purchase).
- Credit notes link to the original invoice via `about_invoice_number`.
- Sending (email/Peppol/letter) is a separate step from creating: use
  `send_orders` with the correct `transport_type` after `create_invoice`.
- Idempotency: all create/send tools accept an `idempotent_key`; if omitted
  the server generates a UUID per call.

Safety: the default base URL is sandbox. Tools clearly note when running
against production. Destructive tools (`delete_order`, `send_orders`) should
prompt for confirmation in your client.
"""


def build_server(settings: settings_mod.Settings | None = None) -> tuple[FastMCP, BillitClient]:
    """Construct a FastMCP server with all tools registered.

    Returns ``(mcp, client)``. The client owns the underlying ``httpx`` pool;
    caller is responsible for ``await client.aclose()`` on shutdown.
    """
    cfg = settings or settings_mod.load()
    _configure_logging(cfg)

    if cfg.is_production:
        log.warning(
            "Billit MCP is targeting PRODUCTION (%s). Real invoices will be created.",
            cfg.base_url,
        )
    else:
        log.info("Billit MCP is targeting sandbox (%s)", cfg.base_url)

    client = BillitClient(cfg)
    mcp = FastMCP(name="billit", instructions=INSTRUCTIONS)

    # Register each tool module. Order doesn't matter; module names follow the
    # Billit resource taxonomy.
    for module in (
        orders,
        parties,
        products,
        documents,
        files,
        reports,
        peppol,
        inbox,
        account,
        search_fetch,
    ):
        module.register(mcp, client)

    return mcp, client


def _configure_logging(cfg: settings_mod.Settings) -> None:
    # stdio transport reserves stdout for JSON-RPC; log to stderr only.
    logging.basicConfig(
        stream=sys.stderr,
        level=cfg.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    # Mute noisy libraries unless debugging.
    if cfg.log_level.upper() != "DEBUG":
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
