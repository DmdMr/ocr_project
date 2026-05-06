from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
import torch
import os

MODEL_PATH = "backend/models/trocr"

processor = TrOCRProcessor.from_pretrained(MODEL_PATH)
model = VisionEncoderDecoderModel.from_pretrained(MODEL_PATH)

device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)


def run_trocr(image_path: str):
    try:
        print("=== TROCR START ===")

        image = Image.open(image_path).convert("RGB")

        pixel_values = processor(images=image, return_tensors="pt").pixel_values.to(device)

        generated_ids = model.generate(
            pixel_values,
            max_new_tokens=100  
        )

        text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

        print("TROCR RESULT:", text)
        print("=== TROCR END ===")

        return {
            "text": text,
            "boxes": [],
            "ocr_lines": [{"text": text, "confidence": 1.0}]
        }

    except Exception as e:
        print("TROCR ERROR:", str(e))
        return {
            "text": "",
            "boxes": [],
            "ocr_lines": []
        }