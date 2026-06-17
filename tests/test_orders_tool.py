"""End-to-end test that the orders module wires tools onto a FastMCP server."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from billit_mcp.server import build_server
from billit_mcp.settings import Settings


@pytest.fixture
def cfg() -> Settings:
    return Settings(  # type: ignore[call-arg]
        BILLIT_API_KEY="k",
        BILLIT_PARTY_ID="1",
        BILLIT_AUTH_MODE="apikey",
        BILLIT_MAX_RETRIES=0,
    )


async def test_server_exposes_orders_tools(cfg: Settings) -> None:
    mcp, client = build_server(cfg)
    try:
        tools = await mcp.get_tools()
        names = {t.name for t in tools.values()} if isinstance(tools, dict) else {t.name for t in tools}
        assert "list_orders" in names
        assert "create_invoice" in names
        assert "send_orders" in names
        assert "search" in names  # ChatGPT compat
        assert "fetch" in names
    finally:
        await client.aclose()


async def test_create_invoice_calls_billit(cfg: Settings, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url="https://api.sandbox.billit.be/v1/orders",
        json=12345,
    )
    mcp, client = build_server(cfg)
    try:
        # FastMCP supports calling tools via the in-process API.
        result = await mcp._tool_manager.call_tool(  # type: ignore[attr-defined]
            "create_invoice",
            {
                "customer": {"PartyID": 7},
                "order_lines": [
                    {"Quantity": 1, "UnitPriceExcl": 10.0, "Description": "x", "VATPercentage": 21}
                ],
            },
        )
        # Result shape varies by FastMCP version; just confirm Billit was called.
        req = httpx_mock.get_request()
        assert req is not None
        assert req.url.path == "/v1/orders"
        body = req.read()
        assert b'"OrderType":"Invoice"' in body or b'"OrderType": "Invoice"' in body
    finally:
        await client.aclose()
