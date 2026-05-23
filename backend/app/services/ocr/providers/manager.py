from __future__ import annotations

import os
from typing import Any

from backend.app.services.ocr.providers.base import OCRProviderResult
from backend.app.services.ocr.providers.ollama_provider import OllamaOCRProvider
from backend.app.services.ocr.providers.remote_provider import RemoteOCRProvider

_PROVIDER_OVERRIDE: str | None = None


class OCRProviderManager:
    def __init__(self):
        self.providers = {
            "remote": RemoteOCRProvider(),
            "ollama": OllamaOCRProvider(),
        }

    def get_selected_provider_name(self) -> str:
        if _PROVIDER_OVERRIDE in self.providers:
            return _PROVIDER_OVERRIDE  # type: ignore[return-value]
        configured = (os.getenv("VISION_OCR_PROVIDER", "remote") or "remote").strip().lower()
        return configured if configured in self.providers else "remote"

    def select_provider(self, provider_name: str) -> str:
        normalized = (provider_name or "").strip().lower()
        if normalized not in self.providers:
            raise ValueError(f"Unsupported provider: {provider_name}")
        global _PROVIDER_OVERRIDE
        _PROVIDER_OVERRIDE = normalized
        return normalized

    def get_provider(self):
        return self.providers[self.get_selected_provider_name()]

    def run_ocr(self, file_bytes: bytes, filename: str, content_type: str) -> OCRProviderResult:
        selected = self.get_selected_provider_name()
        ordered = [selected] + (["ollama"] if selected == "remote" else [])
        last_result: OCRProviderResult | None = None
        for name in ordered:
            result = self.providers[name].recognize(file_bytes=file_bytes, filename=filename, content_type=content_type)
            if result.success:
                return result
            last_result = result
        if last_result is None:
            raise RuntimeError("No OCR providers available")
        return last_result

    def list_providers(self) -> list[dict[str, Any]]:
        selected = self.get_selected_provider_name()
        return [{"name": name, "selected": name == selected} for name in self.providers.keys()]

    def health_status(self) -> dict[str, Any]:
        selected = self.get_selected_provider_name()
        providers = {}
        for name, provider in self.providers.items():
            providers[name] = provider.health_check()
        return {"success": True, "selected_provider": selected, "providers": providers}
