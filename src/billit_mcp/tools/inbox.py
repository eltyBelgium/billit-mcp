"""Inbound document / OCR queue (``/v1/toProcess``)."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ..client import BillitClient
from ._common import as_result, drop_none


def register(mcp: FastMCP, client: BillitClient) -> None:
    @mcp.tool(
        annotations={
            "title": "Submit inbound PDF for OCR",
            "readOnlyHint": False,
            "openWorldHint": True,
        }
    )
    async def submit_inbound_pdf(
        file_name: str,
        file_content_base64: Annotated[
            str, Field(description="Base64-encoded PDF bytes.")
        ],
        mime_type: str = "application/pdf",
        idempotent_key: str | None = None,
        party_id: str | None = None,
    ) -> dict[str, Any]:
        """Upload a supplier invoice PDF. Billit OCRs it and surfaces it as a Cost order."""
        body = drop_none(
            {
                "File": {
                    "FileName": file_name,
                    "FileContent": file_content_base64,
                    "MimeType": mime_type,
                }
            }
        )
        return as_result(
            await client.post(
                "toProcess", json=body, party_id=party_id, idempotent_key=idempotent_key
            )
        )

    @mcp.tool(annotations={"title": "List inbound queue", "readOnlyHint": True})
    async def list_inbound_queue(party_id: str | None = None) -> dict[str, Any]:
        """Show items currently in the OCR/inbound queue."""
        return as_result(await client.get("toProcess", party_id=party_id))
