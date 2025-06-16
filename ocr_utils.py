# ocr_utils.py
import easyocr
import re

# Initialize the reader once
reader = easyocr.Reader(['en'], gpu=False) # Set gpu=True if you have a compatible GPU

def clean_text(text):
    """Cleans the OCR text to keep only alphanumeric characters."""
    return re.sub(r'[^A-Z0-9]', '', text).upper()

def get_plate_from_image(image):
    """
    Takes a CV2 image, performs OCR, and returns the cleaned plate text and confidence.
    """
    results = reader.readtext(image)
    if not results:
        return None, 0.0

    # Find the result with the highest confidence
    best_result = max(results, key=lambda r: r[2])
    plate_text = clean_text(best_result[1])
    confidence = best_result[2]

    # Basic validation for plate-like text (e.g., length)
    if 4 <= len(plate_text) <= 10:
        return plate_text, confidence
    return None, 0.0