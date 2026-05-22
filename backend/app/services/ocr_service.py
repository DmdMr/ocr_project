from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from backend.app.services.ocr.providers import ocr_provider_manager
from backend.app.services.paddle_ocr_service import validate_image_file

HISTORY_PATH = Path(os.getenv("OCR_HISTORY_PATH", "backend/data/ocr_history.jsonl"))


def _append_history(entry: dict[str, Any]) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def recognize_text(image_path: str) -> Dict[str, Any]:
    validate_image_file(image_path)
    file_path = Path(image_path)
    file_bytes = file_path.read_bytes()
    content_type = "image/png" if file_path.suffix.lower() == ".png" else "image/jpeg"

    provider_name = ocr_provider_manager.get_selected_provider_name()
    providers_to_try = [provider_name]
    if provider_name == "remote":
        providers_to_try.append("ollama")

    result = None
    last_error = None
    for name in providers_to_try:
        provider = ocr_provider_manager.providers[name]
        response = provider.recognize(file_bytes=file_bytes, filename=file_path.name, content_type=content_type)
        if response.success:
            result = response
            break
        last_error = response.error or f"{name} OCR failed"

    if result is None:
        raise RuntimeError(f"OCR Pipeline failed: {last_error or 'unknown error'}")

    history_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "image_path": image_path,
        "provider": result.provider,
        "text": result.text,
        "processing_time_ms": result.processing_time_ms,
        "model": os.getenv("OLLAMA_MODEL", "Qwen3-VL") if result.provider == "ollama" else "Qwen3-VL",
    }
    _append_history(history_entry)

    return {
        "success": True,
        "provider": result.provider,
        "text": result.text,
        "recognized_text": result.text,
        "boxes": [],
        "regions": result.regions,
        "top_code": None,
        "ocr_lines": [],
        "confidence": None,
        "processing_time_ms": result.processing_time_ms,
        "model": history_entry["model"],
    }


def recognize_top_code(image_path: str) -> Dict[str, Any]:
    result = recognize_text(image_path)
    return {"text": "", "top_code": "", "ocr_lines": result.get("ocr_lines", [])}
