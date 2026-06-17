"""Generic document storage."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ..client import BillitClient
from ._common import drop_none, odata_params


def register(mcp: FastMCP, client: BillitClient) -> None:
    @mcp.tool(annotations={"title": "List documents", "readOnlyHint": True})
    async def list_documents(
        search: str | None = None,
        top: Annotated[int, Field(ge=1, le=200)] = 50,
        skip: Annotated[int, Field(ge=0)] = 0,
        party_id: str | None = None,
    ) -> dict[str, Any]:
        """List documents stored against the current PartyID."""
        return await client.get(
            "documents",
            params=odata_params(top=top, skip=skip, full_text_search=search),
            party_id=party_id,
        )

    @mcp.tool(annotations={"title": "Get document", "readOnlyHint": True})
    async def get_document(document_id: int, party_id: str | None = None) -> dict[str, Any]:
        """Fetch one document's metadata + file references."""
        return await client.get(f"documents/{document_id}", party_id=party_id)

    @mcp.tool(
        annotations={
            "title": "Upload document",
            "readOnlyHint": False,
            "openWorldHint": True,
        }
    )
    async def upload_document(
        name: str,
        file_content_base64: Annotated[
            str, Field(description="Base64-encoded file bytes.")
        ],
        mime_type: str = "application/pdf",
        description: str | None = None,
        document_date: str | None = None,
        tags: list[str] | None = None,
        idempotent_key: str | None = None,
        party_id: str | None = None,
    ) -> dict[str, Any]:
        """Upload a document (inline base64). Returns the new DocumentID."""
        body = drop_none(
            {
                "Name": name,
                "Description": description,
                "DocumentDate": document_date,
                "Tags": tags,
                "File": {
                    "FileName": name,
                    "FileContent": file_content_base64,
                    "MimeType": mime_type,
                },
            }
        )
        return await client.post(
            "documents", json=body, party_id=party_id, idempotent_key=idempotent_key
        )
