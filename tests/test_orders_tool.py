"""End-to-end test that the orders module wires tools onto a FastMCP server.

Uses FastMCP's in-memory ``Client`` (no subprocess, no real MCP transport) so we
exercise the real tool-dispatch path. Billit HTTP calls are mocked via
``pytest-httpx``.
"""

from __future__ import annotations

import pytest
from fastmcp import Client
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
    mcp, backend = build_server(cfg)
    try:
        async with Client(mcp) as c:
            tools = await c.list_tools()
        names = {t.name for t in tools}
        assert "list_orders" in names
        assert "create_invoice" in names
        assert "send_orders" in names
        assert "search" in names  # ChatGPT compat
        assert "fetch" in names
    finally:
        await backend.aclose()


async def test_create_invoice_calls_billit(cfg: Settings, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url="https://api.sandbox.billit.be/v1/orders",
        json=12345,
    )
    mcp, backend = build_server(cfg)
    try:
        async with Client(mcp) as c:
            await c.call_tool(
                "create_invoice",
                {
                    "customer": {"PartyID": 7},
                    "order_lines": [
                        {
                            "Quantity": 1,
                            "UnitPriceExcl": 10.0,
                            "Description": "x",
                            "VATPercentage": 21,
                        }
                    ],
                },
            )
        # Assert on the outgoing Billit request rather than the tool return value.
        req = httpx_mock.get_request()
        assert req is not None
        assert req.url.path == "/v1/orders"
        assert req.headers["apikey"] == "k"
        assert req.headers["partyID"] == "1"
        body = req.read()
        assert b'"OrderType":"Invoice"' in body or b'"OrderType": "Invoice"' in body
    finally:
        await backend.aclose()
