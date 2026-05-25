from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from backend.app.services.ollama_client import check_health as ollama_check_health
from backend.app.services.ollama_client import pull_model as ollama_pull_model
from backend.app.services.remote_vision_client import test_connection as remote_test_connection

from backend.app.services.ocr.providers.remote_provider import RemoteOCRProvider
from backend.app.services.ocr.providers.ollama_provider import OllamaOCRProvider


@dataclass
class OCRConfig:
    provider: str = "remote"
    remote_url: str = "http://111.88.113.136:8000/ocr"
    ollama_model: str = "qwen3-vl:2b"
    timeout: int = 60


class ProviderManager:
    def __init__(self) -> None:
        self.config_path = Path(os.getenv("AI_OCR_CONFIG_PATH", "backend/data/ai_ocr_config.json"))
        self.providers = {
            "remote": RemoteOCRProvider(),
#            "ollama": OllamaOCRProvider(),
        }

    def load_config(self) -> dict[str, Any]:
        config = OCRConfig(
            provider=os.getenv("VISION_OCR_PROVIDER", "remote"),
            remote_url=os.getenv("REMOTE_VISION_OCR_URL", "http://111.88.113.136:8000/ocr"),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen3-vl:2b"),
            timeout=int(os.getenv("REMOTE_VISION_OCR_TIMEOUT_SECONDS", "60")),
        )
        if self.config_path.exists():
            try:
                payload = json.loads(self.config_path.read_text(encoding="utf-8"))
                config.provider = payload.get("provider", config.provider)
                config.remote_url = payload.get("remote_url", config.remote_url)
                config.ollama_model = payload.get("ollama_model", config.ollama_model)
                config.timeout = int(payload.get("timeout", config.timeout))
            except Exception:
                pass
        return asdict(config)

    def save_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        current = self.load_config()
        next_config = {
            "provider": (payload.get("provider") or current["remote"]).strip().lower(),
            "remote_url": (payload.get("remote_url") or current["remote_url"]).strip(),
            "ollama_model": (payload.get("ollama_model") or current["ollama_model"]).strip(),
            "timeout": int(payload.get("timeout", current["timeout"])),
        }
        if next_config["provider"] not in {"remote", "ollama"}:
            raise ValueError("Unsupported provider")
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(next_config, ensure_ascii=False, indent=2), encoding="utf-8")
        return next_config

    def ollama_status(self) -> dict[str, Any]:
        config = self.load_config()
        model_name = config["ollama_model"]
        installed = shutil.which("ollama") is not None
        running = False
        models: list[str] = []
        vision_capable = False
        if installed:
            try:
                ps = subprocess.run(["ollama", "ps"], capture_output=True, text=True, timeout=5)
                running = ps.returncode == 0
            except Exception:
                running = False
            try:
                listed = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
                if listed.returncode == 0:
                    lines = listed.stdout.splitlines()[1:]
                    models = [line.split()[0] for line in lines if line.strip()]
            except Exception:
                models = []
        model_installed = model_name in models
        vision_capable = any("vl" in m.lower() or "vision" in m.lower() for m in models)
        health = ollama_check_health()
        return {
            "installed": installed,
            "running": running and bool(health.get("success")),
            "model_installed": model_installed,
            "model_name": model_name,
            "installed_models": models,
            "vision_capable": vision_capable,
            "health": health,
        }

    def list_ollama_models(self) -> dict[str, Any]:
        status = self.ollama_status()
        return {
            "installed": status.get("installed", False),
            "running": status.get("running", False),
            "models": status.get("installed_models", []),
            "active_model": self.load_config().get("ollama_model", "qwen3-vl:2b"),
        }

    def pull_ollama_model(self, model_name: str | None = None) -> dict[str, Any]:
        chosen = model_name or self.load_config()["ollama_model"]
        return ollama_pull_model(chosen)

    def set_active_ollama_model(self, model_name: str) -> dict[str, Any]:
        config = self.load_config()
        config["provider"] = "ollama"
        config["ollama_model"] = (model_name or "").strip() or config.get("ollama_model", "qwen3-vl:2b")
        return self.save_config(config)

    def test_ollama(self) -> dict[str, Any]:
        return self.ollama_status()

    def remote_status(self) -> dict[str, Any]:
        config = self.load_config()
        started = time.perf_counter()
        result = remote_test_connection(url=config["remote_url"], timeout=config["timeout"])
        latency_ms = int((time.perf_counter() - started) * 1000)
        result["latency_ms"] = result.get("latency_ms") or latency_ms
        return result
    
    def get_provider(self, name: str):
        return self.providers[name]
    
    def run_ocr(self, file_bytes: bytes, filename: str, content_type: str):
        config = self.load_config()
        provider_name = config.get("provider", "remote")

        provider = self.get_provider(provider_name)

        return provider.recognize(
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type
        )


provider_manager = ProviderManager()
