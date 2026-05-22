from __future__ import annotations

import base64
import logging
import time

from backend.app.services.ocr.providers.base import OCRProviderResult
from backend.app.services.ollama_client import check_health as ollama_check_health
from backend.app.services.ollama_client import generate_ocr as ollama_generate_ocr

logger = logging.getLogger("backend.ocr.providers.ollama")


class OllamaOCRProvider:
    name = "ollama"

    def health_check(self) -> dict[str, object]:
        return ollama_check_health()

    def recognize(self, file_bytes: bytes, filename: str, content_type: str) -> OCRProviderResult:
        started = time.perf_counter()
        image_base64 = base64.b64encode(file_bytes).decode("utf-8")
        response = ollama_generate_ocr(image_base64=image_base64)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info("ollama OCR processed file=%s success=%s time_ms=%s", filename, response.get("success"), elapsed_ms)
        return OCRProviderResult(
            success=bool(response.get("success")),
            provider=self.name,
            text=str(response.get("text") or ""),
            regions=[],
            processing_time_ms=elapsed_ms,
            error=response.get("error"),
        )
