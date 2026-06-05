from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from backend.app.services.provider_manager import provider_manager
from backend.app.services.paddle_ocr_service import validate_image_file
from backend.app.paths import OCR_HISTORY_PATH

print("[DEBUG] provider_manager type:", type(provider_manager))
print("[DEBUG] provider_manager dir:", dir(provider_manager))

HISTORY_PATH = OCR_HISTORY_PATH


def _append_history(entry: dict[str, Any]) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def recognize_text(image_path: str) -> Dict[str, Any]:
    #print("[DEBUG] ACTIVE PROVIDER MANAGER:", provider_manager)
    #print("[DEBUG] TYPE:", type(provider_manager))

    validate_image_file(image_path)

    file_path = Path(image_path)
    file_bytes = file_path.read_bytes()
    content_type = "image/png" if file_path.suffix.lower() == ".png" else "image/jpeg"

    config = provider_manager.load_config()
    provider_name = config.get("provider", "remote")

    os.environ["VISION_OCR_PROVIDER"] = provider_name
    os.environ["REMOTE_VISION_OCR_URL"] = str(
        config.get(
            "remote_url",
            os.getenv("REMOTE_VISION_OCR_URL", "http://90.156.157.68:8000/ocr")
        )
    )
    os.environ["REMOTE_VISION_OCR_TIMEOUT_SECONDS"] = str(
        config.get("timeout", os.getenv("REMOTE_VISION_OCR_TIMEOUT_SECONDS", "60"))
    )
    os.environ["OLLAMA_MODEL"] = str(
        config.get("ollama_model", os.getenv("OLLAMA_MODEL", "qwen3-vl:2b"))
    )

    # ✅ THIS IS WHAT YOU WERE MISSING
    result = provider_manager.run_ocr(
        file_bytes=file_bytes,
        filename=file_path.name,
        content_type=content_type
    )

    if not result.success:
        raise RuntimeError(result.error or "provider OCR failed")

    history_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "image_path": image_path,
        "provider": result.provider,
        "text": result.text,
        "processing_time_ms": result.processing_time_ms,
        "model": os.getenv("OLLAMA_MODEL", "Qwen3-VL"),
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
