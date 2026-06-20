"""Party tools — customers and suppliers."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from ..client import BillitClient
from ._common import as_result, drop_none, odata_params

PartyType = Literal["Customer", "Supplier"]


def register(mcp: FastMCP, client: BillitClient) -> None:
    @mcp.tool(annotations={"title": "List parties", "readOnlyHint": True, "openWorldHint": True})
    async def list_parties(
        party_type: PartyType | None = None,
        search: Annotated[
            str | None,
            Field(description="Free-text search across name, VAT, email."),
        ] = None,
        top: Annotated[int, Field(ge=1, le=200)] = 50,
        skip: Annotated[int, Field(ge=0)] = 0,
        party_id: str | None = None,
    ) -> dict[str, Any]:
        """List customers and/or suppliers."""
        clauses = [f"PartyType eq '{party_type}'"] if party_type else []
        params = odata_params(
            top=top,
            skip=skip,
            filter_=" and ".join(clauses) or None,
            full_text_search=search,
            orderby="Name asc",
        )
        return await client.get("parties", params=params, party_id=party_id)

    @mcp.tool(annotations={"title": "Get party", "readOnlyHint": True, "openWorldHint": True})
    async def get_party(target_party_id: int, party_id: str | None = None) -> dict[str, Any]:
        """Fetch one party by its resource ID. (Different integer than the company PartyID header.)"""
        return await client.get(f"parties/{target_party_id}", party_id=party_id)

    @mcp.tool(
        annotations={
            "title": "Find party by VAT",
            "readOnlyHint": True,
            "openWorldHint": True,
        }
    )
    async def find_party_by_vat(
        vat_number: Annotated[
            str, Field(description="VAT number, e.g. 'BE0563846944' (with country prefix).")
        ],
        party_id: str | None = None,
    ) -> dict[str, Any]:
        """Look up a party by VAT number. Returns the first match or an empty list."""
        params = odata_params(filter_=f"VATNumber eq '{vat_number}'", top=5)
        return await client.get("parties", params=params, party_id=party_id)

    @mcp.tool(
        annotations={
            "title": "Create or upsert party",
            "readOnlyHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        }
    )
    async def create_party(
        name: str,
        party_type: PartyType,
        vat_number: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        iban: str | None = None,
        addresses: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "List of addresses, each {'AddressType': 'InvoiceAddress'|"
                    "'DeliveryAddress', 'Street': ..., 'City': ..., 'Zipcode': ..., "
                    "'CountryCode': 'BE'}"
                )
            ),
        ] = None,
        idempotent_key: str | None = None,
        party_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a customer or supplier. Billit will upsert by VATNumber where possible."""
        body = drop_none(
            {
                "Name": name,
                "PartyType": party_type,
                "VATNumber": vat_number,
                "Email": email,
                "Phone": phone,
                "IBAN": iban,
                "Addresses": addresses,
            }
        )
        return as_result(
            await client.post(
                "parties", json=body, party_id=party_id, idempotent_key=idempotent_key
            )
        )

    @mcp.tool(
        annotations={
            "title": "Update party",
            "readOnlyHint": False,
            "openWorldHint": True,
        }
    )
    async def update_party(
        target_party_id: int,
        patch: dict[str, Any],
        party_id: str | None = None,
    ) -> dict[str, Any]:
        """PATCH a party. Pass only the fields you want to change."""
        return as_result(
            await client.patch(f"parties/{target_party_id}", json=patch, party_id=party_id)
        )
