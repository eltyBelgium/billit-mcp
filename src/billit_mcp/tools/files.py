"""Binary file download by UUID."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Annotated, Any

import httpx
from fastmcp import FastMCP
from pydantic import Field

from ..client import BillitClient


def register(mcp: FastMCP, client: BillitClient) -> None:
    @mcp.tool(
        annotations={
            "title": "Download file",
            "readOnlyHint": True,
            "openWorldHint": True,
        }
    )
    async def download_file(
        file_id: Annotated[
            str, Field(description="File UUID, typically from Order.OrderPDF.FileID.")
        ],
        save_to: Annotated[
            str | None,
            Field(
                description=(
                    "Optional absolute path on the host running the MCP server. "
                    "When omitted, the file is returned inline as base64."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Download a file by its UUID. Returns base64 or saves to disk."""
        # Use the raw HTTP client so we can read bytes — files are not JSON.
        headers = dict(await client._auth.build(client._http))  # type: ignore[attr-defined]
        url = f"/v1/files/{file_id}"
        resp: httpx.Response = await client._http.request("GET", url, headers=headers)  # type: ignore[attr-defined]
        if resp.status_code >= 400:
            return {"error": resp.status_code, "body": resp.text[:500]}
        content = resp.content
        if save_to:
            path = Path(save_to).expanduser().resolve()
            path.write_bytes(content)
            return {
                "file_id": file_id,
                "path": str(path),
                "bytes": len(content),
                "content_type": resp.headers.get("content-type"),
            }
        return {
            "file_id": file_id,
            "content_type": resp.headers.get("content-type"),
            "base64": base64.b64encode(content).decode("ascii"),
            "bytes": len(content),
        }
