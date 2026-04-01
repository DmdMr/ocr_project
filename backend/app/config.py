import os
from dataclasses import dataclass
from pathlib import Path


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    environment: str
    mongo_url: str
    mongo_db_name: str
    upload_dir: str
    secret_key: str
    frontend_origins: list[str]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_allow_origins(self) -> list[str]:
        if self.is_production:
            return self.frontend_origins
        return self.frontend_origins or [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]


def load_settings() -> Settings:
    environment = os.getenv("ENVIRONMENT", "development").strip().lower()
    mongo_url = os.getenv("MONGO_URL", "mongodb://127.0.0.1:27017").strip()
    mongo_db_name = os.getenv("MONGO_DB_NAME", "ocr_database").strip()
    upload_dir = os.getenv("UPLOAD_DIR", "backend/uploads").strip()
    secret_key = os.getenv("SECRET_KEY", "").strip()
    frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173,http://127.0.0.1:5173")
    frontend_origins = _split_csv(frontend_origin)

    if environment == "production" and not secret_key:
        raise RuntimeError("SECRET_KEY must be set when ENVIRONMENT=production")
    if environment == "production" and not frontend_origins:
        raise RuntimeError("FRONTEND_ORIGIN must be set when ENVIRONMENT=production")

    upload_path = Path(upload_dir).expanduser().resolve()
    upload_path.mkdir(parents=True, exist_ok=True)

    return Settings(
        environment=environment,
        mongo_url=mongo_url,
        mongo_db_name=mongo_db_name,
        upload_dir=str(upload_path),
        secret_key=secret_key,
        frontend_origins=frontend_origins,
    )


settings = load_settings()
