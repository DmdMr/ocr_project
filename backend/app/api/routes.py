import os
import hashlib
import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from bson import ObjectId


from backend.app.services.ocr_service import recognize_text
from backend.app.db.database import documents_collection

from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image, ImageOps
from pydantic import BaseModel, Field

from backend.app.db.database import documents_collection, tags_collection
from backend.app.services.archive_service import cleanup_expired_archived_documents, permanently_delete_document
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


def object_id_or_404(doc_id: str):
    try:
        return ObjectId(doc_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Документ не найден") from exc
    

def build_gallery_item(*, filename: str, path: str, file_hash: str, ocr_text: str, boxes: list):
    return {
        "filename": filename,
        "path": path,
        "file_hash": file_hash,
        "recognized_text": ocr_text,
        "boxes": boxes,
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
    if doc.get("is_archived") is None:
        doc["is_archived"] = False
    if "archived_at" not in doc:
        doc["archived_at"] = None
    gallery = doc.get("gallery_images")
    if not gallery:
        doc["gallery_images"] = [
            {
                "filename": doc.get("filename"),
                "path": doc.get("path"),
                "file_hash": doc.get("file_hash"),
                "recognized_text": doc.get("recognized_text", ""),
                "boxes": doc.get("boxes", []),
                "created_at": doc.get("created_at", now_yekaterinburg()),
                "image_version": doc.get("image_version"),
            }
        ]
    if doc.get("attachments") is None:
        doc["attachments"] = []
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


def parse_user_agent(user_agent: str):
    ua = (user_agent or "").lower()

    if "edg/" in ua:
        browser = "Edge"
    elif "chrome/" in ua and "edg/" not in ua:
        browser = "Chrome"
    elif "safari/" in ua and "chrome/" not in ua:
        browser = "Safari"
    elif "firefox/" in ua:
        browser = "Firefox"
    else:
        browser = "unknown"

    if "windows" in ua:
        os_name = "Windows"
    elif "mac os" in ua or "macintosh" in ua:
        os_name = "macOS"
    elif "android" in ua:
        os_name = "Android"
    elif "iphone" in ua or "ipad" in ua or "ios" in ua:
        os_name = "iOS"
    elif "linux" in ua:
        os_name = "Linux"
    else:
        os_name = "unknown"

    if re.search(r"(mobile|iphone|android)", ua):
        device_type = "mobile"
    elif "ipad" in ua or "tablet" in ua:
        device_type = "tablet"
    else:
        device_type = "desktop"

    return {"browser": browser, "os": os_name, "device_type": device_type}


def get_request_actor(request: Request):
    forwarded_for = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    client_host = request.client.host if request.client else None
    ip_address = forwarded_for or client_host or "unknown"
    user_agent = request.headers.get("user-agent") or "unknown"
    request_user = getattr(request.state, "user", None)
    user_id = request.headers.get("x-user-id") or (getattr(request_user, "id", None) if request_user else None)
    user_email = request.headers.get("x-user-email") or (getattr(request_user, "email", None) if request_user else None)
    session_id = request.headers.get("x-session-id") or request.cookies.get("session_id")
    request_id = request.headers.get("x-request-id")

    return {
        "ip": ip_address,
        "device_name": request.headers.get("x-device-name") or "unknown",
        "user_agent": user_agent,
        "device": parse_user_agent(user_agent),
        "user": {"id": user_id, "email": user_email} if user_id or user_email else None,
        "context": {"request_id": request_id, "session_id": session_id} if request_id or session_id else None,
    }


def write_audit_log(
    request: Request,
    action: str,
    payload: dict,
    *,
    status: str = "success",
    message: str | None = None,
    duration_ms: int | None = None,
    file_metadata: dict | None = None,
    before: dict | None = None,
    after: dict | None = None,
):
    actor = get_request_actor(request)
    entry = {
        "timestamp": now_yekaterinburg().isoformat(),
        "action": action,
        "actor": actor,
        "payload": payload,
        "status": status,
    }
    if message is not None:
        entry["message"] = message
    if duration_ms is not None:
        entry["duration_ms"] = duration_ms
    if file_metadata is not None:
        entry["file_metadata"] = file_metadata
    if before is not None or after is not None:
        entry["changes"] = {"before": before, "after": after}
    audit_logger.info(json.dumps(entry, ensure_ascii=False))


def get_image_metadata(file_path: str, file_bytes: bytes, content_type: str):
    width = None
    height = None
    try:
        with Image.open(file_path) as image:
            width, height = image.size
    except Exception:
        pass
    return {
        "file_size": len(file_bytes),
        "file_type": content_type,
        "image_width": width,
        "image_height": height,
    }



@router.post("/upload")
async def upload_image(request: Request, file: UploadFile = File(...)):
    started_at = time.perf_counter()

    if file.content_type not in ["image/png", "image/jpeg", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Разрешены только PNG и JPG")

    file_bytes = await file.read()
    file_hash = calculate_file_hash(file_bytes)

    existing = await documents_collection.find_one({"file_hash": file_hash})
    if existing:
        return {"message": "Файл уже существует", "document": normalize_document(existing)}

    filename, file_path = save_upload_file(file, file_bytes)
    file_path = autocrop_whitespace(file_path)
    ocr_result = recognize_text(file_path)

    gallery_item = build_gallery_item(
        filename=filename,
        path=file_path,
        file_hash=file_hash,
        ocr_text=ocr_result["text"],
        boxes=ocr_result["boxes"],
    )

    document_data = {
        "filename": filename,
        "display_filename": file.filename.strip() or file.filename,
        "path": file_path,
        "recognized_text": ocr_result["text"],  
        "boxes": ocr_result["boxes"],         
        "file_hash": file_hash,
        "created_at": now_yekaterinburg(),
        "image_version": now_yekaterinburg().isoformat(),
        "tags": [],
        "is_archived": False,
        "archived_at": None,
        "gallery_images": [gallery_item],
        "attachments": [],
    }


    result = await documents_collection.insert_one(document_data)
    document_data["_id"] = str(result.inserted_id)
    file_metadata = get_image_metadata(file_path, file_bytes, file.content_type or "application/octet-stream")
    write_audit_log(
        request,
        "document.upload",
        {"document_id": document_data["_id"], "filename": document_data["filename"]},
        message="Файл успешно загружен",
        duration_ms=int((time.perf_counter() - started_at) * 1000),
        file_metadata=file_metadata,
    )

    return {"message": "Файл успешно загружен", "document": document_data}

@router.post("/documents/{doc_id}/gallery")
async def upload_images_to_document(request: Request, doc_id: str, files: List[UploadFile] = File(...)):
    started_at = time.perf_counter()
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
    skipped_files: List[str] = []
    uploaded_files_metadata: List[dict] = []

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
        ocr_result = recognize_text(file_path)

        item = build_gallery_item(
            filename=filename,
            path=file_path,
            file_hash=file_hash,
            ocr_text=ocr_result["text"],
            boxes=ocr_result["boxes"],
        )
        added_items.append(item)
        uploaded_files_metadata.append(
            get_image_metadata(file_path, file_bytes, file.content_type or "application/octet-stream")
        )
        existing_hashes.add(file_hash)

        recognized_text = (ocr_result.get("text") or "").strip()
        if recognized_text:
            appended_texts.append(recognized_text)

    if not added_items:
        detail = "Не загружено ни одного нового корректного изображения"
        if skipped_files:
            detail = f"{detail}. " + "; ".join(skipped_files)
        raise HTTPException(status_code=400, detail=detail)


    existing_text = (document.get("recognized_text") or "").strip()
    combined_text_parts = [part for part in [existing_text, *appended_texts] if part]
    combined_text = "\n\n".join(combined_text_parts)

    await documents_collection.update_one(
        {"_id": object_id},
        {
            "$push": {"gallery_images": {"$each": added_items}},
            "$set": {"recognized_text": combined_text},
        },
    )

    updated_doc = await documents_collection.find_one({"_id": object_id})
    if not updated_doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    updated_doc = normalize_document(updated_doc)
    write_audit_log(
        request,
        "document.gallery.upload",
        {"document_id": doc_id, "added_count": len(added_items), "skipped_files": skipped_files},
        duration_ms=int((time.perf_counter() - started_at) * 1000),
        file_metadata={"files": uploaded_files_metadata},
    )
    return {
        "message": "Галерея обновлена",
        "added_count": len(added_items),
        "skipped_files": skipped_files,
        "document": updated_doc,
    }


@router.post("/documents/{doc_id}/attachments")
async def upload_attachments_to_document(request: Request, doc_id: str, files: List[UploadFile] = File(...)):
    started_at = time.perf_counter()
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
    uploaded_files_metadata: List[dict] = []

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
        uploaded_files_metadata.append(
            {
                "file_size": len(file_bytes),
                "file_type": file.content_type or "application/octet-stream",
            }
        )
        existing_names.add(normalized_name)

    if not added_items:
        detail = "Не загружено ни одного нового файла"
        if skipped_files:
            detail = f"{detail}. " + "; ".join(skipped_files)
        raise HTTPException(status_code=400, detail=detail)

    await documents_collection.update_one(
        {"_id": object_id},
        {"$push": {"attachments": {"$each": added_items}}},
    )

    updated_doc = await documents_collection.find_one({"_id": object_id})
    if not updated_doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    write_audit_log(
        request,
        "document.attachment.upload",
        {"document_id": doc_id, "added_count": len(added_items), "skipped_files": skipped_files},
        duration_ms=int((time.perf_counter() - started_at) * 1000),
        file_metadata={"files": uploaded_files_metadata},
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

@router.put("/documents/{doc_id}")
async def update_document(request: Request, doc_id: str, data: DocumentUpdate):
    started_at = time.perf_counter()
    object_id = object_id_or_404(doc_id)
    before_doc = await documents_collection.find_one({"_id": object_id})
    if not before_doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    update_data = {key: value for key, value in data.model_dump().items() if value is not None}

    if "display_filename" in update_data:
        update_data["display_filename"] = normalize_display_filename(
            update_data["display_filename"],
            before_doc.get("filename") or before_doc.get("display_filename") or "",
        )

    await documents_collection.update_one({"_id": object_id}, {"$set": update_data})

    updated_doc = await documents_collection.find_one({"_id": object_id})
    if not updated_doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    write_audit_log(
        request,
        "document.update",
        {"document_id": doc_id, "updated_fields": sorted(update_data.keys())},
        duration_ms=int((time.perf_counter() - started_at) * 1000),
        before={key: before_doc.get(key) for key in update_data.keys()},
        after={key: updated_doc.get(key) for key in update_data.keys()},
    )

    return normalize_document(updated_doc)



@router.put("/documents/{doc_id}/image")
async def edit_document_image(request: Request, doc_id: str, data: ImageEditRequest):
    started_at = time.perf_counter()
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
            {"$set": set_payload},
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
    with open(file_path, "rb") as image_file:
        edited_image_bytes = image_file.read()
    write_audit_log(
        request,
        "document.image.edit",
        {"document_id": doc_id, "image_filename": target_filename, "rotate_degrees": rotate_degrees},
        duration_ms=int((time.perf_counter() - started_at) * 1000),
        file_metadata=get_image_metadata(file_path, edited_image_bytes, "image/*"),
    )
    return updated_doc


@router.delete("/documents/{doc_id}/gallery/{image_filename}")
async def delete_gallery_image(request: Request, doc_id: str, image_filename: str):
    started_at = time.perf_counter()
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
            }
        )

    await documents_collection.update_one({"_id": object_id}, {"$set": set_payload})

    removed_path = removed_image.get("path") or os.path.join(UPLOAD_DIR, image_filename)
    if removed_path and os.path.exists(removed_path):
        os.remove(removed_path)

    updated_doc = await documents_collection.find_one({"_id": object_id})
    if not updated_doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    write_audit_log(
        request,
        "document.gallery.delete",
        {"document_id": doc_id, "image_filename": image_filename},
        duration_ms=int((time.perf_counter() - started_at) * 1000),
    )

    return normalize_document(updated_doc)


@router.delete("/documents/{doc_id}/attachments/{attachment_filename}")
async def delete_attachment(request: Request, doc_id: str, attachment_filename: str):
    started_at = time.perf_counter()
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
        {"$pull": {"attachments": {"filename": attachment_filename}}},
    )

    updated_doc = await documents_collection.find_one({"_id": object_id})
    if not updated_doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    write_audit_log(
        request,
        "document.attachment.delete",
        {"document_id": doc_id, "attachment_filename": attachment_filename},
        duration_ms=int((time.perf_counter() - started_at) * 1000),
    )

    return normalize_document(updated_doc)




UPLOAD_FOLDER = "backend/uploads"

@router.delete("/documents/{doc_id}")
async def delete_document(request: Request, doc_id: str):
    started_at = time.perf_counter()
    object_id = object_id_or_404(doc_id)
    document = await documents_collection.find_one({"_id": object_id})
    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")
    if document.get("is_archived"):
        return {"message": "Карточка уже в архиве"}

    await documents_collection.update_one(
        {"_id": object_id},
        {"$set": {"is_archived": True, "archived_at": datetime.now(timezone.utc)}},
    )
    write_audit_log(
        request,
        "document.archive",
        {"document_id": doc_id},
        duration_ms=int((time.perf_counter() - started_at) * 1000),
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
async def restore_archived_document(request: Request, doc_id: str):
    started_at = time.perf_counter()
    object_id = object_id_or_404(doc_id)
    document = await documents_collection.find_one({"_id": object_id})
    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    await documents_collection.update_one(
        {"_id": object_id},
        {"$set": {"is_archived": False, "archived_at": None}},
    )
    restored_doc = await documents_collection.find_one({"_id": object_id})
    if not restored_doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    write_audit_log(
        request,
        "document.restore",
        {"document_id": doc_id},
        duration_ms=int((time.perf_counter() - started_at) * 1000),
    )
    return normalize_document(restored_doc)


@router.delete("/documents/{doc_id}/permanent")
async def permanently_delete_archived_document(request: Request, doc_id: str):
    started_at = time.perf_counter()
    object_id = object_id_or_404(doc_id)
    document = await documents_collection.find_one({"_id": object_id})
    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")
    if not document.get("is_archived"):
        raise HTTPException(status_code=400, detail="Сначала переместите карточку в архив")

    removed_files = await permanently_delete_document(document, documents_collection, UPLOAD_DIR)
    write_audit_log(
        request,
        "document.permanent_delete",
        {"document_id": doc_id, "files_deleted": removed_files},
        duration_ms=int((time.perf_counter() - started_at) * 1000),
    )
    return {"message": "Карточка удалена навсегда"}


@router.post("/documents/archive/restore-bulk")
async def restore_archived_documents_bulk(request: Request, payload: DocumentIdsRequest):
    started_at = time.perf_counter()
    object_ids = [object_id_or_404(doc_id) for doc_id in payload.ids]
    if not object_ids:
        raise HTTPException(status_code=400, detail="Список карточек пуст")

    await documents_collection.update_many(
        {"_id": {"$in": object_ids}, "is_archived": True},
        {"$set": {"is_archived": False, "archived_at": None}},
    )
    write_audit_log(
        request,
        "document.bulk_restore",
        {"document_ids": payload.ids},
        duration_ms=int((time.perf_counter() - started_at) * 1000),
    )
    return {"message": "Карточки восстановлены"}


@router.post("/documents/archive/permanent-delete-bulk")
async def permanently_delete_archived_documents_bulk(request: Request, payload: DocumentIdsRequest):
    started_at = time.perf_counter()
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

    write_audit_log(
        request,
        "document.bulk_permanent_delete",
        {"document_ids": deleted_ids, "files_deleted": deleted_files},
        duration_ms=int((time.perf_counter() - started_at) * 1000),
    )
    return {"message": "Карточки удалены навсегда", "deleted_count": len(deleted_ids)}




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





class TagRequest(BaseModel):
    tag: str

@router.post("/tags")
async def create_tag(http_request: Request, request: TagRequest):
    started_at = time.perf_counter()
    tag = request.tag.strip().lower()

    existing_tag = await tags_collection.find_one({"tag": tag})
    if existing_tag:
        raise HTTPException(status_code=400, detail="Тег уже существует")

    new_tag = {"tag": tag, "created_at": now_yekaterinburg()}
    await tags_collection.insert_one(new_tag)
    write_audit_log(
        http_request,
        "tag.create",
        {"tag": tag},
        duration_ms=int((time.perf_counter() - started_at) * 1000),
    )
    return {"message": "Тег добавлен", "tag": new_tag}

@router.delete("/tags/{tag}")
async def delete_tag(request: Request, tag: str):
    started_at = time.perf_counter()
    normalized = tag.strip().lower()

    if not normalized:
        raise HTTPException(status_code=400, detail="Тег обязателен")

    result = await tags_collection.delete_one({"tag": normalized})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Тег не найден")

    await documents_collection.update_many({"tags": normalized}, {"$pull": {"tags": normalized}})
    write_audit_log(
        request,
        "tag.delete",
        {"tag": normalized},
        duration_ms=int((time.perf_counter() - started_at) * 1000),
    )

    return {"message": "Тег удалён", "tag": normalized}




@router.get("/tags")
async def get_tags():
    tags = []
    async for tag in tags_collection.find().sort([("created_at", -1), ("_id", -1)]):
        tags.append(tag["tag"])
    return {"tags": tags}
