"""ChatGPT Apps SDK compatibility — ``search`` and ``fetch`` tools.

ChatGPT (and especially Deep Research) expects servers to expose two specific
tools with these exact signatures:

* ``search(query) -> { results: [{ id, title, url }] }``
* ``fetch(id)    -> { id, title, text, url, metadata? }``

We map both onto Billit's orders + parties surface so the model can browse
invoices and contacts without thinking about Billit's resource taxonomy.

References:
- https://developers.openai.com/apps-sdk/build/mcp-server
"""

from __future__ import annotations

import json
from typing import Any

from fastmcp import FastMCP

from ..client import BillitClient
from ._common import odata_params

_ORDER_PREFIX = "order:"
_PARTY_PREFIX = "party:"


def register(mcp: FastMCP, client: BillitClient) -> None:
    @mcp.tool(
        annotations={
            "title": "Search Billit",
            "readOnlyHint": True,
            "openWorldHint": True,
        }
    )
    async def search(query: str) -> dict[str, Any]:
        """Search invoices and customers/suppliers across Billit.

        Returns ChatGPT Apps SDK-compatible records:
        ``{ "results": [ { "id": "order:123", "title": "...", "url": "..." } ] }``
        """
        results: list[dict[str, str]] = []

        # Orders — first page, sorted newest first.
        orders_resp = await client.get(
            "orders",
            params=odata_params(top=10, full_text_search=query, orderby="OrderDate desc"),
        )
        for o in _items(orders_resp):
            oid = o.get("OrderID") or o.get("Id")
            if oid is None:
                continue
            title = (
                f"{o.get('OrderType', 'Order')} {o.get('OrderNumber', '')} — "
                f"{(o.get('Customer') or {}).get('Name', '')}"
            ).strip(" —")
            results.append(
                {
                    "id": f"{_ORDER_PREFIX}{oid}",
                    "title": title or f"Order {oid}",
                    "url": _ui_order_url(client, oid),
                }
            )

        # Parties.
        parties_resp = await client.get(
            "parties",
            params=odata_params(top=10, full_text_search=query, orderby="Name asc"),
        )
        for p in _items(parties_resp):
            pid = p.get("PartyID") or p.get("Id")
            if pid is None:
                continue
            results.append(
                {
                    "id": f"{_PARTY_PREFIX}{pid}",
                    "title": p.get("Name") or f"Party {pid}",
                    "url": _ui_party_url(client, pid),
                }
            )

        return {"results": results}

    @mcp.tool(
        annotations={
            "title": "Fetch Billit record",
            "readOnlyHint": True,
            "openWorldHint": True,
        }
    )
    async def fetch(id: str) -> dict[str, Any]:  # noqa: A002 — name fixed by spec
        """Fetch a single record by the ID returned from ``search``."""
        if id.startswith(_ORDER_PREFIX):
            oid = id[len(_ORDER_PREFIX) :]
            order = await client.get(f"orders/{oid}")
            return {
                "id": id,
                "title": (
                    f"{order.get('OrderType', 'Order')} {order.get('OrderNumber', '')}"
                ).strip(),
                "text": json.dumps(order, ensure_ascii=False, indent=2, default=str),
                "url": _ui_order_url(client, oid),
                "metadata": {
                    "type": order.get("OrderType"),
                    "direction": order.get("OrderDirection"),
                    "status": order.get("OrderStatus"),
                    "totalIncl": order.get("TotalIncl"),
                    "paid": order.get("Paid"),
                },
            }
        if id.startswith(_PARTY_PREFIX):
            pid = id[len(_PARTY_PREFIX) :]
            party = await client.get(f"parties/{pid}")
            return {
                "id": id,
                "title": party.get("Name") or f"Party {pid}",
                "text": json.dumps(party, ensure_ascii=False, indent=2, default=str),
                "url": _ui_party_url(client, pid),
                "metadata": {
                    "type": party.get("PartyType"),
                    "vat": party.get("VATNumber"),
                    "email": party.get("Email"),
                },
            }
        return {
            "id": id,
            "title": "Unknown record",
            "text": (
                f"Unknown ID format {id!r}. Expected '{_ORDER_PREFIX}<id>' "
                f"or '{_PARTY_PREFIX}<id>'."
            ),
            "url": "",
        }


def _items(resp: Any) -> list[dict[str, Any]]:
    if isinstance(resp, dict):
        items = resp.get("Items")
        if isinstance(items, list):
            return items
    if isinstance(resp, list):
        return resp
    return []


def _ui_order_url(client: BillitClient, oid: object) -> str:
    base = client.settings.normalized_base_url
    ui = base.replace("api.", "my.").replace("/v1", "")
    return f"{ui}/Order/Edit/{oid}"


def _ui_party_url(client: BillitClient, pid: object) -> str:
    base = client.settings.normalized_base_url
    ui = base.replace("api.", "my.").replace("/v1", "")
    return f"{ui}/Party/Edit/{pid}"
