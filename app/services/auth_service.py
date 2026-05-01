import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
)
from app.models.user import User
from app.models.auth import RefreshToken


def login_user(db: Session, email: str, password: str) -> dict:
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")

    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    role_name = user.role.name

    access_token = create_access_token(
        user_id=user.user_id,
        email=user.email,
        role=role_name,
    )

    refresh_token, expires_at = create_refresh_token(
        user_id=user.user_id,
        email=user.email,
        role=role_name,
    )

    db_refresh_token = RefreshToken(
        token_id=str(uuid.uuid4()),
        user_id=user.user_id,
        token_hash=hash_token(refresh_token),
        is_revoked=False,
        expires_at=expires_at,
    )

    db.add(db_refresh_token)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


def refresh_access_token(db: Session, refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    token_hash = hash_token(refresh_token)

    stored_token = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash)
        .first()
    )

    if not stored_token:
        raise HTTPException(status_code=401, detail="Refresh token not found")

    if stored_token.is_revoked:
        raise HTTPException(status_code=401, detail="Refresh token revoked")

    expires_at = stored_token.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = db.query(User).filter(User.user_id == payload["user_id"]).first()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not available")

    access_token = create_access_token(
        user_id=user.user_id,
        email=user.email,
        role=user.role.name,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


def logout_user(db: Session, refresh_token: str) -> dict:
    token_hash = hash_token(refresh_token)

    stored_token = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash)
        .first()
    )

    if not stored_token:
        raise HTTPException(status_code=401, detail="Refresh token not found")

    stored_token.is_revoked = True
    db.commit()

    return {"message": "Logged out successfully"}