"""Configuración centralizada de la aplicación vía variables de entorno.
Todos los valores se cargan desde .env — nunca hardcodear credenciales aquí.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Parámetros de configuración cargados desde .env."""

    # Base de datos (obligatorios — sin default para forzar configuración explícita)
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str

    # JWT
    secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Reset de contraseña
    reset_token_expire_minutes: int = 15

    # Email
    smtp_server: str = ""
    smtp_port: int = 587
    sender_email: str = ""
    sender_password: str = ""

    # CORS
    cors_origins: list[str] = [
        "http://localhost:8080", "http://localhost:5173"]

    # Servidor
    port: int = 8100

    @property
    def database_url(self) -> str:
        """URL de conexión a PostgreSQL."""
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
