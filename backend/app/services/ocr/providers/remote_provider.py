from __future__ import annotations

import logging
import time
from typing import Any

from backend.app.services.ocr.providers.base import OCRProviderResult
from backend.app.services.remote_vision_client import check_health as remote_check_health
from backend.app.services.remote_vision_client import generate_ocr as remote_generate_ocr

logger = logging.getLogger("backend.ocr.providers.remote")


class RemoteOCRProvider:
    name = "remote"

    def health_check(self) -> dict[str, Any]:
        return remote_check_health()

    def recognize(self, file_bytes: bytes, filename: str, content_type: str) -> OCRProviderResult:
        started = time.perf_counter()
        response = remote_generate_ocr(file_bytes=file_bytes, filename=filename, content_type=content_type)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info("remote OCR processed file=%s success=%s time_ms=%s", filename, response.get("success"), elapsed_ms)
        return OCRProviderResult(
            success=bool(response.get("success")),
            provider=self.name,
            text=str(response.get("text") or ""),
            regions=[],
            processing_time_ms=elapsed_ms,
            error=response.get("error"),
        )
