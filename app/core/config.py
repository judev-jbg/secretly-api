"""Centralized application configuration loaded from environment variables."""

import json
from urllib.parse import quote_plus

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings for local development and hosted deployments."""

    # DATABASE_URL is preferred for managed providers such as Supabase.
    database_url: str | None = None
    db_host: str | None = None
    db_port: int | None = None
    db_name: str | None = None
    db_user: str | None = None
    db_password: str | None = None

    # JWT
    secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Password reset
    reset_token_expire_minutes: int = 15

    # Email
    smtp_server: str = ""
    smtp_port: int = 587
    sender_email: str = ""
    sender_password: str = ""

    # CORS
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:8080", "http://localhost:5173"]
    )

    # Local server default. Render supplies PORT to the start command.
    port: int = 8100

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        """Accept a JSON list or a comma-separated environment value."""
        if isinstance(value, list):
            return value
        if value.startswith("["):
            return json.loads(value)
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @model_validator(mode="after")
    def set_database_url(self) -> "Settings":
        """Build the legacy local URL only when DATABASE_URL is absent."""
        if self.database_url:
            return self

        required_values = {
            "DB_HOST": self.db_host,
            "DB_PORT": self.db_port,
            "DB_NAME": self.db_name,
            "DB_USER": self.db_user,
            "DB_PASSWORD": self.db_password,
        }
        missing = [name for name, value in required_values.items() if value is None]
        if missing:
            raise ValueError(
                "Configure DATABASE_URL or all of: " + ", ".join(missing)
            )

        self.database_url = (
            f"postgresql://{quote_plus(self.db_user)}:{quote_plus(self.db_password)}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
        return self

    model_config = {"env_file": ".env", "extra": "ignore", "enable_decoding": False}


settings = Settings()
