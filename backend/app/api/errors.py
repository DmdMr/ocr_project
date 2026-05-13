import logging
from typing import Mapping

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("backend.errors")

ERROR_MESSAGES: dict[str, str] = {
    "OCR_FAILURE": "OCR failure",
    "INVALID_IMAGE": "Invalid image",
    "FILE_TOO_LARGE": "File too large",
    "NETWORK_ERROR": "Network error",
    "AUTH_REQUIRED": "Authentication required",
    "INVALID_CREDENTIALS": "Invalid username or password",
    "ACCESS_DENIED": "Access denied",
    "VALIDATION_ERROR": "Invalid request",
    "NOT_FOUND": "Not found",
    "BAD_REQUEST": "Bad request",
    "INTERNAL_ERROR": "Internal server error",
}

STATUS_FALLBACK_CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "AUTH_REQUIRED",
    403: "ACCESS_DENIED",
    404: "NOT_FOUND",
    413: "FILE_TOO_LARGE",
    422: "VALIDATION_ERROR",
}


def error_payload(error_code: str, message: str | None = None) -> dict[str, str]:
    return {
        "error_code": error_code,
        "message": message or ERROR_MESSAGES.get(error_code, ERROR_MESSAGES["INTERNAL_ERROR"]),
    }


def api_error(status_code: int, error_code: str, message: str | None = None) -> HTTPException:
    return HTTPException(status_code=status_code, detail=error_payload(error_code, message))


def payload_from_http_exception(exc: HTTPException) -> dict[str, str]:
    detail = exc.detail
    if isinstance(detail, Mapping) and detail.get("error_code"):
        return error_payload(str(detail["error_code"]), str(detail.get("message") or ""))

    fallback_code = STATUS_FALLBACK_CODES.get(exc.status_code, "INTERNAL_ERROR")
    return error_payload(fallback_code)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    payload = payload_from_http_exception(exc)
    return JSONResponse(status_code=exc.status_code, content=payload, headers=exc.headers)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning("Request validation failed for %s %s: %s", request.method, request.url.path, exc.errors())
    return JSONResponse(status_code=422, content=error_payload("VALIDATION_ERROR"))


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled API error for %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content=error_payload("INTERNAL_ERROR"))
