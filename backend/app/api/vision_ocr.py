import logging

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.app.services.ocr.providers import ocr_provider_manager

router = APIRouter(prefix="/api", tags=["vision-ocr"])
logger = logging.getLogger("backend.api.vision_ocr")

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/bmp", "image/tiff"}


class ProviderSelectRequest(BaseModel):
    provider: str


@router.get("/ocr/providers")
async def list_ocr_providers():
    return {"success": True, "providers": ocr_provider_manager.list_providers()}


@router.get("/ocr/health")
async def ocr_health():
    return ocr_provider_manager.health_status()


@router.post("/ocr/provider/select")
async def select_ocr_provider(payload: ProviderSelectRequest):
    try:
        selected = ocr_provider_manager.select_provider(payload.provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "provider": selected}


@router.post("/vision-ocr")
async def vision_ocr(file: UploadFile = File(...)):
    if not file.content_type or file.content_type.lower() not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only image uploads are supported")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    logger.info("vision-ocr request file=%s provider=%s", file.filename, ocr_provider_manager.get_selected_provider_name())
    result = ocr_provider_manager.run_ocr(
        file_bytes=file_bytes,
        filename=file.filename or "image.png",
        content_type=file.content_type,
    )

    if not result.success:
        raise HTTPException(status_code=503, detail=result.error or "VISION_OCR_ERROR")

    return {
        "success": True,
        "provider": result.provider,
        "text": result.text,
        "regions": result.regions,
        "processing_time_ms": result.processing_time_ms,
        # TODO: persist user corrections for HITL feedback loop.
        # TODO: attach region overlay coordinates once detector pipeline is unified.
        # TODO: add confidence scoring from provider/model outputs.
        # TODO: export accepted corrections for retraining dataset generation.
    }
