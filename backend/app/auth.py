import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, Response

from backend.app.db.database import sessions_collection, users_collection

SESSION_COOKIE_NAME = "session_id"
SESSION_TTL_DAYS = int(os.getenv("SESSION_TTL_DAYS", "7"))
COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "lax")
PBKDF2_ITERATIONS = int(os.getenv("PASSWORD_HASH_ITERATIONS", "390000"))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _pbkdf2_hash(password: str, salt: bytes, iterations: int) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return base64.b64encode(digest).decode("utf-8")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    salt_b64 = base64.b64encode(salt).decode("utf-8")
    digest_b64 = _pbkdf2_hash(password, salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt_b64}${digest_b64}"


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash or not password_hash.startswith("pbkdf2_sha256$"):
        return False

    try:
        _, iterations_raw, salt_b64, digest_b64 = password_hash.split("$", 3)
        iterations = int(iterations_raw)
        salt = base64.b64decode(salt_b64.encode("utf-8"))
    except (ValueError, TypeError):
        return False

    candidate_digest = _pbkdf2_hash(password, salt, iterations)
    return hmac.compare_digest(candidate_digest, digest_b64)


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
