"""Modelo ORM para la tabla secrets."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Integer, String, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, StringUUID


class Secret(Base):
    """Representa un secreto cifrado almacenado en el vault."""

    __tablename__ = "secrets"

    id: Mapped[str] = mapped_column(
        StringUUID, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(StringUUID, ForeignKey("users.id"), nullable=False)
    alias: Mapped[str] = mapped_column(String(255), nullable=False)
    secret_type: Mapped[str] = mapped_column(String(50), nullable=False)
    encrypted: Mapped[str] = mapped_column(String, nullable=False)
    iv: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_unlock_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    unlock_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    unlock_token_expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="secrets")

    @property
    def is_locked(self) -> bool:
        """Expose lock state without leaking token metadata."""
        return self.locked_at is not None


Index(
    "uq_secrets_user_active_alias",
    Secret.user_id,
    func.lower(func.trim(Secret.alias)),
    unique=True,
    postgresql_where=Secret.deleted_at.is_(None),
    sqlite_where=Secret.deleted_at.is_(None),
)
