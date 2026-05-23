from __future__ import annotations

import time
from io import BytesIO
from typing import Any, Dict

import os
import requests


def _remote_url() -> str:
    return os.getenv("REMOTE_VISION_OCR_URL", "http://111.88.113.136:8000/ocr")


def _timeout() -> int:
    return int(os.getenv("REMOTE_VISION_OCR_TIMEOUT_SECONDS", "60"))


def generate_ocr(file_bytes: bytes, filename: str = "image.png", content_type: str = "image/png") -> Dict[str, Any]:
    files = {"file": (filename, BytesIO(file_bytes), content_type)}
    try:
        response = requests.post(_remote_url(), files=files, timeout=_timeout())
        response.raise_for_status()
        payload = response.json()
        text = str(payload.get("text") or "").strip()
        return {"success": True, "text": text, "model": payload.get("model") or "Qwen3-VL"}
    except requests.Timeout:
        return {"success": False, "text": "", "error": "REMOTE_OCR_TIMEOUT"}
    except requests.ConnectionError:
        return {"success": False, "text": "", "error": "REMOTE_OCR_UNAVAILABLE"}
    except (requests.RequestException, ValueError):
        return {"success": False, "text": "", "error": "REMOTE_OCR_REQUEST_FAILED"}


def check_health(timeout: int = 5) -> Dict[str, Any]:
    return test_connection(_remote_url(), timeout)


def test_connection(url: str, timeout: int) -> Dict[str, Any]:
    started = time.perf_counter()
    try:
        response = requests.get(url, timeout=timeout)
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {"success": response.ok, "connected": response.ok, "url": url, "latency_ms": latency_ms, "status_code": response.status_code}
    except requests.RequestException:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {"success": False, "connected": False, "url": url, "latency_ms": latency_ms}
