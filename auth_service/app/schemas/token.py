from datetime import datetime

from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenValidationResponse(BaseModel):
    valid: bool
    username: str
    user_id: int
    expires_at: datetime
