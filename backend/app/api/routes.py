import hashlib
import os
from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from PIL import Image, ImageOps

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
        raise HTTPException(status_code=404, detail="Document not found") from exc


@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    if file.content_type not in ["image/png", "image/jpeg", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Only PNG and JPG allowed")

    file_bytes = await file.read()
    file_hash = calculate_file_hash(file_bytes)

    existing = await documents_collection.find_one({"file_hash": file_hash})
    if existing:
        existing["_id"] = str(existing["_id"])
        return {"message": "File already exists", "document": existing}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as destination:
        destination.write(file_bytes)

    ocr_result = recognize_text(file_path)

    document_data = {
        "filename": filename,
        "path": file_path,
        "recognized_text": ocr_result["text"],
        "boxes": ocr_result["boxes"],
        "file_hash": file_hash,
        "created_at": datetime.utcnow(),
        "image_version": datetime.utcnow().isoformat(),
        "tags": []
    }

    result = await documents_collection.insert_one(document_data)
    document_data["_id"] = str(result.inserted_id)

    return {"message": "File uploaded successfully", "document": document_data}


@router.get("/documents")
async def get_documents():
    documents = []

    async for doc in documents_collection.find().sort("created_at", -1):
        doc["_id"] = str(doc["_id"])
        documents.append(doc)

    return documents


class DocumentUpdate(BaseModel):
    recognized_text: Optional[str] = None
    tags: Optional[List[str]] = None


class CropRequest(BaseModel):
    x_percent: float = Field(0, ge=0, le=100)
    y_percent: float = Field(0, ge=0, le=100)
    width_percent: float = Field(100, ge=0.1, le=100)
    height_percent: float = Field(100, ge=0.1, le=100)


class ImageEditRequest(BaseModel):
    rotate_degrees: int = 0
    crop: Optional[CropRequest] = None


@router.put("/documents/{doc_id}")
async def update_document(doc_id: str, data: DocumentUpdate):
    object_id = object_id_or_404(doc_id)
    update_data = {key: value for key, value in data.model_dump().items() if value is not None}

    await documents_collection.update_one({"_id": object_id}, {"$set": update_data})

    updated_doc = await documents_collection.find_one({"_id": object_id})
    if not updated_doc:
        raise HTTPException(status_code=404, detail="Document not found")

    updated_doc["_id"] = str(updated_doc["_id"])
    return updated_doc


@router.put("/documents/{doc_id}/image")
async def edit_document_image(doc_id: str, data: ImageEditRequest):
    object_id = object_id_or_404(doc_id)

    document = await documents_collection.find_one({"_id": object_id})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    filename = document.get("filename")
    if not filename:
        raise HTTPException(status_code=400, detail="Document has no image")

    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image file not found")

    rotate_degrees = data.rotate_degrees % 360

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
                raise HTTPException(status_code=400, detail="Invalid crop area")

            image = image.crop((left, top, right, bottom))

        ext = os.path.splitext(filename)[1].lower()
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
    await documents_collection.update_one(
        {"_id": object_id},
        {"$set": {"file_hash": new_hash, "image_version": image_version}}
    )

    updated_doc = await documents_collection.find_one({"_id": object_id})
    if not updated_doc:
        raise HTTPException(status_code=404, detail="Document not found")

    updated_doc["_id"] = str(updated_doc["_id"])
    return updated_doc


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    object_id = object_id_or_404(doc_id)

    document = await documents_collection.find_one({"_id": object_id})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    filename = document.get("filename")
    if filename:
        file_path = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)

    await documents_collection.delete_one({"_id": object_id})

    return {"message": "Deleted successfully"}


@router.get("/search")
async def search_documents(q: str):
    results = []

    async for doc in documents_collection.find(
        {
            "$or": [
                {"recognized_text": {"$regex": q, "$options": "i"}},
                {"filename": {"$regex": q, "$options": "i"}},
                {"tags": {"$regex": q, "$options": "i"}}
            ]
        }
    ):
        doc["_id"] = str(doc["_id"])
        results.append(doc)

    return results


class TagRequest(BaseModel):
    tag: str


@router.post("/tags")
async def create_tag(request: TagRequest):
    tag = request.tag.strip().lower()

    existing_tag = await tags_collection.find_one({"tag": tag})
    if existing_tag:
        raise HTTPException(status_code=400, detail="Tag already exists")

    new_tag = {"tag": tag}
    await tags_collection.insert_one(new_tag)
    return {"message": "Tag added", "tag": new_tag}


@router.delete("/tags/{tag}")
async def delete_tag(tag: str):
    normalized = tag.strip().lower()

    if not normalized:
        raise HTTPException(status_code=400, detail="Tag is required")

    result = await tags_collection.delete_one({"tag": normalized})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Tag not found")

    await documents_collection.update_many(
        {"tags": normalized},
        {"$pull": {"tags": normalized}}
    )

    return {"message": "Tag deleted", "tag": normalized}


@router.get("/tags")
async def get_tags():
    tags = []
    async for tag in tags_collection.find():
        tags.append(tag["tag"])

    return {"tags": tags}
