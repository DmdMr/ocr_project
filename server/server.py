import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Protocol

import requests
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


class OCRProvider(Protocol):
    name: str

    def extract_text(self, image_bytes: bytes, filename: str, content_type: str) -> str:
        ...


class OllamaProvider:
    name = "ollama"

    def __init__(self, endpoint: str, timeout_s: float) -> None:
        self.endpoint = endpoint
        self.timeout_s = timeout_s

    def extract_text(self, image_bytes: bytes, filename: str, content_type: str) -> str:
        files = {"file": (filename, image_bytes, content_type)}
        response = requests.post(self.endpoint, files=files, timeout=self.timeout_s)
        response.raise_for_status()
        payload = response.json()
        text = payload.get("text")
        if not isinstance(text, str):
            raise ValueError("Provider response missing string 'text' field")
        return text


class VPSProvider:
    name = "vps"

    def __init__(self, endpoint: str, timeout_s: float) -> None:
        self.endpoint = endpoint
        self.timeout_s = timeout_s

    def extract_text(self, image_bytes: bytes, filename: str, content_type: str) -> str:
        files = {"file": (filename, image_bytes, content_type)}
        response = requests.post(self.endpoint, files=files, timeout=self.timeout_s)
        response.raise_for_status()
        payload = response.json()
        text = payload.get("text")
        if not isinstance(text, str):
            raise ValueError("Provider response missing string 'text' field")
        return text


class ProviderRouter:
    def __init__(self) -> None:
        timeout_s = float(os.getenv("OCR_HTTP_TIMEOUT", "30"))
        self.providers: Dict[str, OCRProvider] = {
            "ollama": OllamaProvider(
                endpoint=os.getenv("OLLAMA_OCR_ENDPOINT", "http://localhost:11434/api/ocr"),
                timeout_s=timeout_s,
            ),
            "vps": VPSProvider(
                endpoint=os.getenv("VPS_OCR_ENDPOINT", "http://127.0.0.1:8001/ocr"),
                timeout_s=timeout_s,
            ),
        }

    def active_provider(self) -> OCRProvider:
        provider_key = os.getenv("OCR_PROVIDER", "ollama").strip().lower()
        provider = self.providers.get(provider_key)
        if provider is None:
            raise ValueError(
                f"Unsupported OCR_PROVIDER '{provider_key}'. Expected one of: {', '.join(self.providers.keys())}"
            )
        return provider


class MetricsLogger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, record: Dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


app = FastAPI(title="OCR Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = ProviderRouter()
metrics = MetricsLogger(Path("logs/metrics.jsonl"))


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": str(exc)},
    )


@app.post("/ocr")
async def ocr(file: UploadFile = File(...)) -> Dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    provider = router.active_provider()
    started_at = time.perf_counter()

    success = False
    text = ""
    error_message = None

    try:
        text = provider.extract_text(
            image_bytes=image_bytes,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
        )
        success = True
        return_payload = {
            "success": True,
            "text": text,
            "provider": provider.name,
            "latency_ms": round((time.perf_counter() - started_at) * 1000, 3),
        }
        return return_payload
    except requests.Timeout:
        error_message = "Upstream OCR provider timeout"
        raise HTTPException(status_code=504, detail=error_message)
    except requests.RequestException as e:
        error_message = f"Upstream OCR provider error: {e}"
        raise HTTPException(status_code=502, detail=error_message)
    except Exception as e:
        error_message = f"OCR processing failed: {e}"
        raise HTTPException(status_code=500, detail=error_message)
    finally:
        latency_ms = round((time.perf_counter() - started_at) * 1000, 3)
        metrics.log(
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "provider": provider.name,
                "success": success,
                "latency_ms": latency_ms,
                "status": "ok" if success else "error",
                "error": error_message,
                "filename": file.filename,
                "bytes": len(image_bytes),
            }
        )
