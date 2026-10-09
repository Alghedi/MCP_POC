from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    AUTH_SERVICE_URL: str = "http://127.0.0.1:8001"
    MCP_HOST: str = "0.0.0.0"
    MCP_PORT: int = 8000
    AUTH_VALIDATE_TIMEOUT_SECONDS: float = 5.0

    # Used by client.py to authenticate against auth_service
    MCP_SERVER_URL: str = "http://127.0.0.1:8000/mcp"
    MCP_CLIENT_EMAIL: str = ""
    MCP_CLIENT_PASSWORD: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
