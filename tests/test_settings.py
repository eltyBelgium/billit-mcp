"""Settings validation behaviour."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from billit_mcp.settings import PRODUCTION_BASE_URL, SANDBOX_BASE_URL, Settings


def test_apikey_mode_requires_key_and_party_id() -> None:
    with pytest.raises(ValidationError):
        Settings(BILLIT_AUTH_MODE="apikey")  # type: ignore[call-arg]


def test_apikey_mode_requires_party_id() -> None:
    with pytest.raises(ValidationError):
        Settings(BILLIT_AUTH_MODE="apikey", BILLIT_API_KEY="x")  # type: ignore[call-arg]


def test_apikey_mode_ok() -> None:
    cfg = Settings(  # type: ignore[call-arg]
        BILLIT_AUTH_MODE="apikey", BILLIT_API_KEY="x", BILLIT_PARTY_ID="1"
    )
    assert cfg.base_url == SANDBOX_BASE_URL
    assert not cfg.is_production


def test_production_flag() -> None:
    cfg = Settings(  # type: ignore[call-arg]
        BILLIT_AUTH_MODE="apikey",
        BILLIT_API_KEY="x",
        BILLIT_PARTY_ID="1",
        BILLIT_BASE_URL=PRODUCTION_BASE_URL,
    )
    assert cfg.is_production


def test_oauth_mode_requires_credentials() -> None:
    with pytest.raises(ValidationError):
        Settings(BILLIT_AUTH_MODE="oauth")  # type: ignore[call-arg]
