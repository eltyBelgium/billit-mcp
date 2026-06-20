"""Product catalogue tools."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ..client import BillitClient
from ._common import as_result, drop_none, odata_params


def register(mcp: FastMCP, client: BillitClient) -> None:
    @mcp.tool(annotations={"title": "List products", "readOnlyHint": True, "openWorldHint": True})
    async def list_products(
        search: str | None = None,
        top: Annotated[int, Field(ge=1, le=200)] = 50,
        skip: Annotated[int, Field(ge=0)] = 0,
        party_id: str | None = None,
    ) -> dict[str, Any]:
        """List catalogue products."""
        return await client.get(
            "products",
            params=odata_params(top=top, skip=skip, full_text_search=search),
            party_id=party_id,
        )

    @mcp.tool(annotations={"title": "Get product", "readOnlyHint": True})
    async def get_product(product_id: int, party_id: str | None = None) -> dict[str, Any]:
        """Fetch one product by ID."""
        return await client.get(f"products/{product_id}", party_id=party_id)

    @mcp.tool(
        annotations={
            "title": "Upsert product",
            "readOnlyHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        }
    )
    async def upsert_product(
        reference: Annotated[
            str, Field(description="Your SKU / internal reference. Acts as upsert key.")
        ],
        description: str,
        amount_excl: float,
        vat_percentage: float = 21.0,
        unit: str | None = None,
        ean: str | None = None,
        idempotent_key: str | None = None,
        party_id: str | None = None,
    ) -> dict[str, Any]:
        """Create or update a product by reference."""
        body = drop_none(
            {
                "Reference": reference,
                "Description": description,
                "AmountExcl": amount_excl,
                "VAT": vat_percentage,
                "Unit": unit,
                "EAN": ean,
            }
        )
        return as_result(
            await client.post(
                "products", json=body, party_id=party_id, idempotent_key=idempotent_key
            )
        )
