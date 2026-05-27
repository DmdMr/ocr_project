import json
import logging
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from threading import Lock
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.app.services.provider_manager import provider_manager

router = APIRouter(prefix="/api", tags=["vision-ocr"])
logger = logging.getLogger("backend.api.vision_ocr")

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/bmp", "image/tiff"}
ALLOWED_PROVIDERS = {"ollama", "vps", "qwen3-vl"}
DATASET_DIR = Path("dataset")
DATASET_RECORDS_FILE = DATASET_DIR / "records.jsonl"
DATASET_WRITE_LOCK = Lock()
PROJECT_ROOT = Path(__file__).resolve().parents[3]
UPLOADS_DIR = PROJECT_ROOT / "backend" / "uploads"


class ProviderSelectRequest(BaseModel):
    provider: str


class OCRCorrectionRequest(BaseModel):
    image_path: str
    ocr_text: str
    corrected_text: str
    provider: str


def _ensure_dataset_file() -> None:
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    DATASET_RECORDS_FILE.touch(exist_ok=True)


def _read_all_records() -> list[dict]:
    _ensure_dataset_file()
    records: list[dict] = []
    with DATASET_RECORDS_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            row = line.strip()
            if not row:
                continue
            try:
                records.append(json.loads(row))
            except json.JSONDecodeError:
                logger.warning("Skipping invalid JSONL row in %s", DATASET_RECORDS_FILE)
    return records


def _append_record(record: dict) -> None:
    _ensure_dataset_file()
    serialized = json.dumps(record, ensure_ascii=False)
    with DATASET_WRITE_LOCK:
        with DATASET_RECORDS_FILE.open("a", encoding="utf-8") as f:
            f.write(serialized + "\n")
            f.flush()


@router.get("/ocr/providers")
async def list_ocr_providers():
    return {"success": True, "providers": provider_manager.list_providers()}


@router.get("/ocr/health")
async def ocr_health():
    return provider_manager.health_status()


@router.post("/ocr/provider/select")
async def select_ocr_provider(payload: ProviderSelectRequest):
    try:
        selected = provider_manager.select_provider(payload.provider)
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

    logger.info("vision-ocr request file=%s provider=%s", file.filename, provider_manager.get_selected_provider_name())
    result = provider_manager.run_ocr(
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
    }


@router.post("/ocr/correct")
async def save_ocr_correction(payload: OCRCorrectionRequest):
    if payload.provider not in ALLOWED_PROVIDERS:
        raise HTTPException(status_code=400, detail="Unsupported provider")

    normalized_path = str(payload.image_path or "").strip()
    filename = Path(normalized_path).name or "unknown"
    if "?" in filename:
        filename = filename.split("?", 1)[0]
    if "#" in filename:
        filename = filename.split("#", 1)[0]
    stored_image_path = filename
    record = {
        "id": str(uuid4()),
        "image_path": stored_image_path,
        "ocr_text": payload.ocr_text,
        "corrected_text": payload.corrected_text,
        "provider": payload.provider,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "filename": filename,
    }
    _append_record(record)
    return record


@router.get("/ocr/dataset")
async def get_ocr_dataset():
    return _read_all_records()


@router.get("/ocr/export")
async def export_ocr_dataset():
    records = _read_all_records()
    uploads_dir = UPLOADS_DIR
    print(f"[OCR EXPORT] total records: {len(records)}")
    print(f"[OCR EXPORT] uploads_dir: {uploads_dir}")

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        dataset_lines = [json.dumps(record, ensure_ascii=False) for record in records]
        zf.writestr("dataset/records.jsonl", "\n".join(dataset_lines) + ("\n" if dataset_lines else ""))

        for record in records:
            image_path_value = str(record.get("image_path") or "").strip()
            print(f"[OCR EXPORT] image_path={image_path_value!r}")
            if not image_path_value:
                continue
            image_filename = Path(image_path_value).name
            if "?" in image_filename:
                image_filename = image_filename.split("?", 1)[0]
            if "#" in image_filename:
                image_filename = image_filename.split("#", 1)[0]
            if not image_filename:
                continue
            source_path = uploads_dir / image_filename
            print(f"[OCR EXPORT] source_path={source_path} exists={source_path.exists() and source_path.is_file()}")
            if source_path.exists() and source_path.is_file():
                zf.write(source_path, arcname=f"dataset/images/{image_filename}")
        print(f"[OCR EXPORT] zip contents: {zf.namelist()}")

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=ocr_training_dataset.zip"},
    )
