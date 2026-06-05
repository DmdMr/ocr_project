from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "backend.app.main:app",
        host=host,
        port=port,
        log_level=os.getenv("UVICORN_LOG_LEVEL", "info"),
        workers=1,
    )


if __name__ == "__main__":
    main()
