"""Modelo ORM para la tabla users."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, StringUUID


class User(Base):
    """Representa un usuario registrado en el sistema."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        StringUUID, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    auth_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    salt: Mapped[str] = mapped_column(String(255), nullable=False)
    reset_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reset_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    secrets: Mapped[list["Secret"]] = relationship(back_populates="user", cascade="all, delete-orphan")
