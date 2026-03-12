"""Configuración de la conexión a la base de datos con SQLAlchemy."""

from sqlalchemy import create_engine, String, TypeDecorator
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings


class StringUUID(TypeDecorator):
    """Almacena UUIDs como String(36) y garantiza que Python siempre reciba str."""

    impl = String(36)
    cache_ok = True

    def process_result_value(self, value, dialect):
        """Convierte a str si PostgreSQL retorna un objeto UUID nativo."""
        if value is not None:
            return str(value)
        return value


engine = create_engine(settings.database_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Clase base para todos los modelos ORM."""
    pass


def get_db():
    """
    Dependency de FastAPI que provee una sesión de DB por request.
    Cierra la sesión automáticamente al finalizar.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
