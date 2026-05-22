from __future__ import annotations

from typing import Any, Dict

import os

import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_GENERATE_URL = f"{OLLAMA_URL}/api/generate"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen_ocr")
OLLAMA_PROMPT = "Read all handwritten engineering text from this image. Return only clean OCR text."
DEFAULT_TIMEOUT_SECONDS = 60


def check_health(timeout: int = 3) -> Dict[str, Any]:
    try:
        response = requests.get(OLLAMA_URL, timeout=timeout)
        return {"success": response.ok}
    except requests.RequestException:
        return {"success": False}


def generate_ocr(image_base64: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": OLLAMA_PROMPT,
        "images": [image_base64],
        "stream": False,
        "options": {
            "temperature": 0.2,
        },
    }

    try:
        response = requests.post(OLLAMA_GENERATE_URL, json=payload, timeout=timeout)
        response.raise_for_status()
    except requests.Timeout:
        return {"success": False, "text": "", "error": "OLLAMA_TIMEOUT"}
    except requests.ConnectionError:
        return {"success": False, "text": "", "error": "OLLAMA_UNAVAILABLE"}
    except requests.RequestException:
        return {"success": False, "text": "", "error": "OLLAMA_REQUEST_FAILED"}

    try:
        data = response.json()
    except ValueError:
        return {"success": False, "text": "", "error": "OLLAMA_INVALID_RESPONSE"}

    text = (data.get("response") or "").strip()
    return {"success": True, "text": text}
