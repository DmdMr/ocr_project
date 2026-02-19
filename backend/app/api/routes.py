import os
import hashlib
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException
from bson import ObjectId


from backend.app.services.ocr_service import recognize_text
from backend.app.db.database import documents_collection

router = APIRouter(prefix="/api")

UPLOAD_DIR = "backend/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def calculate_file_hash(file_bytes: bytes):
    return hashlib.md5(file_bytes).hexdigest()


# 🔹 Загрузка файла
@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):

    if file.content_type not in ["image/png", "image/jpeg", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Only PNG and JPG allowed")

    file_bytes = await file.read()
    file_hash = calculate_file_hash(file_bytes)

    # Проверка дубликата
    existing = await documents_collection.find_one({"file_hash": file_hash})
    if existing:
        existing["_id"] = str(existing["_id"])
        return {
            "message": "File already exists",
            "document": existing
        }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    recognized_text = recognize_text(file_path)

    document_data = {
        "filename": filename,
        "path": file_path,
        "recognized_text": recognized_text,
        "file_hash": file_hash,
        "created_at": datetime.utcnow(),
        "tags": []
    }


    result = await documents_collection.insert_one(document_data)
    document_data["_id"] = str(result.inserted_id)

    return {
        "message": "File uploaded successfully",
        "document": document_data
    }


# 🔹 Получить все документы
@router.get("/documents")
async def get_documents():
    documents = []
    async for doc in documents_collection.find().sort("created_at", -1):
        doc["_id"] = str(doc["_id"])
        documents.append(doc)
    return documents


from pydantic import BaseModel
from typing import Optional, List
from bson import ObjectId

class DocumentUpdate(BaseModel):
    recognized_text: Optional[str] = None
    tags: Optional[List[str]] = None

@router.put("/documents/{doc_id}")
async def update_document(doc_id: str, data: DocumentUpdate):
    update_data = {k: v for k, v in data.dict().items() if v is not None}

    await documents_collection.update_one(
        {"_id": ObjectId(doc_id)},
        {"$set": update_data}
    )

    updated_doc = await documents_collection.find_one({"_id": ObjectId(doc_id)})
    updated_doc["_id"] = str(updated_doc["_id"])

    return updated_doc



UPLOAD_FOLDER = "backend/uploads"

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):

    # 1️⃣ Find document first
    document = await documents_collection.find_one({"_id": ObjectId(doc_id)})

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # 2️⃣ Delete physical file
    filename = document.get("filename")
    if filename:
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        if os.path.exists(file_path):
            os.remove(file_path)

    # 3️⃣ Delete database record
    await documents_collection.delete_one({"_id": ObjectId(doc_id)})

    return {"message": "Deleted successfully"}




# 🔹 Поиск
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




from pydantic import BaseModel

class TagRequest(BaseModel):
    tag: str


@router.post("/documents/{doc_id}/tags")
async def add_tag(doc_id: str, request: TagRequest):
    tag = request.tag.strip().lower()

    if not tag:
        raise HTTPException(status_code=400, detail="Tag cannot be empty")

    result = await documents_collection.update_one(
        {"_id": ObjectId(doc_id)},
        {"$addToSet": {"tags": tag}}  # prevents duplicates
    )

    if result.modified_count == 1:
        return {"message": "Tag added"}

    raise HTTPException(status_code=404, detail="Document not found")



@router.delete("/documents/{doc_id}/tags")
async def remove_tag(doc_id: str, request: TagRequest):
    tag = request.tag.strip().lower()

    result = await documents_collection.update_one(
        {"_id": ObjectId(doc_id)},
        {"$pull": {"tags": tag}}
    )

    if result.modified_count == 1:
        return {"message": "Tag removed"}

    raise HTTPException(status_code=404, detail="Document not found")
