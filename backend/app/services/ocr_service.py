from typing import Any, Dict

import numpy as np

from backend.app.services.paddle_ocr_service import get_paddle_ocr_service, validate_image_file


def _to_plain_python(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _to_plain_python(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_plain_python(item) for item in value]
    if isinstance(value, tuple):
        return [_to_plain_python(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def _normalize_ocr_result(raw_result: Dict[str, Any]) -> Dict[str, Any]:
    safe_result = _to_plain_python(raw_result or {})
    recognized_text = str(safe_result.get("recognized_text") or "")
    top_code = safe_result.get("top_code")
    ocr_lines = safe_result.get("ocr_lines")
    if not isinstance(ocr_lines, list):
        ocr_lines = []
    confidence = safe_result.get("confidence")
    if confidence is not None:
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = None
    top_region = safe_result.get("top_region")
    if top_region is not None and not isinstance(top_region, dict):
        top_region = None

    return {
        "text": recognized_text,
        "recognized_text": recognized_text,
        "boxes": [],
        "top_code": str(top_code) if top_code is not None else None,
        "ocr_lines": ocr_lines,
        "confidence": confidence,
        "top_region": top_region,
    }


def recognize_text(image_path: str) -> Dict[str, Any]:
    """
    Backward-compatible OCR wrapper used by routes.
    Returns at minimum:
      - text
      - boxes
    Extended fields:
      - recognized_text
      - top_code
      - ocr_lines
      - confidence
    """
    validate_image_file(image_path)
    service = get_paddle_ocr_service()
    result = service.run_ocr(image_path)
    return _normalize_ocr_result(result)


def recognize_top_code(image_path: str) -> Dict[str, Any]:
    """Utility method for future field-based OCR calls."""
    validate_image_file(image_path)
    service = get_paddle_ocr_service()
    return service.ocr_top_code_region(image_path)
