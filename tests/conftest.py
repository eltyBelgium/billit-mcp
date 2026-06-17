"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from billit_mcp.client import BillitClient
from billit_mcp.settings import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(  # type: ignore[call-arg]
        BILLIT_API_KEY="test-key",
        BILLIT_PARTY_ID="42",
        BILLIT_BASE_URL="https://api.sandbox.billit.be",
        BILLIT_AUTH_MODE="apikey",
        BILLIT_MAX_RETRIES=0,
    )


@pytest.fixture
async def client(settings: Settings) -> BillitClient:
    c = BillitClient(settings)
    yield c
    await c.aclose()
