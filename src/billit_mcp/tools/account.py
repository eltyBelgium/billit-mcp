"""Account / own-company info."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ..client import BillitClient


def register(mcp: FastMCP, client: BillitClient) -> None:
    @mcp.tool(
        annotations={
            "title": "Get account info",
            "readOnlyHint": True,
            "openWorldHint": True,
        }
    )
    async def get_account_info(party_id: str | None = None) -> dict[str, Any]:
        """Return current company info, license, addons, and configured sequences.

        Useful as a connectivity smoke test — if this returns 200 your apikey +
        partyID are valid for the configured base URL.
        """
        return await client.get("account/accountInformation", party_id=party_id)
