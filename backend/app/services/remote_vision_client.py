from __future__ import annotations

import os
from io import BytesIO
from typing import Any, Dict

import requests

REMOTE_VISION_OCR_URL = os.getenv("REMOTE_VISION_OCR_URL", "http://127.0.0.1:8000/ocr")
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REMOTE_VISION_OCR_TIMEOUT_SECONDS", "60"))


def generate_ocr(file_bytes: bytes, filename: str = "image.png", content_type: str = "image/png") -> Dict[str, Any]:
    files = {
        "file": (filename, BytesIO(file_bytes), content_type),
    }

    try:
        response = requests.post(
            REMOTE_VISION_OCR_URL,
            files=files,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.Timeout:
        return {"success": False, "text": "", "error": "REMOTE_OCR_TIMEOUT"}
    except requests.ConnectionError:
        return {"success": False, "text": "", "error": "REMOTE_OCR_UNAVAILABLE"}
    except requests.RequestException:
        return {"success": False, "text": "", "error": "REMOTE_OCR_REQUEST_FAILED"}

    try:
        payload = response.json()
    except ValueError:
        return {"success": False, "text": "", "error": "REMOTE_OCR_INVALID_RESPONSE"}

    text = str(payload.get("text") or "").strip()
    success = bool(payload.get("success", True)) and bool(text or payload.get("text") == "")

    if not success:
        return {"success": False, "text": "", "error": "REMOTE_OCR_FAILED"}

    return {"success": True, "text": text}
