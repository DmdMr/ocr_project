import requests

OCR_SERVER_URL = "http://111.88.113.136:8000/ocr"

def run_remote_ocr(image_path):

    with open(image_path, "rb") as f:

        response = requests.post(
            OCR_SERVER_URL,
            files={"file": f},
            timeout=120
        )

    return response.json()
