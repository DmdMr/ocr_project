from typing import Any, Dict

from backend.app.services.trocr_service import run_trocr
from backend.app.services.paddle_ocr_service import validate_image_file


def recognize_text(image_path: str) -> Dict[str, Any]:
    """
    OCR using TrOCR (local model).
    """

    validate_image_file(image_path)

    try:
        result = run_trocr(image_path)

        text = result.get("text", "")
        lines = result.get("ocr_lines", [])

    except Exception as e:
        raise RuntimeError(f"OCR failed: {str(e)}")

    return {
        "text": text,
        "recognized_text": text,
        "boxes": result.get("boxes", []),
        "top_code": None,
        "ocr_lines": lines,
        "confidence": None
    }


def recognize_top_code(image_path: str) -> Dict[str, Any]:
    """
    Not supported with TrOCR yet.
    """

    validate_image_file(image_path)

    return {
        "text": "",
        "top_code": None,
        "ocr_lines": []
    }