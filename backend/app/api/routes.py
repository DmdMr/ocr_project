import os
import hashlib
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from bson import ObjectId


from backend.app.services.ocr_service import recognize_text
from backend.app.db.database import documents_collection

from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image, ImageOps
from pydantic import BaseModel, Field

from backend.app.db.database import documents_collection, tags_collection
from backend.app.services.ocr_service import recognize_text

router = APIRouter(prefix="/api")

UPLOAD_DIR = "backend/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def calculate_file_hash(file_bytes: bytes):
    return hashlib.md5(file_bytes).hexdigest()


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
        "created_at": datetime.utcnow(),
        "image_version": datetime.utcnow().isoformat(),
    }


def build_attachment_item(*, filename: str, path: str, original_name: str, content_type: str, size: int):
    return {
        "filename": filename,
        "path": path,
        "original_name": original_name,
        "content_type": content_type,
        "size": size,
        "created_at": datetime.utcnow(),
    }


def normalize_document(doc: dict):
    doc["_id"] = str(doc["_id"])
    gallery = doc.get("gallery_images")
    if not gallery:
        doc["gallery_images"] = [
            {
                "filename": doc.get("filename"),
                "path": doc.get("path"),
                "file_hash": doc.get("file_hash"),
                "recognized_text": doc.get("recognized_text", ""),
                "boxes": doc.get("boxes", []),
                "created_at": doc.get("created_at", datetime.utcnow()),
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



@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):

    if file.content_type not in ["image/png", "image/jpeg", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Разрешены только PNG и JPG")

    file_bytes = await file.read()
    file_hash = calculate_file_hash(file_bytes)

    existing = await documents_collection.find_one({"file_hash": file_hash})
    if existing:
        return {"message": "Файл уже существует", "document": normalize_document(existing)}

    filename, file_path = save_upload_file(file, file_bytes)
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
        "created_at": datetime.utcnow(),
        "image_version": datetime.utcnow().isoformat(),
        "tags": [],
        "gallery_images": [gallery_item],
        "attachments": [],
    }


    result = await documents_collection.insert_one(document_data)
    document_data["_id"] = str(result.inserted_id)

    return {"message": "Файл успешно загружен", "document": document_data}

@router.post("/documents/{doc_id}/gallery")
async def upload_images_to_document(doc_id: str, files: List[UploadFile] = File(...)):
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
        ocr_result = recognize_text(file_path)

        item = build_gallery_item(
            filename=filename,
            path=file_path,
            file_hash=file_hash,
            ocr_text=ocr_result["text"],
            boxes=ocr_result["boxes"],
        )
        added_items.append(item)
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
    return {
        "message": "Галерея обновлена",
        "added_count": len(added_items),
        "skipped_files": skipped_files,
        "document": updated_doc,
    }


@router.post("/documents/{doc_id}/attachments")
async def upload_attachments_to_document(doc_id: str, files: List[UploadFile] = File(...)):
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
        {"$push": {"attachments": {"$each": added_items}}},
    )

    updated_doc = await documents_collection.find_one({"_id": object_id})
    if not updated_doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    return {
        "message": "Файлы прикреплены",
        "added_count": len(added_items),
        "skipped_files": skipped_files,
        "document": normalize_document(updated_doc),
    }


@router.get("/documents")
async def get_documents():
    documents = []
    async for doc in documents_collection.find().sort("created_at", -1):
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

@router.put("/documents/{doc_id}")
async def update_document(doc_id: str, data: DocumentUpdate):
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

    await documents_collection.update_one({"_id": object_id}, {"$set": update_data})

    updated_doc = await documents_collection.find_one({"_id": object_id})
    if not updated_doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    return normalize_document(updated_doc)



@router.put("/documents/{doc_id}/image")
async def edit_document_image(doc_id: str, data: ImageEditRequest):
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

    image_version = datetime.utcnow().isoformat()
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
    return updated_doc


@router.delete("/documents/{doc_id}/attachments/{attachment_filename}")
async def delete_attachment(doc_id: str, attachment_filename: str):
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

    return normalize_document(updated_doc)




UPLOAD_FOLDER = "backend/uploads"

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    object_id = object_id_or_404(doc_id)

    document = await documents_collection.find_one({"_id": object_id})

    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    gallery_images = document.get("gallery_images") or []
    gallery_filenames = [item.get("filename") for item in gallery_images if item.get("filename")]
    attachment_files = document.get("attachments") or []
    attachment_filenames = [item.get("filename") for item in attachment_files if item.get("filename")]

    filenames_to_delete = set(gallery_filenames)
    filenames_to_delete.update(attachment_filenames)
    if document.get("filename"):
        filenames_to_delete.add(document.get("filename"))

    for filename in filenames_to_delete:
        file_path = os.path.join(UPLOAD_DIR, filename)

        if os.path.exists(file_path):
            os.remove(file_path)

    await documents_collection.delete_one({"_id": object_id})
    return {"message": "Успешно удалено"}




@router.get("/search")
async def search_documents(q: str):
    results = []
    async for doc in documents_collection.find(
        {
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
async def create_tag(request: TagRequest):
    tag = request.tag.strip().lower()

    existing_tag = await tags_collection.find_one({"tag": tag})
    if existing_tag:
        raise HTTPException(status_code=400, detail="Тег уже существует")

    new_tag = {"tag": tag, "created_at": datetime.utcnow()}
    await tags_collection.insert_one(new_tag)
    return {"message": "Тег добавлен", "tag": new_tag}

@router.delete("/tags/{tag}")
async def delete_tag(tag: str):
    normalized = tag.strip().lower()

    if not normalized:
        raise HTTPException(status_code=400, detail="Тег обязателен")

    result = await tags_collection.delete_one({"tag": normalized})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Тег не найден")

    await documents_collection.update_many({"tags": normalized}, {"$pull": {"tags": normalized}})

    return {"message": "Тег удалён", "tag": normalized}




@router.get("/tags")
async def get_tags():
    tags = []
    async for tag in tags_collection.find().sort([("created_at", -1), ("_id", -1)]):
        tags.append(tag["tag"])
    return {"tags": tags}
