from doctr.models import ocr_predictor
from PIL import Image
import numpy as np

# модель загружается один раз при старте
model = ocr_predictor(pretrained=True)

def recognize_text(image_path: str) -> str:
    img = Image.open(image_path).convert("RGB")
    img_array = np.array(img)

    result = model([img_array])

    text = ""
    for page in result.pages:
        for block in page.blocks:
            for line in block.lines:
                words = [word.value for word in line.words]
                text += " ".join(words) + "\n"

    return text.strip()
