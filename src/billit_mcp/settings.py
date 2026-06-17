"""Runtime configuration. All values come from environment variables.

Sandbox is the default base URL — opt in to production explicitly by setting
``BILLIT_BASE_URL=https://api.billit.be``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AuthMode = Literal["apikey", "oauth"]
Transport = Literal["stdio", "http"]

SANDBOX_BASE_URL = "https://api.sandbox.billit.be"
PRODUCTION_BASE_URL = "https://api.billit.be"


class Settings(BaseSettings):
    """Server settings, loaded from environment / .env."""

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Billit ---
    api_key: str | None = Field(default=None, alias="BILLIT_API_KEY")
    party_id: str | None = Field(default=None, alias="BILLIT_PARTY_ID")
    base_url: str = Field(default=SANDBOX_BASE_URL, alias="BILLIT_BASE_URL")
    auth_mode: AuthMode = Field(default="apikey", alias="BILLIT_AUTH_MODE")
    timeout: float = Field(default=30.0, alias="BILLIT_TIMEOUT")
    max_retries: int = Field(default=3, alias="BILLIT_MAX_RETRIES")

    # OAuth (only used when auth_mode == "oauth")
    oauth_client_id: str | None = Field(default=None, alias="BILLIT_OAUTH_CLIENT_ID")
    oauth_client_secret: str | None = Field(default=None, alias="BILLIT_OAUTH_CLIENT_SECRET")
    oauth_refresh_token: str | None = Field(default=None, alias="BILLIT_OAUTH_REFRESH_TOKEN")

    # --- MCP server ---
    transport: Transport = Field(default="stdio", alias="MCP_TRANSPORT")
    host: str = Field(default="127.0.0.1", alias="MCP_HOST")
    port: int = Field(default=8000, alias="MCP_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def is_production(self) -> bool:
        return self.base_url.rstrip("/") == PRODUCTION_BASE_URL

    @property
    def normalized_base_url(self) -> str:
        return self.base_url.rstrip("/")

    @model_validator(mode="after")
    def _check_auth_config(self) -> Settings:
        if self.auth_mode == "apikey":
            if not self.api_key:
                raise ValueError(
                    "BILLIT_API_KEY is required when BILLIT_AUTH_MODE=apikey. "
                    "Get one from https://my.sandbox.billit.be → My Profile."
                )
            if not self.party_id:
                raise ValueError(
                    "BILLIT_PARTY_ID is required. Every Billit call needs the "
                    "partyID header — see https://docs.billit.be/docs/partyid-and-key"
                )
        elif self.auth_mode == "oauth":
            missing = [
                name
                for name, val in [
                    ("BILLIT_OAUTH_CLIENT_ID", self.oauth_client_id),
                    ("BILLIT_OAUTH_CLIENT_SECRET", self.oauth_client_secret),
                    ("BILLIT_OAUTH_REFRESH_TOKEN", self.oauth_refresh_token),
                ]
                if not val
            ]
            if missing:
                raise ValueError(
                    f"OAuth mode requires: {', '.join(missing)}. "
                    "Email support@billit.eu to obtain credentials."
                )
        return self


def load() -> Settings:
    """Load settings; raises ValidationError with a clear message on bad config."""
    return Settings()  # type: ignore[call-arg]
