"""Auth header construction + OAuth refresh.

Two modes:

* **apikey** — Static ``apikey`` + ``partyID`` headers. Personal use only per
  Billit terms.
* **oauth** — ``Authorization: Bearer <access_token>``, refreshed on demand from
  the single-use refresh token. The PartyID is implicit in the token scope, but
  Billit still expects the ``partyID`` header on most calls if supplied.

The implementation here is intentionally small and synchronous-ish; refresh
runs via ``httpx.AsyncClient`` in :meth:`OAuthTokenSource.access_token`.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

import httpx

from .errors import BillitAuthError
from .settings import Settings

log = logging.getLogger(__name__)


@dataclass
class OAuthTokenSource:
    """Caches an access token; refreshes on expiry or 401."""

    settings: Settings
    _access_token: str | None = None
    _expires_at: float = 0.0
    _refresh_token: str | None = None
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def __post_init__(self) -> None:
        self._refresh_token = self.settings.oauth_refresh_token

    async def access_token(self, http: httpx.AsyncClient, force_refresh: bool = False) -> str:
        async with self._lock:
            if (
                not force_refresh
                and self._access_token
                and time.time() < self._expires_at - 60
            ):
                return self._access_token
            await self._refresh(http)
            assert self._access_token is not None
            return self._access_token

    async def _refresh(self, http: httpx.AsyncClient) -> None:
        if not self._refresh_token:
            raise BillitAuthError(
                "OAuth refresh token missing or already consumed",
                status_code=401,
                hint="Refresh tokens are single-use — store the new one returned on each refresh.",
            )
        url = f"{self.settings.normalized_base_url}/OAuth2/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
            "client_id": self.settings.oauth_client_id,
            "client_secret": self.settings.oauth_client_secret,
        }
        log.debug("Refreshing Billit OAuth token at %s", url)
        resp = await http.post(url, json=payload, timeout=self.settings.timeout)
        if resp.status_code >= 400:
            raise BillitAuthError(
                "OAuth refresh failed",
                status_code=resp.status_code,
                body=_safe_json(resp),
                hint="Verify BILLIT_OAUTH_CLIENT_ID / SECRET and that the refresh token has not already been used.",
            )
        data = resp.json()
        self._access_token = data["access_token"]
        # Billit returns expires_in in seconds (typically 3600).
        self._expires_at = time.time() + float(data.get("expires_in", 3600))
        # Billit rotates the refresh token on each refresh — replace ours.
        if rt := data.get("refresh_token"):
            self._refresh_token = rt
            log.info(
                "Billit OAuth refresh token rotated — persist this value in your secret store: %s…",
                rt[:8],
            )


class AuthHeaders:
    """Computes the headers attached to every Billit request."""

    def __init__(self, settings: Settings, oauth: OAuthTokenSource | None = None) -> None:
        self._settings = settings
        self._oauth = oauth

    async def build(
        self, http: httpx.AsyncClient, *, party_id_override: str | None = None
    ) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._settings.auth_mode == "apikey":
            assert self._settings.api_key is not None
            headers["apikey"] = self._settings.api_key
            pid = party_id_override or self._settings.party_id
            if pid:
                headers["partyID"] = pid
        else:
            assert self._oauth is not None
            token = await self._oauth.access_token(http)
            headers["Authorization"] = f"Bearer {token}"
            pid = party_id_override or self._settings.party_id
            if pid:
                headers["partyID"] = pid
        return headers


def make_auth(settings: Settings) -> tuple[AuthHeaders, OAuthTokenSource | None]:
    """Build the headers helper and (if applicable) the OAuth refresh source."""
    if settings.auth_mode == "oauth":
        src = OAuthTokenSource(settings=settings)
        return AuthHeaders(settings, src), src
    return AuthHeaders(settings, None), None


def _safe_json(resp: httpx.Response) -> object:
    try:
        return resp.json()
    except Exception:
        return resp.text[:500]
