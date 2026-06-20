"""Tiny helpers shared by tool modules."""

from __future__ import annotations

from typing import Any


def drop_none(d: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``d`` without keys whose value is None."""
    return {k: v for k, v in d.items() if v is not None}


def as_result(value: Any) -> dict[str, Any]:
    """Normalize a Billit response into a dict.

    Several Billit endpoints return bare scalars (e.g. ``POST /orders`` returns
    just the integer OrderID) or JSON arrays. MCP structured output requires a
    dict, so we wrap non-dict values under a predictable key.
    """
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return {"items": value}
    return {"result": value}


def order_id_result(value: Any) -> dict[str, Any]:
    """Wrap a create-order response. Billit returns a bare int OrderID."""
    if isinstance(value, dict):
        return value
    return {"OrderID": value}


def odata_params(
    *,
    top: int | None = None,
    skip: int | None = None,
    filter_: str | None = None,
    orderby: str | None = None,
    select: str | None = None,
    full_text_search: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the query-string dict for an OData-style Billit list endpoint."""
    q: dict[str, Any] = {}
    if top is not None:
        q["$top"] = top
    if skip is not None:
        q["$skip"] = skip
    if filter_:
        q["$filter"] = filter_
    if orderby:
        q["$orderby"] = orderby
    if select:
        q["$select"] = select
    if full_text_search:
        q["fullTextSearch"] = full_text_search
    if extra:
        q.update(extra)
    return q
