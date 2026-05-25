from __future__ import annotations

import time
from io import BytesIO
from typing import Any, Dict

import os
import requests


def _remote_url() -> str:
    return os.getenv("REMOTE_VISION_OCR_URL", "http://90.156.157.68:8000/ocr")


def _timeout() -> int:
    return int(os.getenv("REMOTE_VISION_OCR_TIMEOUT_SECONDS", "60"))


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


def generate_ocr(file_bytes: bytes, filename: str = "image.png", content_type: str = "image/png") -> Dict[str, Any]:
    files = {"file": (filename, BytesIO(file_bytes), content_type)}

    url = _remote_url()
    timeout = _timeout()

    print("[REMOTE OCR] URL:", url)
    print("[REMOTE OCR] TIMEOUT:", timeout)
    print("[REMOTE OCR] FILE:", filename)
    print("[REMOTE OCR] CONTENT-TYPE:", content_type)

    try:
        response = requests.post(url, files=files, timeout=timeout)

        print("[REMOTE OCR] STATUS CODE:", response.status_code)
        print("[REMOTE OCR] RESPONSE TEXT:", response.text)

        response.raise_for_status()

        payload = response.json()

        print("[REMOTE OCR] JSON PAYLOAD:", payload)

        text = str(payload.get("text") or "").strip()

        return {
            "success": True,
            "text": text,
            "model": payload.get("model") or "Qwen3-VL"
        }

    except requests.Timeout:
        print("[REMOTE OCR] ERROR: TIMEOUT")
        return {"success": False, "text": "", "error": "REMOTE_OCR_TIMEOUT"}

    except requests.ConnectionError as e:
        print("[REMOTE OCR] ERROR: CONNECTION", str(e))
        return {"success": False, "text": "", "error": "REMOTE_OCR_UNAVAILABLE"}

    except requests.RequestException as e:
        print("[REMOTE OCR] ERROR: REQUEST EXCEPTION", str(e))
        return {"success": False, "text": "", "error": "REMOTE_OCR_REQUEST_FAILED"}

    except ValueError as e:
        print("[REMOTE OCR] ERROR: JSON PARSE FAILED", str(e))
        return {"success": False, "text": "", "error": "REMOTE_OCR_BAD_JSON"}
