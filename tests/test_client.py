"""Billit client behaviour — auth headers, idempotency, error mapping."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from billit_mcp.client import BillitClient
from billit_mcp.errors import BillitAuthError, BillitNotFound


async def test_apikey_headers_attached(client: BillitClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://api.sandbox.billit.be/v1/account/accountInformation",
        json={"CompanyName": "Test BV"},
    )
    out = await client.get("account/accountInformation")
    assert out == {"CompanyName": "Test BV"}

    req = httpx_mock.get_request()
    assert req is not None
    assert req.headers["apikey"] == "test-key"
    assert req.headers["partyID"] == "42"


async def test_party_id_override(client: BillitClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://api.sandbox.billit.be/v1/orders/9",
        json={"OrderID": 9},
    )
    await client.get("orders/9", party_id="999")
    req = httpx_mock.get_request()
    assert req is not None
    assert req.headers["partyID"] == "999"


async def test_idempotent_key_auto_set_on_post(
    client: BillitClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        method="POST",
        url="https://api.sandbox.billit.be/v1/orders",
        json={"OrderID": 1},
    )
    await client.post("orders", json={"OrderType": "Invoice"})
    req = httpx_mock.get_request()
    assert req is not None
    assert "Idempotent-Key" in req.headers
    assert len(req.headers["Idempotent-Key"]) >= 8


async def test_explicit_idempotent_key_wins(
    client: BillitClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        method="POST",
        url="https://api.sandbox.billit.be/v1/orders",
        json={"OrderID": 1},
    )
    await client.post("orders", json={}, idempotent_key="my-key")
    req = httpx_mock.get_request()
    assert req is not None
    assert req.headers["Idempotent-Key"] == "my-key"


async def test_401_maps_to_auth_error(
    client: BillitClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://api.sandbox.billit.be/v1/orders/1",
        status_code=401,
        json={"ErrorMessage": "bad key"},
    )
    with pytest.raises(BillitAuthError) as exc:
        await client.get("orders/1")
    assert "bad key" in str(exc.value)
    assert exc.value.status_code == 401


async def test_404_maps_to_not_found(
    client: BillitClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://api.sandbox.billit.be/v1/orders/999",
        status_code=404,
        json={"ErrorMessage": "not found"},
    )
    with pytest.raises(BillitNotFound):
        await client.get("orders/999")


async def test_collect_paginates(client: BillitClient, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://api.sandbox.billit.be/v1/orders?%24top=2",
        json={
            "Items": [{"OrderID": 1}, {"OrderID": 2}],
            "NextPageLink": "https://api.sandbox.billit.be/v1/orders?%24top=2&%24skip=2",
        },
    )
    httpx_mock.add_response(
        method="GET",
        url="https://api.sandbox.billit.be/v1/orders?%24top=2&%24skip=2",
        json={"Items": [{"OrderID": 3}], "NextPageLink": None},
    )
    items = await client.collect("orders", page_size=2)
    assert [i["OrderID"] for i in items] == [1, 2, 3]


async def test_error_envelope_passthrough(
    client: BillitClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        method="POST",
        url="https://api.sandbox.billit.be/v1/orders",
        status_code=400,
        json={"ErrorEnum": "InvalidVAT", "ErrorMessage": "VATNumber invalid"},
    )
    with pytest.raises(Exception) as exc:
        await client.post("orders", json={})
    msg = str(exc.value)
    assert "VATNumber invalid" in msg or "InvalidVAT" in repr(exc.value.body)  # type: ignore[attr-defined]
