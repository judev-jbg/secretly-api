"""Modelo ORM para la tabla secrets."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey
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

    user: Mapped["User"] = relationship(back_populates="secrets")
