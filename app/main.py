"""Punto de entrada de la aplicación FastAPI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.routers import auth, secrets

limiter = Limiter(key_func=get_remote_address)

DESCRIPTION = """
## Secretly API — Gestor de secretos cifrados en el cliente

API RESTful para almacenar y gestionar secretos (tokens, credenciales, claves SSH, etc.)
cifrados **end-to-end** en el cliente. El servidor nunca tiene acceso al contenido en texto plano.

### Características principales

- **Autenticación JWT** con access y refresh tokens.
- **Cifrado client-side**: los secretos se almacenan como blobs cifrados con un IV único.
- **Salt por usuario**: permite derivar claves de cifrado en el cliente sin exponer la contraseña.
- **Reset de contraseña**: flujo seguro con token de un solo uso y expiración.

### Flujo típico

1. Registrar un usuario (`POST /api/auth/register`) enviando email, contraseña y salt.
2. Iniciar sesión (`POST /api/auth/login`) para obtener tokens JWT y el salt.
3. Usar el `access_token` como Bearer en las peticiones a `/api/secrets`.
4. Crear, leer, actualizar y eliminar secretos cifrados en el vault.
"""

TAGS_METADATA = [
    {
        "name": "auth",
        "description": "Registro, login, refresh de tokens y reset de contraseña.",
    },
    {
        "name": "secrets",
        "description": "CRUD del vault de secretos cifrados. Todos los endpoints requieren JWT Bearer.",
    },
    {
        "name": "health",
        "description": "Estado del servicio.",
    },
]

app = FastAPI(
    title="Secretly API",
    version="1.0.0",
    description=DESCRIPTION,
    openapi_tags=TAGS_METADATA,
    contact={
        "name": "Secretly Team",
    },
    license_info={
        "name": "MIT",
    },
    docs_url=None,
    redoc_url=None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(secrets.router)


@app.get("/api/health", tags=["health"])
def health():
    """Verifica que el servicio está activo y respondiendo."""
    return {"status": "ok"}


@app.get("/api/docs", include_in_schema=False)
async def scalar_docs():
    """Renderiza la documentación interactiva con Scalar."""
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=app.title,
    )
