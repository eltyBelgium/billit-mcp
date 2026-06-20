"""Peppol network — participant registration, inbox, lookup."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ..client import BillitClient
from ._common import as_result


def register(mcp: FastMCP, client: BillitClient) -> None:
    @mcp.tool(
        annotations={
            "title": "Lookup Peppol participant",
            "readOnlyHint": True,
            "openWorldHint": True,
        }
    )
    async def lookup_peppol_participant(
        vat_or_cbe: Annotated[
            str,
            Field(
                description=(
                    "VAT number (e.g. 'BE0563846944') or Belgian CBE/KBO number. "
                    "This endpoint requires no authentication on Billit's side."
                )
            ),
        ],
    ) -> dict[str, Any]:
        """Check whether a company is registered on the Peppol network.

        Useful as a pre-flight check before attempting to send via Peppol —
        if the participant doesn't exist, the send will fail.
        """
        return as_result(await client.get(f"peppol/participantInformation/{vat_or_cbe}"))

    @mcp.tool(annotations={"title": "List Peppol inbox", "readOnlyHint": True})
    async def list_peppol_inbox(party_id: str | None = None) -> dict[str, Any]:
        """Show inbound Peppol documents (returns first 10 items)."""
        return as_result(await client.get("peppol/inbox", party_id=party_id))

    @mcp.tool(
        annotations={
            "title": "Accept Peppol document",
            "readOnlyHint": False,
            "openWorldHint": True,
        }
    )
    async def confirm_peppol_inbox(
        inbox_item_id: int,
        party_id: str | None = None,
    ) -> dict[str, Any]:
        """Accept an inbound Peppol document into your Billit inbox."""
        return as_result(
            await client.post(f"peppol/inbox/{inbox_item_id}/confirm", party_id=party_id)
        )

    @mcp.tool(
        annotations={
            "title": "Refuse Peppol document",
            "readOnlyHint": False,
            "destructiveHint": True,
            "openWorldHint": True,
        }
    )
    async def refuse_peppol_inbox(
        inbox_item_id: int,
        party_id: str | None = None,
    ) -> dict[str, Any]:
        """Reject an inbound Peppol document."""
        return as_result(
            await client.post(f"peppol/inbox/{inbox_item_id}/refuse", party_id=party_id)
        )

    @mcp.tool(
        annotations={
            "title": "Register on Peppol",
            "readOnlyHint": False,
            "openWorldHint": True,
        }
    )
    async def register_peppol_participant(
        party_id: str | None = None,
    ) -> dict[str, Any]:
        """Register the current company on the Peppol network."""
        return as_result(await client.post("peppol/participants", party_id=party_id))
