from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "OCR Project"
APP_DIR_NAME = "ocr-project"


def _default_user_data_dir() -> Path:
    if sys.platform == "win32":
        base = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / APP_DIR_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path(os.getenv("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))) / APP_DIR_NAME


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_dir(env_name: str, fallback: Path, *, create: bool = True) -> Path:
    value = os.getenv(env_name)
    resolved = Path(value).expanduser() if value else fallback
    resolved = resolved.resolve()
    if create:
        resolved.mkdir(parents=True, exist_ok=True)
    return resolved


USER_DATA_DIR = _resolve_dir("OCR_APP_DATA_DIR", _default_user_data_dir())
RESOURCE_DIR = _resolve_dir("OCR_APP_RESOURCES_DIR", _project_root(), create=False)

UPLOAD_DIR = _resolve_dir("UPLOAD_DIR", USER_DATA_DIR / "uploads")
DATA_DIR = _resolve_dir("OCR_DATA_DIR", USER_DATA_DIR / "data")
LOG_DIR = _resolve_dir("AUDIT_LOG_DIR", USER_DATA_DIR / "logs")
DATASET_DIR = _resolve_dir("OCR_DATASET_DIR", USER_DATA_DIR / "dataset")
MODEL_DIR = _resolve_dir("OCR_MODEL_DIR", RESOURCE_DIR / "backend" / "models", create=False)

DB_PATH = Path(os.getenv("SQLITE_DB_PATH", str(DATA_DIR / "ocr_app.db"))).expanduser().resolve()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

AI_OCR_CONFIG_PATH = Path(os.getenv("AI_OCR_CONFIG_PATH", str(DATA_DIR / "ai_ocr_config.json"))).expanduser().resolve()
AI_OCR_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

OCR_HISTORY_PATH = Path(os.getenv("OCR_HISTORY_PATH", str(DATA_DIR / "ocr_history.jsonl"))).expanduser().resolve()
OCR_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)

TRAINING_DATA_PATH = Path(os.getenv("OCR_TRAINING_DATA_PATH", str(DATA_DIR / "training.jsonl"))).expanduser().resolve()
TRAINING_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

FRONTEND_DIST_DIR = Path(os.getenv("FRONTEND_DIST_DIR", str(RESOURCE_DIR / "frontend" / "dist"))).expanduser().resolve()
