# ocr_service.py
from doctr.models import ocr_predictor
from PIL import Image
#from transformers import TrOCRProcessor, VisionEncoderDecoderModel
import torch
import numpy as np
import cv2

# ----------------------------
# Device setup for TrOCR
# ----------------------------
#DEVICE = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"

# ----------------------------
# Load models once
# ----------------------------
# DocTR for typed/printed text
doctr_model = ocr_predictor(pretrained=True)

# TrOCR for handwritten text
#processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
#trocr_model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten").to(DEVICE)

# ----------------------------
# Helper: detect if handwritten
# ----------------------------
"""

def is_handwritten(image_path: str, threshold: float = 0.02) -> bool:

    Simple heuristic: lower edge density -> likely handwriting.

    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    img = cv2.resize(img, (256, 256))
    edges = cv2.Canny(img, 100, 200)
    edge_density = np.sum(edges > 0) / edges.size
    return edge_density < threshold
"""
# ----------------------------
# OCR function
# ----------------------------
def recognize_text(image_path: str) -> dict:
    """
    Returns OCR result as a dictionary:
        {
            "text": "recognized text",
            "boxes": []  # empty for now
        }

    if is_handwritten(image_path):
        # Handwritten → TrOCR
        image = Image.open(image_path).convert("RGB")
        pixel_values = processor(images=image, return_tensors="pt").pixel_values.to(DEVICE)
        output_ids = trocr_model.generate(
            pixel_values,
            num_beams=5,
            max_length=256,
            early_stopping=True
        )
        text = processor.batch_decode(output_ids, skip_special_tokens=True)[0]
    """
        # Typed/printed → DocTR
    img = Image.open(image_path).convert("RGB")
    img_array = np.array(img)
    result = doctr_model([img_array])
    lines = []
    for page in result.pages:
        for block in page.blocks:
            for line in block.lines:
                words = [word.value for word in line.words]
                if words:
                    lines.append(" ".join(words))
    text = "\n".join(lines)

    return {
        "text": text,
        "boxes": []  
    }

# ----------------------------
# Example usage
# ----------------------------
if __name__ == "__main__":
    example_path = "example_image.png"
    result = recognize_text(example_path)
    print("Recognized text:\n", result["text"])