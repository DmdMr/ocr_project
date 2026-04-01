import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, Response
from passlib.context import CryptContext
from passlib.exc import UnknownHashError

from backend.app.config import settings
from backend.app.db.database import sessions_collection, users_collection

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
MAX_BCRYPT_PASSWORD_BYTES = 72

SESSION_COOKIE_NAME = "session_id"
SESSION_TTL_DAYS = int(os.getenv("SESSION_TTL_DAYS", "7"))
COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "true" if settings.is_production else "false").lower() == "true"
COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "lax")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def password_exceeds_bcrypt_limit(password: str) -> bool:
    return len(password.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return pwd_context.verify(password, password_hash)
    except (UnknownHashError, ValueError):
        return False


async def create_session(user_id: str):
    session_id = secrets.token_urlsafe(48)
    now = utc_now()
    expires_at = now + timedelta(days=SESSION_TTL_DAYS)
    await sessions_collection.insert_one(
        {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": now,
            "expires_at": expires_at,
        }
    )
    return session_id, expires_at


async def resolve_current_user(session_id: Optional[str]):
    if not session_id:
        return None

    session = await sessions_collection.find_one(
        {"session_id": session_id, "expires_at": {"$gt": utc_now()}},
    )
    if not session:
        return None

    user = await users_collection.find_one({"_id": session["user_id"], "is_active": True})
    if not user:
        await sessions_collection.delete_one({"session_id": session_id})
        return None

    return {
        "id": user["_id"],
        "username": user["username"],
        "created_at": user.get("created_at"),
        "is_active": user.get("is_active", True),
    }


async def get_current_user(session_id: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE_NAME)):
    return await resolve_current_user(session_id)


async def require_current_user(current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return current_user


def set_session_cookie(response: Response, session_id: str, expires_at: datetime):
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        expires=expires_at,
        path="/",
    )


def clear_session_cookie(response: Response):
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
    )
