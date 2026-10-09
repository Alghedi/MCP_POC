from datetime import datetime, timezone

import httpx
from fastmcp.server.auth.auth import AccessToken, TokenVerifier

from app.core.config import settings


class AuthServiceTokenVerifier(TokenVerifier):
    """Validates JWTs by delegating to auth_service's GET /auth/validate."""

    def __init__(self, base_url: str = settings.AUTH_SERVICE_URL, timeout: float = settings.AUTH_VALIDATE_TIMEOUT_SECONDS) -> None:
        super().__init__()
        self._validate_url = f"{base_url.rstrip('/')}/auth/validate"
        self._timeout = timeout

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    self._validate_url, headers={"Authorization": f"Bearer {token}"}
                )
        except httpx.HTTPError:
            # auth_service unreachable: fail closed, treat the token as invalid
            return None

        if response.status_code != 200:
            return None

        data = response.json()
        if not data.get("valid"):
            return None

        # auth_service returns naive UTC timestamps (no tzinfo)
        expires_at_naive = datetime.fromisoformat(data["expires_at"])
        expires_at = int(expires_at_naive.replace(tzinfo=timezone.utc).timestamp())
        return AccessToken(
            token=token,
            client_id=data["username"],
            scopes=[],
            expires_at=expires_at,
            subject=data["username"],
            claims={"user_id": data["user_id"], "username": data["username"]},
        )


token_verifier = AuthServiceTokenVerifier()
