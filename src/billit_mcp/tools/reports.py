"""Aggregated/analytic reports."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ..client import BillitClient
from ._common import as_result


def register(mcp: FastMCP, client: BillitClient) -> None:
    @mcp.tool(annotations={"title": "List reports", "readOnlyHint": True})
    async def list_reports(party_id: str | None = None) -> dict[str, Any]:
        """List available report definitions for the current PartyID."""
        return as_result(await client.get("reports", party_id=party_id))

    @mcp.tool(annotations={"title": "Get report", "readOnlyHint": True})
    async def get_report(report_id: int, party_id: str | None = None) -> dict[str, Any]:
        """Fetch a report's generated CSV results."""
        return as_result(await client.get(f"reports/{report_id}", party_id=party_id))
