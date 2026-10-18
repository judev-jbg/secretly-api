"""Small idempotent migrations for deployments created before Alembic."""

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


logger = logging.getLogger(__name__)


SECRET_COLUMNS = {
    "deleted_at": "TIMESTAMP",
    "failed_unlock_attempts": "INTEGER NOT NULL DEFAULT 0",
    "locked_at": "TIMESTAMP",
    "unlock_token_hash": "VARCHAR(64)",
    "unlock_token_expires": "TIMESTAMP",
}


def migrate_secret_lifecycle(engine: Engine) -> None:
    """Add lifecycle columns and active-alias index to an existing database."""
    inspector = inspect(engine)
    if "secrets" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("secrets")}
    with engine.begin() as connection:
        for name, definition in SECRET_COLUMNS.items():
            if name not in existing:
                logger.info("Adding secrets.%s", name)
                connection.execute(
                    text(f"ALTER TABLE secrets ADD COLUMN {name} {definition}")
                )
        connection.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_secrets_user_active_alias "
            "ON secrets (user_id, lower(trim(alias))) WHERE deleted_at IS NULL"
        ))
