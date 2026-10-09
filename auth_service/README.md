# Auth Service

Servicio de autenticación JWT construido con FastAPI, SQLAlchemy y SQLite, gestionado con [uv](https://docs.astral.sh/uv/).

## Características

- Registro y login de usuarios con password hasheado (bcrypt)
- Access token JWT (expira en 1 hora)
- Refresh token persistido en SQLite, con rotación en cada uso y revocación en logout
- Endpoint protegido de ejemplo (`/auth/me`)
- Migraciones de base de datos con Alembic

## Requisitos

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) instalado

## Configuración

Copia `.env.example` a `.env` y ajusta los valores (especialmente `SECRET_KEY` en un entorno real):

```powershell
Copy-Item .env.example .env
```

Variables disponibles:

| Variable | Descripción | Default |
|---|---|---|
| `SECRET_KEY` | Clave usada para firmar los JWT | — |
| `ALGORITHM` | Algoritmo de firma JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duración del access token | `60` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Duración del refresh token | `1` |
| `DATABASE_URL` | URL de conexión SQLAlchemy | `sqlite:///./auth.db` |
| `PORT` | Puerto de escucha del servicio | `8001` |

## Instalación de dependencias

```powershell
uv sync
```

> Si tu red corporativa intercepta TLS y falla la descarga de paquetes, usa `uv sync --system-certs`.

## Migraciones de base de datos

Aplicar las migraciones (crea `auth.db` y sus tablas):

```powershell
uv run alembic upgrade head
```

Generar una nueva migración después de modificar los modelos:

```powershell
uv run alembic revision --autogenerate -m "descripción del cambio"
uv run alembic upgrade head
```

## Arrancar el servicio

```powershell
uv run uvicorn app.main:app --port 8001
```

Con recarga automática en desarrollo:

```powershell
uv run uvicorn app.main:app --port 8001 --reload
```

El servicio queda disponible en `http://127.0.0.1:8001`.

## Documentación OpenAPI

FastAPI expone la documentación interactiva automáticamente:

- Swagger UI: [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)
- Redoc: [http://127.0.0.1:8001/redoc](http://127.0.0.1:8001/redoc)
- Esquema OpenAPI (JSON): [http://127.0.0.1:8001/openapi.json](http://127.0.0.1:8001/openapi.json)

## Endpoints

Todos los endpoints de autenticación están bajo el prefijo `/auth`.

| Método | Ruta | Descripción | Body / Auth |
|---|---|---|---|
| `POST` | `/auth/register` | Registra un nuevo usuario | JSON: `username`, `email`, `password` |
| `POST` | `/auth/login` | Autentica y emite un par de tokens | JSON: `email`, `password` |
| `POST` | `/auth/refresh` | Rota el refresh token y emite un nuevo par | JSON: `refresh_token` |
| `POST` | `/auth/logout` | Revoca un refresh token | JSON: `refresh_token` |
| `GET` | `/auth/me` | Devuelve el usuario autenticado | Header `Authorization: Bearer <access_token>` |
| `GET` | `/auth/validate` | Valida un access token y devuelve sus claims | Header `Authorization: Bearer <access_token>` |
| `GET` | `/health` | Chequeo de salud del servicio | — |

> En Swagger UI, el candado "Authorize" usa el esquema `HTTPBearer`: pega directamente el `access_token` obtenido de `/auth/login`.

### Ejemplo de flujo

```powershell
# Registro
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8001/auth/register" `
  -Body (@{username="alice"; email="alice@example.com"; password="SuperSecret1"} | ConvertTo-Json) `
  -ContentType "application/json"

# Login (devuelve access_token y refresh_token)
$login = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8001/auth/login" `
  -Body (@{email="alice@example.com"; password="SuperSecret1"} | ConvertTo-Json) `
  -ContentType "application/json"

# Endpoint protegido
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8001/auth/me" `
  -Headers @{Authorization = "Bearer $($login.access_token)"}

# Validar el access token
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8001/auth/validate" `
  -Headers @{Authorization = "Bearer $($login.access_token)"}

# Refresh (rota el refresh token)
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8001/auth/refresh" `
  -Body (@{refresh_token=$login.refresh_token} | ConvertTo-Json) `
  -ContentType "application/json"

# Logout (revoca el refresh token)
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8001/auth/logout" `
  -Body (@{refresh_token=$login.refresh_token} | ConvertTo-Json) `
  -ContentType "application/json"
```

## Estructura del proyecto

```
auth_service/
  app/
    core/        # configuración (Settings) y seguridad (hashing, JWT)
    db/          # engine, sesión y Base declarativa de SQLAlchemy
    models/      # User, RefreshToken
    schemas/     # esquemas Pydantic (request/response)
    routers/     # endpoints de /auth
    dependencies.py
    main.py      # entrypoint de FastAPI
  alembic/       # migraciones de base de datos
  pyproject.toml
  .env.example
```
