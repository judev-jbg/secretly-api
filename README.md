# Secretly API

API RESTful Zero-Knowledge para gestionar secretos cifrados end-to-end. Utiliza cifrado AES-256-GCM con clave derivada mediante Argon2id — el servidor nunca accede al contenido en texto plano.

## Stack

- **FastAPI** + **Uvicorn**
- **PostgreSQL** + **SQLAlchemy**
- **JWT** (python-jose) + **bcrypt** (passlib)
- **Scalar** para documentación interactiva OpenAPI

## Inicio rápido

```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus valores

# Ejecutar servidor
uvicorn app.main:app --host 0.0.0.0 --port 8100
```

### Con PM2

```bash
pm2 start ecosystem.config.js
pm2 logs secretly-api
```

## Documentación

La documentación interactiva (Scalar) está disponible en:

```
http://localhost:8100/docs
```

## Endpoints

### Auth (`/auth`)

| Método | Ruta                  | Descripción                       |
|--------|-----------------------|-----------------------------------|
| POST   | `/auth/register`      | Registrar usuario                 |
| POST   | `/auth/login`         | Iniciar sesión (retorna JWT)      |
| POST   | `/auth/refresh`       | Refrescar access token            |
| POST   | `/auth/forgot-password` | Solicitar reset de contraseña   |
| POST   | `/auth/reset-password`  | Aplicar reset de contraseña     |

### Secrets (`/secrets`) — requiere Bearer token

| Método | Ruta                  | Descripción                       |
|--------|-----------------------|-----------------------------------|
| GET    | `/secrets`            | Listar secretos (solo metadatos)  |
| GET    | `/secrets/{id}`       | Obtener secreto con blob cifrado  |
| POST   | `/secrets`            | Crear secreto                     |
| PUT    | `/secrets/{id}`       | Actualizar secreto                |
| DELETE | `/secrets/{id}`       | Eliminar secreto                  |

### Health

| Método | Ruta      | Descripción          |
|--------|-----------|----------------------|
| GET    | `/health` | Estado del servicio  |

## Tests

```bash
pytest tests/ -v
```

## Estructura

```
secretly-api/
├── app/
│   ├── core/
│   │   ├── config.py          ← variables de entorno (pydantic-settings)
│   │   ├── security.py        ← JWT, bcrypt, helpers de auth
│   │   └── database.py        ← conexión SQLAlchemy
│   ├── models/
│   │   ├── user.py            ← modelo User
│   │   └── secret.py          ← modelo Secret
│   ├── schemas/
│   │   ├── auth.py            ← schemas de autenticación
│   │   └── secret.py          ← schemas de secretos
│   ├── routers/
│   │   ├── auth.py            ← /auth/* endpoints
│   │   └── secrets.py         ← /secrets/* endpoints
│   ├── services/
│   │   ├── auth_service.py    ← lógica de auth
│   │   └── secret_service.py  ← CRUD de secretos
│   └── main.py                ← instancia FastAPI, middleware, docs
├── tests/
├── ecosystem.config.js        ← configuración PM2
├── .env.example
├── requirements.txt
└── README.md
```
