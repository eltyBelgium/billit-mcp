"""Async HTTP wrapper around the Billit REST API.

A single :class:`BillitClient` is shared across all tool calls. It owns the
``httpx.AsyncClient``, attaches auth headers, injects an ``Idempotent-Key``
on POST requests, and maps non-2xx responses to typed exceptions.

The wrapper deliberately stays thin — all Billit-specific knowledge lives in
the tool modules. Pagination helpers are here because they're transport-level.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator, Mapping
from typing import Any

import httpx

from . import errors
from .auth import AuthHeaders, OAuthTokenSource, make_auth
from .settings import Settings

log = logging.getLogger(__name__)

_DEFAULT_RETRY_STATUS = {429, 500, 502, 503, 504}


class BillitClient:
    """Thin async client. One instance per process, share across tools."""

    def __init__(
        self,
        settings: Settings,
        *,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._http = http or httpx.AsyncClient(
            base_url=settings.normalized_base_url,
            timeout=settings.timeout,
            http2=True,
            headers={"User-Agent": "billit-mcp/0.1"},
        )
        self._auth: AuthHeaders
        self._oauth: OAuthTokenSource | None
        self._auth, self._oauth = make_auth(settings)

    @property
    def settings(self) -> Settings:
        return self._settings

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> BillitClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    # ------------------------------------------------------------------ core

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        party_id: str | None = None,
        idempotent_key: str | None = None,
        extra_headers: Mapping[str, str] | None = None,
    ) -> Any:
        """Make a request and return the parsed JSON body."""
        url = path if path.startswith("http") else f"/v1/{path.lstrip('/')}"
        headers = dict(await self._auth.build(self._http, party_id_override=party_id))
        if json is not None:
            headers["Content-Type"] = "application/json"
        if method.upper() in {"POST", "PUT", "PATCH"}:
            headers["Idempotent-Key"] = idempotent_key or str(uuid.uuid4())
        if extra_headers:
            headers.update(extra_headers)

        attempt = 0
        while True:
            attempt += 1
            resp = await self._http.request(
                method, url, params=params, json=json, headers=headers
            )
            if resp.status_code < 400:
                return _parse(resp)
            # Refresh once on a 401 in OAuth mode (token may have expired between
            # cache check and request).
            if (
                resp.status_code in (401,)
                and self._oauth is not None
                and attempt == 1
            ):
                log.info("Billit returned 401; forcing OAuth refresh and retrying")
                token = await self._oauth.access_token(self._http, force_refresh=True)
                headers["Authorization"] = f"Bearer {token}"
                continue
            if (
                resp.status_code in _DEFAULT_RETRY_STATUS
                and attempt <= self._settings.max_retries
            ):
                backoff = min(2 ** (attempt - 1), 8)
                log.warning(
                    "Billit %s on %s — retrying in %.1fs (attempt %d/%d)",
                    resp.status_code,
                    url,
                    backoff,
                    attempt,
                    self._settings.max_retries,
                )
                await asyncio.sleep(backoff)
                continue
            raise errors.from_response(resp.status_code, _parse(resp))

    # ------------------------------------------------------------------ verbs

    async def get(self, path: str, **kw: Any) -> Any:
        return await self.request("GET", path, **kw)

    async def post(self, path: str, **kw: Any) -> Any:
        return await self.request("POST", path, **kw)

    async def patch(self, path: str, **kw: Any) -> Any:
        return await self.request("PATCH", path, **kw)

    async def put(self, path: str, **kw: Any) -> Any:
        return await self.request("PUT", path, **kw)

    async def delete(self, path: str, **kw: Any) -> Any:
        return await self.request("DELETE", path, **kw)

    # ------------------------------------------------------------------ pagination

    async def paginate(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        page_size: int = 50,
        max_items: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield items from a Billit list endpoint, following ``NextPageLink``.

        Stops after ``max_items`` if set. Pass ``params={"fullTextSearch": "..."}``
        for cross-field search, or OData filter params (``$filter``, ``$orderby``).
        """
        q = {"$top": page_size, **(params or {})}
        url: str | None = path
        seen = 0
        while url:
            resp = await self.get(url, params=q if url == path else None)
            items = resp.get("Items") if isinstance(resp, dict) else None
            if items is None and isinstance(resp, list):
                items = resp
            for item in items or []:
                yield item
                seen += 1
                if max_items is not None and seen >= max_items:
                    return
            next_link = (
                resp.get("NextPageLink") if isinstance(resp, dict) else None
            )
            url = next_link or None

    async def collect(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        page_size: int = 50,
        max_items: int | None = 200,
    ) -> list[dict[str, Any]]:
        """Convenience: drain :meth:`paginate` into a list (with a sane cap)."""
        out: list[dict[str, Any]] = []
        async for item in self.paginate(
            path, params=params, page_size=page_size, max_items=max_items
        ):
            out.append(item)
        return out


def _parse(resp: httpx.Response) -> Any:
    if not resp.content:
        return None
    ctype = resp.headers.get("content-type", "")
    if "json" in ctype:
        try:
            return resp.json()
        except Exception:
            return resp.text
    return resp.text
