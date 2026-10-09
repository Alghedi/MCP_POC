from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    refresh_token_expiry,
    verify_password,
)
from app.dependencies import bearer_scheme, get_current_user, get_db
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.token import LoginRequest, RefreshRequest, Token, TokenValidationResponse
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_token_pair(user: User, db: Session) -> Token:
    access_token = create_access_token(subject=user.username)
    refresh_token = generate_refresh_token()
    db.add(
        RefreshToken(
            token_hash=hash_token(refresh_token),
            user_id=user.id,
            expires_at=refresh_token_expiry(),
        )
    )
    db.commit()
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)) -> User:
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Username already registered")
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")

    user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(credentials: LoginRequest, db: Session = Depends(get_db)) -> Token:
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Inactive user")

    return _issue_token_pair(user, db)


@router.post("/refresh", response_model=Token)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> Token:
    token_hash = hash_token(payload.refresh_token)
    stored = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    invalid_token_exception = HTTPException(
        status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token"
    )
    if stored is None or stored.revoked:
        raise invalid_token_exception
    if stored.expires_at < datetime.utcnow():
        raise invalid_token_exception

    user = db.query(User).filter(User.id == stored.user_id).first()
    if user is None or not user.is_active:
        raise invalid_token_exception

    # Rotate: revoke the used refresh token before issuing a new pair
    stored.revoked = True
    db.add(stored)
    db.commit()

    return _issue_token_pair(user, db)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshRequest, db: Session = Depends(get_db)) -> None:
    token_hash = hash_token(payload.refresh_token)
    stored = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if stored is not None and not stored.revoked:
        stored.revoked = True
        db.add(stored)
        db.commit()


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get("/validate", response_model=TokenValidationResponse)
def validate(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> TokenValidationResponse:
    invalid_token_exception = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        raise invalid_token_exception
    if payload.get("type") != "access":
        raise invalid_token_exception

    user = db.query(User).filter(User.username == payload.get("sub")).first()
    if user is None or not user.is_active:
        raise invalid_token_exception

    return TokenValidationResponse(
        valid=True,
        username=user.username,
        user_id=user.id,
        expires_at=datetime.utcfromtimestamp(payload["exp"]),
    )
