import os
import cv2
import numpy as np
from typing import Any, Dict
from transformers import TrOCRProcessor, ViTImageProcessor, AutoTokenizer, VisionEncoderDecoderModel
from PIL import Image

# Use PaddleOCR's underlying detector engine to find text line regions
from paddleocr import PaddleOCR

from backend.app.services.paddle_ocr_service import validate_image_file

# Configuration
FINE_TUNED_DIR = "/Users/demidmurakhin/Desktop/ocr_project/backend/models/fine_tuned_russian_trocr"

# Initialise TrOCR components globally once to keep performance high
print("Loading fine-tuned Russian TrOCR model...")

# Load components individually to bypass the Hugging Face configuration conflict
ft_image_processor = ViTImageProcessor.from_pretrained(FINE_TUNED_DIR)
ft_tokenizer = AutoTokenizer.from_pretrained(FINE_TUNED_DIR)

# Construct the processor manually in memory
processor = TrOCRProcessor(image_processor=ft_image_processor, tokenizer=ft_tokenizer)
model = VisionEncoderDecoderModel.from_pretrained(FINE_TUNED_DIR)

# Initialise PaddleOCR detector (PaddleOCR maps internal components cleanly via default language configuration flags)
print("Loading PaddleOCR text detector...")
detector = PaddleOCR(use_angle_cls=False, lang='ru')


def run_trocr_on_crop(cropped_image: Image.Image) -> str:
    """
    Inference helper running your local fine-tuned TrOCR on a single text line crop.
    """
    # Convert image to RGB channel format expected by TrOCR
    if cropped_image.mode != "RGB":
        cropped_image = cropped_image.convert("RGB")
        
    pixel_values = processor(images=cropped_image, return_tensors="pt").pixel_values
    generated_ids = model.generate(pixel_values)
    generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return generated_text.strip()


def recognize_text(image_path: str) -> Dict[str, Any]:
    """
    Multi-line OCR using PaddleOCR for line segment detection 
    and your local fine-tuned TrOCR model for text generation.
    """
    validate_image_file(image_path)

    try:
        # 1. Load image using OpenCV for manipulation and PIL for TrOCR compatibility
        cv_img = cv2.imread(image_path)
        if cv_img is None:
            raise FileNotFoundError(f"Cannot load image at {image_path}")
            
        pil_img = Image.open(image_path)

        # 2. Detect text line bounding boxes using PaddleOCR
    

                # 2. Detect text line bounding boxes using PaddleOCR
                # 2. Detect text line bounding boxes using PaddleOCR
        detection_result = detector.ocr(image_path)
        
        lines = []
        boxes_out = []
        all_texts = []

        # STRICT STRUCTURAL CHECK: Ensure PaddleOCR returned a valid nested list structure
        if not detection_result or not isinstance(detection_result, list) or not detection_result[0]:
            print(f"Warning: PaddleOCR returned no readable data layout for {image_path}")
            return {
                "text": "",
                "recognized_text": "",
                "boxes": [],
                "top_code": None,
                "ocr_lines": [],
                "confidence": None
            }

        # Filter out any malformed entries that aren't lists/tuples to prevent lambda sorting index crashes
        valid_entries = []
        for entry in detection_result[0]:
            try:
                # Test if we can safely traverse down to the y-coordinate entry[0][0][1]
                if isinstance(entry, (list, tuple)) and len(entry) > 0:
                    if isinstance(entry[0], (list, tuple)) and len(entry[0]) > 0:
                        if isinstance(entry[0][0], (list, tuple)) and len(entry[0][0]) > 1:
                            valid_entries.append(entry)
            except Exception:
                continue

        # Fallback if no elements pass the structural data test
        if not valid_entries:
            print(f"Warning: Zero entries matched the structural coordinate layout in {image_path}")
            return {
                "text": "",
                "recognized_text": "",
                "boxes": [],
                "top_code": None,
                "ocr_lines": [],
                "confidence": None
            }

        # Now we sort using only completely verified layouts
        sorted_entries = sorted(valid_entries, key=lambda entry: entry[0][0][1])

        for i, entry in enumerate(sorted_entries):


                # Isolate just the 4-point bounding box coordinates array 
                box = entry[0] 
                
                # Format box points into an integer bounding rectangle layout matrix
                pts = np.array(box, dtype=np.int32)
                x, y, w, h = cv2.boundingRect(pts)
                
                # Enforce safe boundaries within image limits
                img_h, img_w = cv_img.shape[:2]
                x_min, y_min = max(0, x), max(0, y)
                x_max, y_max = min(img_w, x + w), min(img_h, y + h)

                if (x_max - x_min) < 2 or (y_max - y_min) < 2:
                    continue

                # 3. Crop out the individual text line
                cropped_pil = pil_img.crop((x_min, y_min, x_max, y_max))

                # 4. Perform localized line recognition using your 93% accuracy TrOCR model
                recognized_line_text = run_trocr_on_crop(cropped_pil)
                
                if recognized_line_text:
                    all_texts.append(recognized_line_text)
                    
                    # Construct lines dictionary payload
                    lines.append({
                        "line_number": i + 1,
                        "text": recognized_line_text,
                        "box": [x_min, y_min, x_max, y_max]
                    })
                    
                    # Store plain box representation
                    boxes_out.append([x_min, y_min, x_max, y_max])


        # Combine all lines cleanly into a single string output separated by linebreaks
        combined_text = "\n".join(all_texts)

    except Exception as e:
        raise RuntimeError(f"OCR Pipeline failed: {str(e)}")

    return {
        "text": combined_text,
        "recognized_text": combined_text,
        "boxes": boxes_out,
        "top_code": None,
        "ocr_lines": lines,
        "confidence": None
    }


def recognize_top_code(image_path: str) -> Dict[str, Any]:
    """
    Extracts the topmost text string found in the document using TrOCR pipeline.
    """
    validate_image_file(image_path)
    
    result = recognize_text(image_path)
    ocr_lines = result.get("ocr_lines", [])
    
    # Return the first sorted line text as top_code string frame value
    top_code_text = ocr_lines[0]["text"] if ocr_lines else ""

    return {
        "text": top_code_text,
        "top_code": top_code_text,
        "ocr_lines": ocr_lines
    }
