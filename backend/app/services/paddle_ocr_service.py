import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

import cv2
import numpy as np
from PIL import Image


@dataclass
class OcrLine:
    text: str
    confidence: Optional[float] = None


def _safe_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class PaddleOcrService:
    def __init__(self) -> None:
        self._ocr_engine = None
        self.top_crop_ratio = float(os.getenv("PADDLE_TOP_CROP_RATIO", "0.30"))

    def _get_engine(self):
        if self._ocr_engine is not None:
            return self._ocr_engine

        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise RuntimeError(
                "PaddleOCR dependency is missing. Install paddleocr and paddlepaddle."
            ) from exc

        lang = os.getenv("PADDLE_OCR_LANG", "ru")
        use_angle_cls = os.getenv("PADDLE_OCR_USE_ANGLE_CLS", "true").lower() == "true"
        self._ocr_engine = PaddleOCR(use_angle_cls=use_angle_cls, lang=lang)
        return self._ocr_engine

    def _read_image(self, image_path: str) -> np.ndarray:
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError("Invalid image file")
        return image

    def _crop_top_region(self, image: np.ndarray, crop_ratio: Optional[float] = None) -> np.ndarray:
        ratio = crop_ratio if crop_ratio is not None else self.top_crop_ratio
        ratio = max(0.1, min(ratio, 0.8))
        height = image.shape[0]
        crop_height = max(1, int(height * ratio))
        return image[:crop_height, :]

    def _preprocess_top_region(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        enlarged = cv2.resize(gray, None, fx=1.7, fy=1.7, interpolation=cv2.INTER_CUBIC)
        denoised = cv2.GaussianBlur(enlarged, (3, 3), 0)
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

    def _ocr_image_array(self, image: np.ndarray) -> List[OcrLine]:
        engine = self._get_engine()
        result = engine.ocr(image, cls=True)

        lines: List[OcrLine] = []
        for block in result or []:
            for entry in block or []:
                if not entry or len(entry) < 2:
                    continue
                rec = entry[1]
                if not isinstance(rec, (list, tuple)) or not rec:
                    continue
                text = str(rec[0]).strip()
                if not text:
                    continue
                confidence = _safe_float(rec[1] if len(rec) > 1 else None)
                lines.append(OcrLine(text=text, confidence=confidence))
        return lines

    @staticmethod
    def _normalize_candidate(text: str) -> str:
        normalized = text or ""
        normalized = normalized.replace("О", "0").replace("о", "0")
        normalized = normalized.replace("O", "0").replace("o", "0")
        normalized = normalized.replace(",", ".")
        normalized = normalized.replace(" ", "")
        normalized = re.sub(r"[^0-9.]", "", normalized)
        return normalized

    def extract_top_code_candidate(self, lines: Sequence[str]) -> Optional[str]:
        dotted_pattern = re.compile(r"\b\d{2}[.]\d{3}[.]\d{3}\b")
        numeric_pattern = re.compile(r"\b\d{5,8}\b")

        normalized_lines = [self._normalize_candidate(line) for line in lines if line]

        for line in normalized_lines:
            match = dotted_pattern.search(line)
            if match:
                return match.group(0)

        for line in normalized_lines:
            match = numeric_pattern.search(line)
            if match:
                return match.group(0)

        return None

    def ocr_top_code_region(self, image_path: str, crop_ratio: Optional[float] = None) -> Dict[str, Any]:
        image = self._read_image(image_path)
        top_region = self._crop_top_region(image, crop_ratio=crop_ratio)
        preprocessed = self._preprocess_top_region(top_region)
        top_lines = self._ocr_image_array(preprocessed)

        top_texts = [line.text for line in top_lines]
        best_top_code = self.extract_top_code_candidate(top_texts)
        avg_confidence = None
        confidences = [line.confidence for line in top_lines if line.confidence is not None]
        if confidences:
            avg_confidence = float(sum(confidences) / len(confidences))

        return {
            "top_code": best_top_code,
            "ocr_lines": [{"text": line.text, "confidence": line.confidence} for line in top_lines],
            "recognized_text": "\n".join(top_texts),
            "confidence": avg_confidence,
        }

    def run_ocr(self, image_path: str, crop_ratio: Optional[float] = None) -> Dict[str, Any]:
        image = self._read_image(image_path)

        full_lines = self._ocr_image_array(image)
        full_text_lines = [line.text for line in full_lines]
        full_confidences = [line.confidence for line in full_lines if line.confidence is not None]
        full_confidence = None
        if full_confidences:
            full_confidence = float(sum(full_confidences) / len(full_confidences))

        top_result = self.ocr_top_code_region(image_path, crop_ratio=crop_ratio)

        return {
            "top_code": top_result.get("top_code"),
            "recognized_text": "\n".join(full_text_lines),
            "ocr_lines": [{"text": line.text, "confidence": line.confidence} for line in full_lines],
            "confidence": full_confidence,
            "top_region": top_result,
        }


def validate_image_file(image_path: str) -> None:
    try:
        with Image.open(image_path) as img:
            img.verify()
    except Exception as exc:  # pragma: no cover - defensive validation
        raise ValueError("Invalid image file") from exc


_service_instance: Optional[PaddleOcrService] = None


def get_paddle_ocr_service() -> PaddleOcrService:
    global _service_instance
    if _service_instance is None:
        _service_instance = PaddleOcrService()
    return _service_instance
