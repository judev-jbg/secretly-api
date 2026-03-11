```
secretly-api/
│
├── app/
│   ├── __init__.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py          ← variables de entorno (Settings con pydantic)
│   │   ├── security.py        ← JWT, bcrypt, helpers de auth
│   │   └── database.py        ← conexión SQLAlchemy + sesión
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py            ← modelo SQLAlchemy User
│   │   └── secret.py          ← modelo SQLAlchemy Secret
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py            ← LoginRequest, TokenResponse, ResetRequest...
│   │   └── secret.py          ← SecretCreate, SecretResponse, SecretList...
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py            ← /auth/* endpoints
│   │   └── secrets.py         ← /secrets/* endpoints
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py    ← lógica de login, reset, tokens
│   │   └── secret_service.py  ← CRUD de secretos
│   │
│   └── main.py                ← instancia FastAPI, registra routers, CORS
│
├── tests/
│   ├── __init__.py
│   ├── test_auth.py
│   └── test_secrets.py
│
├── .env                        ← variables locales (no commitear)
├── .env.example                ← plantilla con claves vacías (sí commitear)
├── requirements.txt
└── README.md
```
