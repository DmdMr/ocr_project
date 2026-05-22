import base64

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.app.services.ollama_client import generate_ocr

router = APIRouter(prefix="/api", tags=["vision-ocr"])

@router.post("/vision-ocr")
async def vision_ocr(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are supported")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    image_base64 = base64.b64encode(file_bytes).decode("utf-8")
    result = generate_ocr(image_base64)

    if not result.get("success"):
        raise HTTPException(status_code=503, detail=result.get("error", "OLLAMA_ERROR"))

    return result
