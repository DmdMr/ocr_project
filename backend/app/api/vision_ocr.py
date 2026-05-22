from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.app.services.remote_vision_client import generate_ocr

router = APIRouter(prefix="/api", tags=["vision-ocr"])

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/bmp", "image/tiff"}


@router.post("/vision-ocr")
async def vision_ocr(file: UploadFile = File(...)):
    if not file.content_type or file.content_type.lower() not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only image uploads are supported")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    result = generate_ocr(
        file_bytes=file_bytes,
        filename=file.filename or "image.png",
        content_type=file.content_type,
    )

    if not result.get("success"):
        raise HTTPException(status_code=503, detail=result.get("error", "REMOTE_OCR_ERROR"))

    return {"success": True, "text": result.get("text", "")}
