import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, Cookie, Depends, File, Form, HTTPException, Request, Response, UploadFile
from PIL import Image, ImageOps
from pydantic import BaseModel, Field

from backend.app.auth import (
    USER_ROLE_ADMIN,
    USER_ROLE_EDITOR,
    clear_session_cookie,
    create_session,
    get_auth_context,
    get_current_user,
    hash_password,
    require_admin_user,
    require_editor_user,
    set_session_cookie,
    verify_password,
)
from backend.app.db.database import (
    activity_logs_collection,
    app_settings_collection,
    documents_collection,
    folders_collection,
    sessions_collection,
    tags_collection,
    users_collection,
)
from backend.app.services.archive_service import cleanup_expired_archived_documents, permanently_delete_document
from backend.app.services.folder_service import UNSORTED_FOLDER_NAME, ensure_unsorted_folder
from backend.app.services.ocr_service import recognize_text
from backend.app.utils.image_preprocessing import autocrop_whitespace

router = APIRouter(prefix="/api")

UPLOAD_DIR = "backend/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
AUDIT_LOG_DIR = "backend/logs"
AUDIT_LOG_FILE = os.path.join(AUDIT_LOG_DIR, "audit.log")
os.makedirs(AUDIT_LOG_DIR, exist_ok=True)


audit_logger = logging.getLogger("backend.audit")
if not audit_logger.handlers:
    audit_logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(AUDIT_LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    audit_logger.addHandler(file_handler)
    audit_logger.propagate = False

def calculate_file_hash(file_bytes: bytes):
    return hashlib.md5(file_bytes).hexdigest()


YEKATERINBURG_TZ = timezone(timedelta(hours=5))


def now_yekaterinburg():
    return datetime.now(YEKATERINBURG_TZ)


SETTINGS_DOCUMENT_ID = "main"
ALLOWED_CUSTOM_FIELD_TYPES = {"text", "number", "people"}


def normalize_custom_field_name(name: str):
    return (name or "").strip().lower()


def default_value_for_field_type(field_type: str):
    if field_type == "people":
        return []
    return None


async def get_or_create_settings():
    settings_doc = await app_settings_collection.find_one({"_id": SETTINGS_DOCUMENT_ID})
    if settings_doc:
        if not isinstance(settings_doc.get("fields_for_cards"), list):
            await app_settings_collection.update_one(
                {"_id": SETTINGS_DOCUMENT_ID},
                {"$set": {"fields_for_cards": []}},
            )
            settings_doc["fields_for_cards"] = []
        return settings_doc

    settings_doc = {"_id": SETTINGS_DOCUMENT_ID, "fields_for_cards": []}
    await app_settings_collection.insert_one(settings_doc)
    return settings_doc


def object_id_or_404(doc_id: str):
    try:
        return ObjectId(doc_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Документ не найден") from exc
    

def build_folder_id_candidates(folder_id: str):
    normalized = (folder_id or "").strip()
    if not normalized:
        return []
    candidates = [normalized]
    if ObjectId.is_valid(normalized):
        candidates.insert(0, ObjectId(normalized))
    return candidates


async def find_folder_by_public_id(folder_id: str):
    candidates = build_folder_id_candidates(folder_id)
    if not candidates:
        raise HTTPException(status_code=400, detail="Некорректный идентификатор папки")
    folder = await folders_collection.find_one({"_id": {"$in": candidates}})
    if not folder:
        raise HTTPException(status_code=404, detail="Папка не найдена")
    return folder


async def resolve_folder_id_or_unsorted(folder_id: Optional[str]):
    unsorted_id = await ensure_unsorted_folder(folders_collection)
    if folder_id is None or not str(folder_id).strip():
        return unsorted_id

    folder = await find_folder_by_public_id(folder_id)
    return folder["_id"]


def serialize_folder(folder: dict):
    return {
        "id": str(folder["_id"]),
        "name": folder.get("name", ""),
        "parent_id": str(folder["parent_id"]) if folder.get("parent_id") else None,
        "is_system": bool(folder.get("is_system", False)),
        "created_at": folder.get("created_at"),
        "updated_at": folder.get("updated_at"),
        "created_by_user_id": folder.get("created_by_user_id"),
        "created_by_username": folder.get("created_by_username"),
    }


async def build_folder_path(folder_id: ObjectId):
    chain = []
    current_id = folder_id
    visited = set()
    while current_id:
        if current_id in visited:
            raise HTTPException(status_code=400, detail="Обнаружен цикл в структуре папок")
        visited.add(current_id)
        folder = await folders_collection.find_one({"_id": current_id})
        if not folder:
            break
        chain.append({"id": str(folder["_id"]), "name": folder.get("name", "")})
        current_id = folder.get("parent_id")
    chain.reverse()
    return chain


async def is_descendant_folder(candidate_parent_id: ObjectId, folder_id: ObjectId):
    current_id = candidate_parent_id
    visited = set()
    while current_id:
        if current_id in visited:
            return True
        visited.add(current_id)
        if current_id == folder_id:
            return True
        parent = await folders_collection.find_one({"_id": current_id}, {"parent_id": 1})
        if not parent:
            return False
        current_id = parent.get("parent_id")
    return False


def build_gallery_item(
    *,
    filename: str,
    path: str,
    file_hash: str,
    ocr_text: str,
    boxes: list,
    top_code: Optional[str] = None,
    ocr_lines: Optional[list] = None,
):
    return {
        "filename": filename,
        "path": path,
        "file_hash": file_hash,
        "recognized_text": ocr_text,
        "boxes": boxes,
        "top_code": top_code,
        "ocr_lines": ocr_lines or [],
        "created_at": now_yekaterinburg(),
        "image_version": now_yekaterinburg().isoformat(),
    }


def build_attachment_item(*, filename: str, path: str, original_name: str, content_type: str, size: int):
    return {
        "filename": filename,
        "path": path,
        "original_name": original_name,
        "content_type": content_type,
        "size": size,
        "created_at": now_yekaterinburg(),
    }


def normalize_document(doc: dict):
    doc["_id"] = str(doc["_id"])
    if doc.get("folder_id") is not None and not isinstance(doc.get("folder_id"), str):
        doc["folder_id"] = str(doc["folder_id"])
    if doc.get("is_archived") is None:
        doc["is_archived"] = False
    if "archived_at" not in doc:
        doc["archived_at"] = None
    if "top_code" not in doc:
        doc["top_code"] = None
    if not isinstance(doc.get("ocr_lines"), list):
        doc["ocr_lines"] = []
    gallery = doc.get("gallery_images")
    if not gallery:
        doc["gallery_images"] = [
            {
                "filename": doc.get("filename"),
                "path": doc.get("path"),
                "file_hash": doc.get("file_hash"),
                "recognized_text": doc.get("recognized_text", ""),
                "boxes": doc.get("boxes", []),
                "top_code": doc.get("top_code"),
                "ocr_lines": doc.get("ocr_lines", []),
                "created_at": doc.get("created_at", now_yekaterinburg()),
                "image_version": doc.get("image_version"),
            }
        ]
    if doc.get("attachments") is None:
        doc["attachments"] = []
    if not isinstance(doc.get("custom_fields"), dict):
        doc["custom_fields"] = {}
    return doc


def save_upload_file(file: UploadFile, file_bytes: bytes):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as destination:
        destination.write(file_bytes)
    return filename, file_path


def normalize_display_filename(raw_name: str, original_filename: str):
    trimmed = (raw_name or "").strip()
    if not trimmed:
        raise HTTPException(status_code=400, detail="Имя файла не может быть пустым")

    original_suffix = Path(original_filename).suffix
    if not original_suffix:
        return trimmed

    candidate_suffix = Path(trimmed).suffix
    if candidate_suffix.lower() == original_suffix.lower():
        stem = Path(trimmed).stem.strip()
    else:
        stem = trimmed[: -len(candidate_suffix)].strip() if candidate_suffix else trimmed

    if not stem:
        raise HTTPException(status_code=400, detail="Имя файла не может быть пустым")

    return f"{stem}{original_suffix}"


def get_request_actor(request: Request):
    forwarded_for = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    client_host = request.client.host if request.client else None
    ip_address = forwarded_for or client_host or "unknown"

    return {
        "ip": ip_address,
        "device_name": request.headers.get("x-device-name") or "unknown",
        "user_agent": request.headers.get("user-agent") or "unknown",
    }

from datetime import datetime, date
from bson import ObjectId

async def write_audit_log(request: Request, action: str, payload: dict, current_user: Optional[dict] = None):
    actor = get_request_actor(request)
    if current_user:
        actor["user_id"] = current_user.get("id")
        actor["username"] = current_user.get("username")
        actor["role"] = current_user.get("role")

    created_at = datetime.now(timezone.utc)

    entry = {
        "timestamp": now_yekaterinburg().isoformat(),
        "created_at": created_at,
        "action": action,
        "actor": actor,
        "payload": payload,
    }

    await activity_logs_collection.insert_one(entry)

    log_entry = {
        **entry,
        "created_at": created_at.isoformat(),
    }

    audit_logger.info(json.dumps(log_entry, ensure_ascii=False, default=str))

class AuthCredentials(BaseModel):
    username: str
    password: str


class CreateUserPayload(AuthCredentials):
    role: str = USER_ROLE_EDITOR
    is_active: bool = True


class UserUpdatePayload(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserPasswordUpdatePayload(BaseModel):
    new_password: str


def serialize_user(user: dict):
    return {
        "id": user["_id"],
        "username": user["username"],
        "role": user.get("role", USER_ROLE_EDITOR),
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at"),
        "is_active": user.get("is_active", True),
    }


def serialize_activity_log(log: dict):
    return {
        "id": str(log.get("_id")),
        "timestamp": log.get("timestamp"),
        "created_at": log.get("created_at"),
        "action": log.get("action"),
        "actor": log.get("actor", {}),
        "payload": log.get("payload", {}),
    }


@router.post("/auth/register")
async def register(
    request: Request,
    payload: CreateUserPayload,
    current_user=Depends(require_admin_user),
):
    username = (payload.username or "").strip()
    password = payload.password or ""
    role = (payload.role or USER_ROLE_EDITOR).strip().lower()

    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Имя пользователя должно содержать минимум 3 символа")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Пароль должен содержать минимум 6 символов")
    if role not in {USER_ROLE_EDITOR, USER_ROLE_ADMIN}:
        raise HTTPException(status_code=400, detail="Недопустимая роль пользователя")

    username_lower = username.lower()
    existing_user = await users_collection.find_one({"username_lower": username_lower})
    if existing_user:
        raise HTTPException(status_code=400, detail="Пользователь с таким именем уже существует")

    now = datetime.now(timezone.utc)
    user_id = str(ObjectId())
    await users_collection.insert_one(
        {
            "_id": user_id,
            "username": username,
            "username_lower": username_lower,
            "password_hash": hash_password(password),
            "role": role,
            "created_at": now,
            "updated_at": now,
            "is_active": bool(payload.is_active),
        }
    )
    created_user = {
        "id": user_id,
        "username": username,
        "role": role,
        "created_at": now,
        "updated_at": now,
        "is_active": bool(payload.is_active),
    }
    await write_audit_log(
        request,
        "user.create",
        {"user_id": user_id, "username": username, "role": role, "is_active": bool(payload.is_active)},
        current_user=current_user,
    )

    return {**created_user, "created_by": current_user["id"]}


@router.post("/auth/login")
async def login(request: Request, payload: AuthCredentials, response: Response):
    username = (payload.username or "").strip()
    password = payload.password or ""
    username_lower = username.lower()

    user = await users_collection.find_one({"username_lower": username_lower})
    if not user or not verify_password(password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Пользователь деактивирован")

    role = user.get("role", USER_ROLE_EDITOR)
    if role not in {USER_ROLE_EDITOR, USER_ROLE_ADMIN}:
        role = USER_ROLE_EDITOR
        await users_collection.update_one(
            {"_id": user["_id"]},
            {"$set": {"role": role, "updated_at": datetime.now(timezone.utc)}},
        )

    session_id, expires_at = await create_session(user["_id"])
    set_session_cookie(response, session_id, expires_at)
    auth_user = serialize_user({**user, "role": role})
    await write_audit_log(
        request,
        "auth.login",
        {"user_id": auth_user["id"], "username": auth_user["username"], "role": auth_user["role"]},
        current_user=auth_user,
    )
    return auth_user


@router.post("/auth/logout")
async def logout(response: Response, current_user=Depends(get_current_user), session_id: Optional[str] = Cookie(default=None, alias="session_id")):
    if session_id:
        await sessions_collection.delete_one({"session_id": session_id})
    clear_session_cookie(response)
    return {"message": "Logged out"}


@router.get("/auth/me")
async def me(auth_context=Depends(get_auth_context)):
    return auth_context


@router.get("/users")
async def list_users(current_user=Depends(require_admin_user)):
    users = []
    async for user in users_collection.find({}, {"password_hash": 0}).sort("created_at", -1):
        users.append(serialize_user(user))
    return {"users": users}


@router.post("/users")
async def create_user(request: Request, payload: CreateUserPayload, current_user=Depends(require_admin_user)):
    return await register(request=request, payload=payload, current_user=current_user)


@router.patch("/users/{user_id}")
async def update_user(request: Request, user_id: str, payload: UserUpdatePayload, current_user=Depends(require_admin_user)):
    user = await users_collection.find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    update_data = {}
    if payload.username is not None:
        username = payload.username.strip()
        if len(username) < 3:
            raise HTTPException(status_code=400, detail="Имя пользователя должно содержать минимум 3 символа")
        username_lower = username.lower()
        existing = await users_collection.find_one({"username_lower": username_lower, "_id": {"$ne": user_id}})
        if existing:
            raise HTTPException(status_code=400, detail="Пользователь с таким именем уже существует")
        update_data["username"] = username
        update_data["username_lower"] = username_lower

    if payload.role is not None:
        role = payload.role.strip().lower()
        if role not in {USER_ROLE_EDITOR, USER_ROLE_ADMIN}:
            raise HTTPException(status_code=400, detail="Недопустимая роль пользователя")
        if user.get("role") == USER_ROLE_ADMIN and role != USER_ROLE_ADMIN:
            other_admin_exists = await users_collection.count_documents(
                {"role": USER_ROLE_ADMIN, "is_active": True, "_id": {"$ne": user_id}},
                limit=1,
            )
            if not other_admin_exists:
                raise HTTPException(status_code=400, detail="Нельзя убрать роль последнего активного администратора")
        update_data["role"] = role

    if payload.is_active is not None:
        if user.get("role") == USER_ROLE_ADMIN and not payload.is_active:
            other_admin_exists = await users_collection.count_documents(
                {"role": USER_ROLE_ADMIN, "is_active": True, "_id": {"$ne": user_id}},
                limit=1,
            )
            if not other_admin_exists:
                raise HTTPException(status_code=400, detail="Нельзя деактивировать последнего активного администратора")
        update_data["is_active"] = bool(payload.is_active)

    if not update_data:
        raise HTTPException(status_code=400, detail="Нет полей для обновления")

    update_data["updated_at"] = datetime.now(timezone.utc)
    await users_collection.update_one({"_id": user_id}, {"$set": update_data})
    updated_user = await users_collection.find_one({"_id": user_id}, {"password_hash": 0})
    if not updated_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    await write_audit_log(
        request,
        "user.update",
        {"user_id": user_id, "updated_fields": sorted(update_data.keys())},
        current_user=current_user,
    )
    if "role" in update_data:
        await write_audit_log(
            request,
            "user.role.change",
            {"user_id": user_id, "new_role": update_data["role"]},
            current_user=current_user,
        )
    if "is_active" in update_data:
        await write_audit_log(
            request,
            "user.activate" if update_data["is_active"] else "user.deactivate",
            {"user_id": user_id, "is_active": update_data["is_active"]},
            current_user=current_user,
        )
    return serialize_user(updated_user)


@router.patch("/users/{user_id}/password")
async def reset_user_password(
    request: Request,
    user_id: str,
    payload: UserPasswordUpdatePayload,
    current_user=Depends(require_admin_user),
):
    user = await users_collection.find_one({"_id": user_id}, {"_id": 1, "username": 1})
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    new_password = payload.new_password or ""
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Пароль должен содержать минимум 6 символов")

    await users_collection.update_one(
        {"_id": user_id},
        {"$set": {"password_hash": hash_password(new_password), "updated_at": datetime.now(timezone.utc)}},
    )

    await sessions_collection.delete_many({"user_id": user_id})
    await write_audit_log(
        request,
        "user.password.reset",
        {"user_id": user_id, "username": user.get("username")},
        current_user=current_user,
    )
    return {"message": "Пароль обновлён"}


@router.get("/activity-logs")
async def get_activity_logs(
    limit: int = 100,
    current_user=Depends(require_admin_user),
):
    safe_limit = max(1, min(limit, 500))
    logs = []
    async for entry in activity_logs_collection.find().sort("created_at", -1).limit(safe_limit):
        logs.append(serialize_activity_log(entry))
    return {"logs": logs, "count": len(logs)}


@router.post("/upload")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    perform_ocr: bool = Form(True),
    folder_id: Optional[str] = Form(None),
    current_user=Depends(require_editor_user),
):

    if file.content_type not in ["image/png", "image/jpeg", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Разрешены только PNG и JPG")

    file_bytes = await file.read()
    file_hash = calculate_file_hash(file_bytes)

    existing = await documents_collection.find_one({"file_hash": file_hash})
    if existing:
        return {"message": "Файл уже существует", "document": normalize_document(existing)}

    filename, file_path = save_upload_file(file, file_bytes)
    file_path = autocrop_whitespace(file_path)
    if perform_ocr:
        try:
            ocr_result = recognize_text(file_path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail="OCR failure") from exc
    else:
        ocr_result = {"text": "", "boxes": [], "top_code": None, "ocr_lines": []}

    gallery_item = build_gallery_item(
        filename=filename,
        path=file_path,
        file_hash=file_hash,
        ocr_text=ocr_result["text"],
        boxes=ocr_result["boxes"],
        top_code=ocr_result.get("top_code"),
        ocr_lines=ocr_result.get("ocr_lines", []),
    )

    settings_doc = await get_or_create_settings()
    resolved_folder_id = await resolve_folder_id_or_unsorted(folder_id)
    fields_for_cards = settings_doc.get("fields_for_cards") or []
    custom_fields = {
        normalize_custom_field_name(field.get("name", "")): default_value_for_field_type(field.get("type", "text"))
        for field in fields_for_cards
        if normalize_custom_field_name(field.get("name", ""))
    }

    document_data = {
        "filename": filename,
        "display_filename": file.filename.strip() or file.filename,
        "path": file_path,
        "recognized_text": ocr_result["text"],  
        "boxes": ocr_result["boxes"],         
        "top_code": ocr_result.get("top_code"),
        "ocr_lines": ocr_result.get("ocr_lines", []),
        "file_hash": file_hash,
        "created_at": now_yekaterinburg(),
        "folder_id": resolved_folder_id,
        "image_version": now_yekaterinburg().isoformat(),
        "tags": [],
        "is_archived": False,
        "archived_at": None,
        "gallery_images": [gallery_item],
        "attachments": [],
        "custom_fields": custom_fields,
        "created_by_user_id": current_user["id"],
        "created_by_username": current_user["username"],
        "updated_by_user_id": current_user["id"],
        "updated_by_username": current_user["username"],
    }


    result = await documents_collection.insert_one(document_data)
    document_data["_id"] = str(result.inserted_id)
    await write_audit_log(
        request,
        "document.upload",
        {
            "document_id": document_data["_id"],
            "filename": document_data["filename"],
            "perform_ocr": perform_ocr,
        },
        current_user=current_user,
    )

    return {
        "message": "Файл успешно загружен",
        "document": document_data,
        "filename": filename,
        "recognized_text": document_data.get("recognized_text", ""),
        "top_code": document_data.get("top_code"),
        "ocr_lines": document_data.get("ocr_lines", []),
    }

@router.post("/documents/{doc_id}/gallery")
async def upload_images_to_document(request: Request, doc_id: str, files: List[UploadFile] = File(...), current_user=Depends(require_editor_user)):
    object_id = object_id_or_404(doc_id)
    document = await documents_collection.find_one({"_id": object_id})
    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    if not files:
        raise HTTPException(status_code=400, detail="Требуется хотя бы один файл")

    gallery_items = document.get("gallery_images") or []
    existing_hashes = {item.get("file_hash") for item in gallery_items if item.get("file_hash")}

    added_items = []
    appended_texts: List[str] = []
    appended_codes: List[str] = []
    skipped_files: List[str] = []

    for file in files:
        if file.content_type not in ["image/png", "image/jpeg", "image/jpg"]:
            skipped_files.append(f"{file.filename}: неподдерживаемый тип файла")
            continue

        file_bytes = await file.read()
        if not file_bytes:
            skipped_files.append(f"{file.filename}: пустой файл")
            continue

        file_hash = calculate_file_hash(file_bytes)
        if file_hash in existing_hashes:
            skipped_files.append(f"{file.filename}: дубликат изображения")
            continue

        filename, file_path = save_upload_file(file, file_bytes)
        file_path = autocrop_whitespace(file_path)
        try:
            ocr_result = recognize_text(file_path)
        except ValueError:
            skipped_files.append(f"{file.filename}: некорректное изображение")
            continue
        except RuntimeError:
            skipped_files.append(f"{file.filename}: сервис OCR недоступен")
            continue
        except Exception:
            skipped_files.append(f"{file.filename}: ошибка OCR")
            continue

        item = build_gallery_item(
            filename=filename,
            path=file_path,
            file_hash=file_hash,
            ocr_text=ocr_result["text"],
            boxes=ocr_result["boxes"],
            top_code=ocr_result.get("top_code"),
            ocr_lines=ocr_result.get("ocr_lines", []),
        )
        added_items.append(item)
        existing_hashes.add(file_hash)

        recognized_text = (ocr_result.get("text") or "").strip()
        if recognized_text:
            appended_texts.append(recognized_text)
        top_code = (ocr_result.get("top_code") or "").strip()
        if top_code:
            appended_codes.append(top_code)

    if not added_items:
        detail = "Не загружено ни одного нового корректного изображения"
        if skipped_files:
            detail = f"{detail}. " + "; ".join(skipped_files)
        raise HTTPException(status_code=400, detail=detail)


    existing_text = (document.get("recognized_text") or "").strip()
    combined_text_parts = [part for part in [existing_text, *appended_texts] if part]
    combined_text = "\n\n".join(combined_text_parts)
    existing_top_code = (document.get("top_code") or "").strip()
    merged_top_code = existing_top_code or (appended_codes[0] if appended_codes else None)

    await documents_collection.update_one(
        {"_id": object_id},
        {
            "$push": {"gallery_images": {"$each": added_items}},
            "$set": {
                "recognized_text": combined_text,
                "top_code": merged_top_code,
                "updated_by_user_id": current_user["id"],
                "updated_by_username": current_user["username"],
            },
        },
    )

    updated_doc = await documents_collection.find_one({"_id": object_id})
    if not updated_doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    updated_doc = normalize_document(updated_doc)
    await write_audit_log(
        request,
        "document.gallery.upload",
        {"document_id": doc_id, "added_count": len(added_items), "skipped_files": skipped_files},
        current_user=current_user,
    )
    return {
        "message": "Галерея обновлена",
        "added_count": len(added_items),
        "skipped_files": skipped_files,
        "document": updated_doc,
    }


@router.post("/documents/{doc_id}/attachments")
async def upload_attachments_to_document(request: Request, doc_id: str, files: List[UploadFile] = File(...), current_user=Depends(require_editor_user)):
    object_id = object_id_or_404(doc_id)
    document = await documents_collection.find_one({"_id": object_id})
    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    if not files:
        raise HTTPException(status_code=400, detail="Требуется хотя бы один файл")

    attachments = document.get("attachments") or []
    existing_names = {item.get("original_name", "").strip().lower() for item in attachments}

    added_items = []
    skipped_files: List[str] = []

    for file in files:
        original_name = (file.filename or "").strip()
        if not original_name:
            skipped_files.append("Безымянный файл: пустое имя файла")
            continue

        if (file.content_type or "").startswith("image/"):
            skipped_files.append(f"{original_name}: изображения добавляются через галерею")
            continue

        file_bytes = await file.read()
        if not file_bytes:
            skipped_files.append(f"{original_name}: пустой файл")
            continue

        normalized_name = original_name.lower()
        if normalized_name in existing_names:
            skipped_files.append(f"{original_name}: такой файл уже прикреплён")
            continue

        filename, file_path = save_upload_file(file, file_bytes)
        attachment = build_attachment_item(
            filename=filename,
            path=file_path,
            original_name=original_name,
            content_type=file.content_type or "application/octet-stream",
            size=len(file_bytes),
        )
        added_items.append(attachment)
        existing_names.add(normalized_name)

    if not added_items:
        detail = "Не загружено ни одного нового файла"
        if skipped_files:
            detail = f"{detail}. " + "; ".join(skipped_files)
        raise HTTPException(status_code=400, detail=detail)

    await documents_collection.update_one(
        {"_id": object_id},
        {"$push": {"attachments": {"$each": added_items}}, "$set": {"updated_by_user_id": current_user["id"], "updated_by_username": current_user["username"]}},
    )

    updated_doc = await documents_collection.find_one({"_id": object_id})
    if not updated_doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    await write_audit_log(
        request,
        "document.attachment.upload",
        {"document_id": doc_id, "added_count": len(added_items), "skipped_files": skipped_files},
        current_user=current_user,
    )

    return {
        "message": "Файлы прикреплены",
        "added_count": len(added_items),
        "skipped_files": skipped_files,
        "document": normalize_document(updated_doc),
    }


@router.get("/documents")
async def get_documents():
    await cleanup_expired_archived_documents(documents_collection, UPLOAD_DIR, retention_days=30)
    documents = []
    query = {"$or": [{"is_archived": False}, {"is_archived": {"$exists": False}}]}
    async for doc in documents_collection.find(query).sort("created_at", -1):
        normalized = normalize_document(doc)
        documents.append(normalized)
    return documents

class CropRequest(BaseModel):
    x_percent: float = Field(0, ge=0, le=100)
    y_percent: float = Field(0, ge=0, le=100)
    width_percent: float = Field(100, ge=0.1, le=100)
    height_percent: float = Field(100, ge=0.1, le=100)


class ImageEditRequest(BaseModel):
    rotate_degrees: int = 0
    crop: Optional[CropRequest] = None
    image_filename: Optional[str] = None



from typing import Optional, List


class DocumentUpdate(BaseModel):
    recognized_text: Optional[str] = None
    tags: Optional[List[str]] = None
    display_filename: Optional[str] = None


class DocumentIdsRequest(BaseModel):
    ids: List[str] = Field(default_factory=list)


class CustomFieldDefinition(BaseModel):
    name: str
    type: str


class DocumentCustomFieldsUpdate(BaseModel):
    custom_fields: dict = Field(default_factory=dict)


class FolderCreatePayload(BaseModel):
    name: str
    parent_id: Optional[str] = None


class FolderUpdatePayload(BaseModel):
    name: str


class FolderMovePayload(BaseModel):
    target_parent_id: Optional[str] = None


class DocumentMovePayload(BaseModel):
    target_folder_id: str


@router.get("/settings")
async def get_settings():
    settings_doc = await get_or_create_settings()
    return {"fields_for_cards": settings_doc.get("fields_for_cards", [])}


@router.post("/settings/fields")
async def create_settings_field(request: Request, payload: CustomFieldDefinition, current_user=Depends(require_admin_user)):
    field_name = normalize_custom_field_name(payload.name)
    field_type = (payload.type or "").strip().lower()

    if not field_name:
        raise HTTPException(status_code=400, detail="Имя поля обязательно")
    if field_type not in ALLOWED_CUSTOM_FIELD_TYPES:
        raise HTTPException(status_code=400, detail="Неподдерживаемый тип поля")

    settings_doc = await get_or_create_settings()
    fields = settings_doc.get("fields_for_cards") or []
    if any(normalize_custom_field_name(item.get("name", "")) == field_name for item in fields):
        raise HTTPException(status_code=400, detail="Поле с таким именем уже существует")

    field_data = {"name": field_name, "type": field_type, "created_at": now_yekaterinburg()}
    await app_settings_collection.update_one(
        {"_id": SETTINGS_DOCUMENT_ID},
        {"$push": {"fields_for_cards": field_data}},
    )
    await documents_collection.update_many(
        {"custom_fields." + field_name: {"$exists": False}},
        {"$set": {"custom_fields." + field_name: default_value_for_field_type(field_type)}},
    )
    await write_audit_log(
        request,
        "settings.field.create",
        {"field_name": field_name, "field_type": field_type},
        current_user=current_user,
    )
    return {"message": "Поле добавлено", "field": field_data}


@router.delete("/settings/fields/{name}")
async def delete_settings_field(request: Request, name: str, current_user=Depends(require_admin_user)):
    field_name = normalize_custom_field_name(name)
    if not field_name:
        raise HTTPException(status_code=400, detail="Имя поля обязательно")

    settings_doc = await get_or_create_settings()
    fields = settings_doc.get("fields_for_cards") or []
    field_exists = any(normalize_custom_field_name(item.get("name", "")) == field_name for item in fields)
    if not field_exists:
        raise HTTPException(status_code=404, detail="Поле не найдено")

    await app_settings_collection.update_one(
        {"_id": SETTINGS_DOCUMENT_ID},
        {"$pull": {"fields_for_cards": {"name": field_name}}},
    )
    await write_audit_log(request, "settings.field.delete", {"field_name": field_name}, current_user=current_user)
    return {"message": "Поле удалено", "field_name": field_name}

@router.put("/documents/{doc_id}")
async def update_document(request: Request, doc_id: str, data: DocumentUpdate, current_user=Depends(require_editor_user)):
    object_id = object_id_or_404(doc_id)
    update_data = {key: value for key, value in data.model_dump().items() if value is not None}

    if "display_filename" in update_data:
        existing_doc = await documents_collection.find_one({"_id": object_id})
        if not existing_doc:
            raise HTTPException(status_code=404, detail="Документ не найден")

        update_data["display_filename"] = normalize_display_filename(
            update_data["display_filename"],
            existing_doc.get("filename") or existing_doc.get("display_filename") or "",
        )

    update_data["updated_by_user_id"] = current_user["id"]
    update_data["updated_by_username"] = current_user["username"]

    await documents_collection.update_one({"_id": object_id}, {"$set": update_data})

    updated_doc = await documents_collection.find_one({"_id": object_id})
    if not updated_doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    await write_audit_log(
        request,
        "document.update",
        {"document_id": doc_id, "updated_fields": sorted(update_data.keys())},
        current_user=current_user,
    )

    return normalize_document(updated_doc)


@router.patch("/documents/{doc_id}/fields")
async def update_document_custom_fields(request: Request, doc_id: str, payload: DocumentCustomFieldsUpdate, current_user=Depends(require_editor_user)):
    object_id = object_id_or_404(doc_id)
    existing_doc = await documents_collection.find_one({"_id": object_id})
    if not existing_doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    settings_doc = await get_or_create_settings()
    fields_for_cards = settings_doc.get("fields_for_cards") or []
    allowed_fields = {normalize_custom_field_name(field.get("name", "")): field.get("type", "text") for field in fields_for_cards}

    current_custom_fields = existing_doc.get("custom_fields") if isinstance(existing_doc.get("custom_fields"), dict) else {}
    merged_fields = dict(current_custom_fields)

    for field_name, field_type in allowed_fields.items():
        if field_name and field_name not in merged_fields:
            merged_fields[field_name] = default_value_for_field_type(field_type)

    for key, value in (payload.custom_fields or {}).items():
        normalized_key = normalize_custom_field_name(key)
        if not normalized_key or normalized_key not in allowed_fields:
            continue
        merged_fields[normalized_key] = value

    await documents_collection.update_one(
        {"_id": object_id},
        {"$set": {"custom_fields": merged_fields, "updated_by_user_id": current_user["id"], "updated_by_username": current_user["username"]}},
    )
    updated_doc = await documents_collection.find_one({"_id": object_id})
    if not updated_doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    await write_audit_log(
        request,
        "document.custom_fields.update",
        {"document_id": doc_id, "field_names": sorted(list((payload.custom_fields or {}).keys()))},
        current_user=current_user,
    )
    return normalize_document(updated_doc)



@router.put("/documents/{doc_id}/image")
async def edit_document_image(request: Request, doc_id: str, data: ImageEditRequest, current_user=Depends(require_editor_user)):
    object_id = object_id_or_404(doc_id)

    document = await documents_collection.find_one({"_id": object_id})
    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    target_filename = (data.image_filename or document.get("filename") or "").strip()
    if not target_filename:
        raise HTTPException(status_code=400, detail="У документа нет изображения")

    file_path = os.path.join(UPLOAD_DIR, target_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл изображения не найден")


    requested_rotation = data.rotate_degrees
    rotate_degrees = int(round(requested_rotation / 90.0) * 90) % 360

    with Image.open(file_path) as image:
        image = ImageOps.exif_transpose(image)

        if rotate_degrees:
            image = image.rotate(-rotate_degrees, expand=True)

        if data.crop:
            width, height = image.size

            left = int(width * (data.crop.x_percent / 100.0))
            top = int(height * (data.crop.y_percent / 100.0))
            crop_width = int(width * (data.crop.width_percent / 100.0))
            crop_height = int(height * (data.crop.height_percent / 100.0))

            right = min(width, left + max(1, crop_width))
            bottom = min(height, top + max(1, crop_height))

            if left >= right or top >= bottom:
                raise HTTPException(status_code=400, detail="Некорректная область обрезки")

            image = image.crop((left, top, right, bottom))

        ext = os.path.splitext(target_filename)[1].lower()
        if ext in {".jpg", ".jpeg"}:
            image = image.convert("RGB")
            image.save(file_path, format="JPEG", quality=95)
        elif ext == ".png":
            image.save(file_path, format="PNG")
        else:
            image.save(file_path)

    with open(file_path, "rb") as updated_file:
        new_hash = calculate_file_hash(updated_file.read())

    image_version = now_yekaterinburg().isoformat()
    set_payload = {}
    if target_filename == document.get("filename"):
        set_payload["file_hash"] = new_hash
        set_payload["image_version"] = image_version

    if set_payload:
        await documents_collection.update_one(
            {"_id": object_id},
            {"$set": {**set_payload, "updated_by_user_id": current_user["id"], "updated_by_username": current_user["username"]}},
        )

    await documents_collection.update_one(
        {"_id": object_id, "gallery_images.filename": target_filename},
        {
            "$set": {
                "gallery_images.$.file_hash": new_hash,
                "gallery_images.$.image_version": image_version,
            }
        },
    )

    updated_doc = await documents_collection.find_one({"_id": object_id})
    if not updated_doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    updated_doc = normalize_document(updated_doc)
    updated_doc["applied_rotate_degrees"] = rotate_degrees
    updated_doc["edited_image_filename"] = target_filename
    await write_audit_log(
        request,
        "document.image.edit",
        {"document_id": doc_id, "image_filename": target_filename, "rotate_degrees": rotate_degrees},
        current_user=current_user,
    )
    return updated_doc


@router.delete("/documents/{doc_id}/gallery/{image_filename}")
async def delete_gallery_image(request: Request, doc_id: str, image_filename: str, current_user=Depends(require_editor_user)):
    object_id = object_id_or_404(doc_id)
    document = await documents_collection.find_one({"_id": object_id})
    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    gallery_images = document.get("gallery_images") or []
    if len(gallery_images) <= 1:
        raise HTTPException(status_code=400, detail="Нельзя удалить последнее изображение карточки")

    image_index = next((idx for idx, item in enumerate(gallery_images) if item.get("filename") == image_filename), -1)
    if image_index < 0:
        raise HTTPException(status_code=404, detail="Изображение не найдено")

    removed_image = gallery_images[image_index]
    updated_gallery = [item for item in gallery_images if item.get("filename") != image_filename]
    new_primary = updated_gallery[0]

    set_payload = {
        "gallery_images": updated_gallery,
    }

    if document.get("filename") == image_filename:
        set_payload.update(
            {
                "filename": new_primary.get("filename"),
                "path": new_primary.get("path"),
                "file_hash": new_primary.get("file_hash"),
                "image_version": new_primary.get("image_version"),
                "recognized_text": new_primary.get("recognized_text", ""),
                "boxes": new_primary.get("boxes", []),
                "top_code": new_primary.get("top_code"),
                "ocr_lines": new_primary.get("ocr_lines", []),
            }
        )

    await documents_collection.update_one({"_id": object_id}, {"$set": {**set_payload, "updated_by_user_id": current_user["id"], "updated_by_username": current_user["username"]}})

    removed_path = removed_image.get("path") or os.path.join(UPLOAD_DIR, image_filename)
    if removed_path and os.path.exists(removed_path):
        os.remove(removed_path)

    updated_doc = await documents_collection.find_one({"_id": object_id})
    if not updated_doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    await write_audit_log(
        request,
        "document.gallery.delete",
        {"document_id": doc_id, "image_filename": image_filename},
        current_user=current_user,
    )

    return normalize_document(updated_doc)


@router.delete("/documents/{doc_id}/attachments/{attachment_filename}")
async def delete_attachment(request: Request, doc_id: str, attachment_filename: str, current_user=Depends(require_editor_user)):
    object_id = object_id_or_404(doc_id)
    document = await documents_collection.find_one({"_id": object_id})
    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    attachments = document.get("attachments") or []
    attachment = next((item for item in attachments if item.get("filename") == attachment_filename), None)
    if not attachment:
        raise HTTPException(status_code=404, detail="Файл не найден")

    file_path = os.path.join(UPLOAD_DIR, attachment_filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    await documents_collection.update_one(
        {"_id": object_id},
        {"$pull": {"attachments": {"filename": attachment_filename}}, "$set": {"updated_by_user_id": current_user["id"], "updated_by_username": current_user["username"]}},
    )

    updated_doc = await documents_collection.find_one({"_id": object_id})
    if not updated_doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    await write_audit_log(
        request,
        "document.attachment.delete",
        {"document_id": doc_id, "attachment_filename": attachment_filename},
        current_user=current_user,
    )

    return normalize_document(updated_doc)




UPLOAD_FOLDER = "backend/uploads"

@router.delete("/documents/{doc_id}")
async def delete_document(request: Request, doc_id: str, current_user=Depends(require_editor_user)):
    object_id = object_id_or_404(doc_id)
    document = await documents_collection.find_one({"_id": object_id})
    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")
    if document.get("is_archived"):
        return {"message": "Карточка уже в архиве"}

    await documents_collection.update_one(
        {"_id": object_id},
        {"$set": {"is_archived": True, "archived_at": datetime.now(timezone.utc), "updated_by_user_id": current_user["id"], "updated_by_username": current_user["username"]}},
    )
    await write_audit_log(
        request,
        "document.archive",
        {"document_id": doc_id},
        current_user=current_user,
    )
    return {"message": "Карточка перемещена в архив"}


@router.get("/documents/archived")
async def get_archived_documents():
    await cleanup_expired_archived_documents(documents_collection, UPLOAD_DIR, retention_days=30)
    documents = []
    async for doc in documents_collection.find({"is_archived": True}).sort("archived_at", -1):
        documents.append(normalize_document(doc))
    return documents


@router.post("/documents/{doc_id}/restore")
async def restore_archived_document(request: Request, doc_id: str, current_user=Depends(require_editor_user)):
    object_id = object_id_or_404(doc_id)
    document = await documents_collection.find_one({"_id": object_id})
    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    await documents_collection.update_one(
        {"_id": object_id},
        {"$set": {"is_archived": False, "archived_at": None, "updated_by_user_id": current_user["id"], "updated_by_username": current_user["username"]}},
    )
    restored_doc = await documents_collection.find_one({"_id": object_id})
    if not restored_doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    await write_audit_log(request, "document.restore", {"document_id": doc_id}, current_user=current_user)
    return normalize_document(restored_doc)


@router.delete("/documents/{doc_id}/permanent")
async def permanently_delete_archived_document(request: Request, doc_id: str, current_user=Depends(require_editor_user)):
    object_id = object_id_or_404(doc_id)
    document = await documents_collection.find_one({"_id": object_id})
    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")
    if not document.get("is_archived"):
        raise HTTPException(status_code=400, detail="Сначала переместите карточку в архив")

    removed_files = await permanently_delete_document(document, documents_collection, UPLOAD_DIR)
    await write_audit_log(
        request,
        "document.permanent_delete",
        {"document_id": doc_id, "files_deleted": removed_files},
        current_user=current_user,
    )
    return {"message": "Карточка удалена навсегда"}


@router.post("/documents/archive/restore-bulk")
async def restore_archived_documents_bulk(request: Request, payload: DocumentIdsRequest, current_user=Depends(require_editor_user)):
    object_ids = [object_id_or_404(doc_id) for doc_id in payload.ids]
    if not object_ids:
        raise HTTPException(status_code=400, detail="Список карточек пуст")

    await documents_collection.update_many(
        {"_id": {"$in": object_ids}, "is_archived": True},
        {"$set": {"is_archived": False, "archived_at": None, "updated_by_user_id": current_user["id"], "updated_by_username": current_user["username"]}},
    )
    await write_audit_log(request, "document.bulk_restore", {"document_ids": payload.ids}, current_user=current_user)
    return {"message": "Карточки восстановлены"}


@router.post("/documents/archive/permanent-delete-bulk")
async def permanently_delete_archived_documents_bulk(request: Request, payload: DocumentIdsRequest, current_user=Depends(require_editor_user)):
    object_ids = [object_id_or_404(doc_id) for doc_id in payload.ids]
    if not object_ids:
        raise HTTPException(status_code=400, detail="Список карточек пуст")

    cursor = documents_collection.find({"_id": {"$in": object_ids}, "is_archived": True})
    deleted_ids: List[str] = []
    deleted_files: List[str] = []
    async for document in cursor:
        removed_files = await permanently_delete_document(document, documents_collection, UPLOAD_DIR)
        deleted_ids.append(str(document["_id"]))
        deleted_files.extend(removed_files)

    await write_audit_log(
        request,
        "document.bulk_permanent_delete",
        {"document_ids": deleted_ids, "files_deleted": deleted_files},
        current_user=current_user,
    )
    return {"message": "Карточки удалены навсегда", "deleted_count": len(deleted_ids)}




@router.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    object_id = object_id_or_404(doc_id)
    document = await documents_collection.find_one({"_id": object_id})
    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")
    return normalize_document(document)


@router.get("/search")
async def search_documents(q: str):
    results = []
    async for doc in documents_collection.find(
        {
            "is_archived": {"$ne": True},
            "$or": [
                {"recognized_text": {"$regex": q, "$options": "i"}},
                {"display_filename": {"$regex": q, "$options": "i"}},
                {"filename": {"$regex": q, "$options": "i"}},
                {"tags": {"$regex": q, "$options": "i"}},
            ]
        }
    ):
        results.append(normalize_document(doc))
    return results





@router.get("/folders/tree")
async def get_folder_tree(current_user=Depends(require_editor_user)):
    await ensure_unsorted_folder(folders_collection)
    folders = []
    async for folder in folders_collection.find().sort("name", 1):
        folders.append(folder)

    by_parent = {}
    for folder in folders:
        parent_key = str(folder["parent_id"]) if folder.get("parent_id") else None
        by_parent.setdefault(parent_key, []).append(folder)

    def build_node(folder: dict):
        folder_id = str(folder["_id"])
        children = sorted(by_parent.get(folder_id, []), key=lambda item: item.get("name", "").lower())
        return {**serialize_folder(folder), "children": [build_node(child) for child in children]}

    roots = sorted(by_parent.get(None, []), key=lambda item: item.get("name", "").lower())
    return {"folders": [build_node(root) for root in roots]}


@router.get("/folders/{folder_id}/contents")
async def get_folder_contents(folder_id: str, current_user=Depends(require_editor_user)):
    folder = await find_folder_by_public_id(folder_id)
    folder_object_id = folder["_id"]

    child_folders = []
    async for child in folders_collection.find({"parent_id": folder_object_id}).sort("name", 1):
        child_folders.append(serialize_folder(child))

    documents = []
    async for doc in documents_collection.find(
        {"folder_id": folder_object_id, "$or": [{"is_archived": False}, {"is_archived": {"$exists": False}}]}
    ).sort("created_at", -1):
        documents.append(normalize_document(doc))

    return {"folder": serialize_folder(folder), "folders": child_folders, "documents": documents}


@router.post("/folders")
async def create_folder(request: Request, payload: FolderCreatePayload, current_user=Depends(require_editor_user)):
    folder_name = (payload.name or "").strip()
    if not folder_name:
        raise HTTPException(status_code=400, detail="Имя папки обязательно")

    parent_object_id = None
    if payload.parent_id:
        parent_folder = await find_folder_by_public_id(payload.parent_id)
        parent_object_id = parent_folder["_id"]

    duplicate = await folders_collection.find_one({"name": folder_name, "parent_id": parent_object_id})
    if duplicate:
        raise HTTPException(status_code=400, detail="Папка с таким именем уже существует")

    now = datetime.now(timezone.utc)
    new_folder = {
        "name": folder_name,
        "parent_id": parent_object_id,
        "is_system": False,
        "created_at": now,
        "updated_at": now,
        "created_by_user_id": current_user["id"],
        "created_by_username": current_user["username"],
    }
    inserted = await folders_collection.insert_one(new_folder)
    created_folder = await folders_collection.find_one({"_id": inserted.inserted_id})
    await write_audit_log(
        request,
        "folder.create",
        {"folder_id": str(inserted.inserted_id), "parent_id": payload.parent_id, "name": folder_name},
        current_user=current_user,
    )
    return {"folder": serialize_folder(created_folder)}


@router.put("/folders/{folder_id}")
async def rename_folder(request: Request, folder_id: str, payload: FolderUpdatePayload, current_user=Depends(require_editor_user)):
    folder = await find_folder_by_public_id(folder_id)
    folder_object_id = folder["_id"]
    if folder.get("is_system"):
        raise HTTPException(status_code=400, detail="Системную папку нельзя переименовать")

    new_name = (payload.name or "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Имя папки обязательно")

    duplicate = await folders_collection.find_one(
        {"_id": {"$ne": folder_object_id}, "name": new_name, "parent_id": folder.get("parent_id")}
    )
    if duplicate:
        raise HTTPException(status_code=400, detail="Папка с таким именем уже существует")

    await folders_collection.update_one(
        {"_id": folder_object_id},
        {"$set": {"name": new_name, "updated_at": datetime.now(timezone.utc)}},
    )
    updated_folder = await folders_collection.find_one({"_id": folder_object_id})
    await write_audit_log(request, "folder.rename", {"folder_id": folder_id, "name": new_name}, current_user=current_user)
    return {"folder": serialize_folder(updated_folder)}


@router.delete("/folders/{folder_id}")
async def delete_folder(request: Request, folder_id: str, current_user=Depends(require_editor_user)):
    folder = await find_folder_by_public_id(folder_id)
    folder_object_id = folder["_id"]
    if folder.get("is_system"):
        raise HTTPException(status_code=400, detail="Системную папку нельзя удалить")

    child_count = await folders_collection.count_documents({"parent_id": folder_object_id}, limit=1)
    if child_count:
        raise HTTPException(status_code=400, detail="Нельзя удалить непустую папку")

    doc_count = await documents_collection.count_documents(
        {"folder_id": folder_object_id, "$or": [{"is_archived": False}, {"is_archived": {"$exists": False}}]},
        limit=1,
    )
    if doc_count:
        raise HTTPException(status_code=400, detail="Нельзя удалить непустую папку")

    await folders_collection.delete_one({"_id": folder_object_id})
    await write_audit_log(request, "folder.delete", {"folder_id": folder_id}, current_user=current_user)
    return {"message": "Папка удалена"}


@router.post("/folders/{folder_id}/move")
async def move_folder(request: Request, folder_id: str, payload: FolderMovePayload, current_user=Depends(require_editor_user)):
    folder = await find_folder_by_public_id(folder_id)
    folder_object_id = folder["_id"]
    if folder.get("is_system"):
        raise HTTPException(status_code=400, detail="Системную папку нельзя перемещать")

    target_parent_id = None
    if payload.target_parent_id:
        parent_folder = await find_folder_by_public_id(payload.target_parent_id)
        target_parent_id = parent_folder["_id"]
        if target_parent_id == folder_object_id:
            raise HTTPException(status_code=400, detail="Нельзя переместить папку в саму себя")
        if await is_descendant_folder(target_parent_id, folder_object_id):
            raise HTTPException(status_code=400, detail="Нельзя переместить папку в дочернюю папку")

    duplicate = await folders_collection.find_one(
        {"_id": {"$ne": folder_object_id}, "name": folder.get("name"), "parent_id": target_parent_id}
    )
    if duplicate:
        raise HTTPException(status_code=400, detail="В папке назначения уже есть папка с таким именем")

    await folders_collection.update_one(
        {"_id": folder_object_id},
        {"$set": {"parent_id": target_parent_id, "updated_at": datetime.now(timezone.utc)}},
    )
    updated_folder = await folders_collection.find_one({"_id": folder_object_id})
    await write_audit_log(
        request,
        "folder.move",
        {"folder_id": folder_id, "target_parent_id": payload.target_parent_id},
        current_user=current_user,
    )
    return {"folder": serialize_folder(updated_folder)}


@router.post("/documents/{doc_id}/move")
async def move_document_to_folder(request: Request, doc_id: str, payload: DocumentMovePayload, current_user=Depends(require_editor_user)):
    object_id = object_id_or_404(doc_id)
    document = await documents_collection.find_one({"_id": object_id})
    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    target_folder_id = await resolve_folder_id_or_unsorted(payload.target_folder_id)
    await documents_collection.update_one(
        {"_id": object_id},
        {"$set": {"folder_id": target_folder_id, "updated_by_user_id": current_user["id"], "updated_by_username": current_user["username"]}},
    )
    updated_doc = await documents_collection.find_one({"_id": object_id})
    await write_audit_log(
        request,
        "document.move",
        {"document_id": doc_id, "target_folder_id": str(target_folder_id)},
        current_user=current_user,
    )
    return normalize_document(updated_doc)


@router.get("/folders/{folder_id}/path")
async def get_folder_path(folder_id: str, current_user=Depends(require_editor_user)):
    folder = await find_folder_by_public_id(folder_id)
    folder_object_id = folder["_id"]
    return {"path": await build_folder_path(folder_object_id)}


@router.get("/documents/{doc_id}/path")
async def get_document_path(doc_id: str, current_user=Depends(require_editor_user)):
    object_id = object_id_or_404(doc_id)
    document = await documents_collection.find_one({"_id": object_id})
    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    if not document.get("folder_id"):
        folder_id = await ensure_unsorted_folder(folders_collection)
        await documents_collection.update_one({"_id": object_id}, {"$set": {"folder_id": folder_id}})
    else:
        folder_id = document["folder_id"]
        if isinstance(folder_id, str):
            folder = await find_folder_by_public_id(folder_id)
            folder_id = folder["_id"]

    path = await build_folder_path(folder_id)
    return {
        "document_id": doc_id,
        "folder_path": path,
        "document": {"id": doc_id, "name": document.get("display_filename") or document.get("filename")},
    }


class TagRequest(BaseModel):
    tag: str

@router.post("/tags")
async def create_tag(http_request: Request, request: TagRequest, current_user=Depends(require_admin_user)):
    tag = request.tag.strip().lower()

    existing_tag = await tags_collection.find_one({"tag": tag})
    if existing_tag:
        raise HTTPException(status_code=400, detail="Тег уже существует")

    new_tag = {"tag": tag, "created_at": now_yekaterinburg()}
    await tags_collection.insert_one(new_tag)
    await write_audit_log(http_request, "tag.create", {"tag": tag}, current_user=current_user)
    return {"message": "Тег добавлен", "tag": new_tag}

@router.delete("/tags/{tag}")
async def delete_tag(request: Request, tag: str, current_user=Depends(require_admin_user)):
    normalized = tag.strip().lower()

    if not normalized:
        raise HTTPException(status_code=400, detail="Тег обязателен")

    result = await tags_collection.delete_one({"tag": normalized})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Тег не найден")

    await documents_collection.update_many({"tags": normalized}, {"$pull": {"tags": normalized}})
    await write_audit_log(request, "tag.delete", {"tag": normalized}, current_user=current_user)

    return {"message": "Тег удалён", "tag": normalized}




@router.get("/tags")
async def get_tags():
    tags = []
    async for tag in tags_collection.find().sort([("created_at", -1), ("_id", -1)]):
        tags.append(tag["tag"])
    return {"tags": tags}
