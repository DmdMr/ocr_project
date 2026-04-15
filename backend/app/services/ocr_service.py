from typing import Any, Dict

from backend.app.services.paddle_ocr_service import get_paddle_ocr_service, validate_image_file


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

    recognized_text = result.get("recognized_text", "")
    return {
        "text": recognized_text,
        "recognized_text": recognized_text,
        "boxes": [],
        "top_code": result.get("top_code"),
        "ocr_lines": result.get("ocr_lines", []),
        "confidence": result.get("confidence"),
    }


def recognize_top_code(image_path: str) -> Dict[str, Any]:
    """Utility method for future field-based OCR calls."""
    validate_image_file(image_path)
    service = get_paddle_ocr_service()
    return service.ocr_top_code_region(image_path)
