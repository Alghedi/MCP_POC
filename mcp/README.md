# MCP Server

Servidor [MCP](https://modelcontextprotocol.io/) construido con [FastMCP](https://gofastmcp.com), gestionado con [uv](https://docs.astral.sh/uv/). La autenticación se delega completamente al servicio `auth_service`: cada request valida el JWT recibido llamando a su endpoint `GET /auth/validate`.

## Características

- Transporte `streamable-http`, expuesto en el puerto 8000
- Autenticación por token Bearer, validada contra `auth_service` (sin lógica de JWT propia, sin código compartido)
- Ruta pública `GET /health` para chequeos de infraestructura
- Aún sin tools de negocio registrados — se agregan con `@mcp.tool` en `app/main.py`

## Requisitos

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) instalado
- `auth_service` corriendo (por defecto en `http://127.0.0.1:8001`)

## Configuración

Copia `.env.example` a `.env` y ajusta los valores si es necesario:

```powershell
Copy-Item .env.example .env
```

Variables disponibles:

| Variable | Descripción | Default |
|---|---|---|
| `AUTH_SERVICE_URL` | URL base de auth_service | `http://127.0.0.1:8001` |
| `MCP_HOST` | Host de escucha del servidor MCP | `0.0.0.0` |
| `MCP_PORT` | Puerto de escucha del servidor MCP | `8000` |
| `AUTH_VALIDATE_TIMEOUT_SECONDS` | Timeout al llamar a `auth_service` para validar un token | `5` |
| `MCP_SERVER_URL` | URL del endpoint MCP usada por `client.py` | `http://127.0.0.1:8000/mcp` |
| `MCP_CLIENT_EMAIL` | Email usado por `client.py` para autenticarse contra auth_service | — |
| `MCP_CLIENT_PASSWORD` | Password usado por `client.py` para autenticarse contra auth_service | — |

## Instalación de dependencias

```powershell
uv sync
```

> Si tu red corporativa intercepta TLS y falla la descarga de paquetes, usa `uv sync --system-certs`.

## Arrancar el servicio

Con `auth_service` corriendo en el puerto 8001:

```powershell
uv run python -m app.main
```

El servidor MCP queda disponible en `http://127.0.0.1:8000/mcp` (endpoint MCP) y `http://127.0.0.1:8000/health` (chequeo de salud, sin autenticación).

También puedes usar el CLI de FastMCP, en modo módulo (`--module`) para que las importaciones de `app.*` resuelvan correctamente — el transporte y puerto los define el propio `app/main.py`:

```powershell
uv run fastmcp run app.main --module
```

> Evita `uv run fastmcp run app/main.py ...`: FastMCP agrega al `sys.path` solo la carpeta del archivo (`app/`), no la raíz del proyecto, por lo que `from app.core...` falla con `ModuleNotFoundError: No module named 'app'`.

## Flujo de autenticación

1. Obtén un `access_token` autenticándote contra `auth_service`:

   ```powershell
   $login = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8001/auth/login" `
     -Body (@{email="user@example.com"; password="SuperSecret1"} | ConvertTo-Json) `
     -ContentType "application/json"
   ```

2. Usa ese token como header `Authorization: Bearer <access_token>` en cada conexión/request al servidor MCP. Con el cliente de FastMCP:

   ```python
   from fastmcp import Client

   async def main():
       async with Client(
           "http://127.0.0.1:8000/mcp",
           auth=login_access_token,  # el access_token obtenido de auth_service
       ) as client:
           tools = await client.list_tools()
           print(tools)
   ```

3. Internamente, el servidor MCP toma ese header y llama a `GET {AUTH_SERVICE_URL}/auth/validate` con el mismo Bearer token. Si auth_service responde `valid: true`, la request se procesa; en cualquier otro caso (token inválido, expirado, revocado, o auth_service inalcanzable) se rechaza con `401 Unauthorized`.

## Agregar tools de negocio

Los tools se registran en `app/main.py` (o en módulos que importes desde ahí) usando el decorador de FastMCP:

```python
@mcp.tool
def mi_tool(parametro: str) -> str:
    return f"Procesado: {parametro}"
```

Dentro de un tool, la identidad del usuario autenticado (poblada por `AuthServiceTokenVerifier`) está disponible vía el contexto de FastMCP, con `user_id` y `username` en los claims del access token.

## Cliente de ejemplo (`client.py`)

Script de línea de comandos que se autentica contra `auth_service` (usando `MCP_CLIENT_EMAIL`/`MCP_CLIENT_PASSWORD` de `.env`), se conecta al servidor MCP con el `access_token` obtenido, y llama al tool `get_exchange_rate`.

1. Registra el usuario cliente en auth_service (una sola vez) y configura `MCP_CLIENT_EMAIL`/`MCP_CLIENT_PASSWORD` en `.env` con esas credenciales.
2. Con `auth_service` (puerto 8001) y el servidor MCP (puerto 8000) corriendo, ejecuta:

   ```powershell
   uv run python client.py --from USD --to EUR --date latest
   ```

   Los tres argumentos son opcionales (`--from USD --to EUR --date latest` son los valores por defecto).


## Estructura del proyecto

```
mcp/
  app/
    core/
      config.py   # configuración (Settings): AUTH_SERVICE_URL, MCP_HOST, MCP_PORT
      auth.py     # AuthServiceTokenVerifier: valida tokens llamando a auth_service
    main.py        # instancia FastMCP, ruta /health, arranque en puerto 8000
  pyproject.toml
  .env.example
```
