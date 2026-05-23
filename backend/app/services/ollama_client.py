from __future__ import annotations

from typing import Any, Dict

import os
import requests

OLLAMA_PROMPT = "Read all handwritten engineering text from this image. Return only clean OCR text."
DEFAULT_TIMEOUT_SECONDS = 60


def _ollama_url() -> str:
    return os.getenv("OLLAMA_URL", "http://localhost:11434")


def _generate_url() -> str:
    return f"{_ollama_url()}/api/generate"


def _model_name() -> str:
    return os.getenv("OLLAMA_MODEL", "qwen3-vl:2b")


def check_health(timeout: int = 3) -> Dict[str, Any]:
    url = _ollama_url()
    try:
        response = requests.get(url, timeout=timeout)
        return {"success": response.ok, "url": url}
    except requests.RequestException:
        return {"success": False, "url": url}


def generate_ocr(image_base64: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
    payload = {
        "model": _model_name(),
        "prompt": OLLAMA_PROMPT,
        "images": [image_base64],
        "stream": False,
        "options": {"temperature": 0.2},
    }
    try:
        response = requests.post(_generate_url(), json=payload, timeout=timeout)
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

    return {"success": True, "text": (data.get("response") or "").strip(), "model": _model_name()}


def pull_model(model_name: str, timeout: int = 300) -> Dict[str, Any]:
    try:
        response = requests.post(f"{_ollama_url()}/api/pull", json={"name": model_name, "stream": False}, timeout=timeout)
        response.raise_for_status()
        return {"success": True, "model": model_name}
    except requests.RequestException as exc:
        return {"success": False, "model": model_name, "error": str(exc)}
