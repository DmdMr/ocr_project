import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from bson import ObjectId
from dotenv import load_dotenv
from pathlib import Path
from fastapi import Cookie, Depends, HTTPException, Response
from passlib.context import CryptContext

from backend.app.db.database import sessions_collection, users_collection

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

SESSION_COOKIE_NAME = "session_id"
SESSION_TTL_DAYS = int(os.getenv("SESSION_TTL_DAYS", "7"))
COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "lax")
PASSWORD_HASH_SCHEME = os.getenv("PASSWORD_HASH_SCHEME", "pbkdf2_sha256")
PASSWORD_HASH_ROUNDS = int(os.getenv("PASSWORD_HASH_ROUNDS", "390000"))
BOOTSTRAP_ADMIN_USERNAME = os.getenv("BOOTSTRAP_ADMIN_USERNAME")
BOOTSTRAP_ADMIN_PASSWORD = os.getenv("BOOTSTRAP_ADMIN_PASSWORD")

print("ENV PATH:", env_path)
print("ADMIN USER:", os.getenv("BOOTSTRAP_ADMIN_USERNAME"))
print("ADMIN PASS:", os.getenv("BOOTSTRAP_ADMIN_PASSWORD"))

USER_ROLE_EDITOR = "editor"
USER_ROLE_ADMIN = "admin"
USER_ROLE_VIEWER = "viewer"
UserRole = Literal["viewer", "editor", "admin"]

PASSWORD_CONTEXT = CryptContext(
    schemes=[PASSWORD_HASH_SCHEME],
    deprecated="auto",
    pbkdf2_sha256__default_rounds=PASSWORD_HASH_ROUNDS,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    return PASSWORD_CONTEXT.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False

    try:
        return PASSWORD_CONTEXT.verify(password, password_hash)
    except Exception:
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
        "role": user.get("role", USER_ROLE_EDITOR),
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at"),
        "is_active": user.get("is_active", True),
    }


async def get_current_user(session_id: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE_NAME)):
    return await resolve_current_user(session_id)


async def require_current_user(current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return current_user


require_auth = require_current_user


def viewer_context():
    return {
        "id": None,
        "username": None,
        "role": USER_ROLE_VIEWER,
        "created_at": None,
        "updated_at": None,
        "is_active": True,
        "is_authenticated": False,
    }


async def get_auth_context(current_user=Depends(get_current_user)):
    if not current_user:
        return viewer_context()

    return {**current_user, "is_authenticated": True}


def require_role(*roles: UserRole):
    async def _require_role(current_user=Depends(require_current_user)):
        user_role = current_user.get("role", USER_ROLE_EDITOR)
        if user_role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

    return _require_role


require_admin_user = require_role(USER_ROLE_ADMIN)
require_editor_user = require_role(USER_ROLE_EDITOR, USER_ROLE_ADMIN)


async def bootstrap_first_admin():
    admin_exists = await users_collection.count_documents({"role": USER_ROLE_ADMIN}, limit=1)
    if admin_exists:
        return False

    if not BOOTSTRAP_ADMIN_USERNAME or not BOOTSTRAP_ADMIN_PASSWORD:
        return False

    username = BOOTSTRAP_ADMIN_USERNAME.strip()
    if not username:
        return False

    username_lower = username.lower()
    existing_user = await users_collection.find_one({"username_lower": username_lower}, {"_id": 1})
    if existing_user:
        return False

    now = utc_now()
    user_id = str(ObjectId())
    await users_collection.insert_one(
        {
            "_id": user_id,
            "username": username,
            "username_lower": username_lower,
            "password_hash": hash_password(BOOTSTRAP_ADMIN_PASSWORD),
            "role": USER_ROLE_ADMIN,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    return True


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
