"""Importa todos los modelos para que SQLAlchemy los registre al crear las tablas."""
from app.models.user import User  # noqa: F401
from app.models.secret import Secret  # noqa: F401
