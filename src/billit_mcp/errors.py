"""Billit error mapping → MCP-friendly errors.

Billit responses use this envelope on errors:

    {
        "ErrorEnum": "...",
        "ErrorMessage": "...",
        "ErrorParams": [...],
        "DefaultText": "..."
    }

We surface ``BillitError`` to the FastMCP layer; FastMCP turns it into a
tool-execution error (``result.isError = true``) so the model can self-correct.
"""

from __future__ import annotations

from typing import Any


class BillitError(Exception):
    """Anything the Billit API rejects."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        body: Any | None = None,
        hint: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.body = body
        self.hint = hint
        super().__init__(message)

    def __str__(self) -> str:  # surfaced as the tool's text content
        parts = [f"Billit API {self.status_code}: {super().__str__()}"]
        if self.hint:
            parts.append(f"Hint: {self.hint}")
        if self.body is not None:
            parts.append(f"Body: {self.body!r}")
        return " | ".join(parts)


class BillitAuthError(BillitError):
    """401/403 — bad apikey/partyID or expired OAuth token."""


class BillitNotFound(BillitError):
    """404 — wrong ID, or right ID but for a different PartyID."""


class BillitRateLimited(BillitError):
    """429 — back off and retry."""


def from_response(status_code: int, body: Any) -> BillitError:
    """Map an HTTP status + JSON body to the right exception subclass."""
    envelope: dict[str, Any] = body if isinstance(body, dict) else {}
    msg = (
        envelope.get("ErrorMessage")
        or envelope.get("DefaultText")
        or envelope.get("Message")
        or str(body)[:500]
    )

    if status_code in (401, 403):
        hint = (
            "Check that apikey + partyID headers are both set, that they match "
            "the sandbox vs production base URL, and that the user behind the "
            "apikey has access to PartyID. See "
            "https://docs.billit.be/docs/partyid-and-key"
        )
        return BillitAuthError(msg, status_code=status_code, body=envelope, hint=hint)
    if status_code == 404:
        return BillitNotFound(msg, status_code=status_code, body=envelope)
    if status_code == 429:
        return BillitRateLimited(msg, status_code=status_code, body=envelope)
    return BillitError(msg, status_code=status_code, body=envelope)
