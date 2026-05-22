from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class OCRProviderResult:
    success: bool
    provider: str
    text: str
    regions: list[dict[str, Any]]
    processing_time_ms: int
    error: str | None = None


class OCRProvider(Protocol):
    name: str

    def health_check(self) -> dict[str, Any]:
        ...

    def recognize(self, file_bytes: bytes, filename: str, content_type: str) -> OCRProviderResult:
        ...
