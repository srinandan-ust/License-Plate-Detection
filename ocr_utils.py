# raspberry_pi_code/ocr_utils.py
import easyocr
import re

class OCRProcessor:
    def __init__(self, languages=['en'], gpu=False):
        print("Initializing EasyOCR reader...")
        self.reader = easyocr.Reader(languages, gpu=gpu)
        print("EasyOCR reader initialized.")

    def _clean_text(self, text):
        # Basic cleaning: alphanumeric, uppercase. Adapt as needed.
        cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())
        return cleaned

    def detect_plate(self, image):
        """
        Detects text in an image and tries to identify a license plate.
        Returns: (plate_text, confidence) or (None, None) if no suitable plate found.
        """
        if image is None:
            return None, None
            
        try:
            results = self.reader.readtext(image)
            if not results:
                return None, None

            # For simplicity, assume the best candidate is the one with highest confidence
            # or some heuristic (e.g. longest alphanumeric string).
            # This logic can be significantly improved.
            best_plate = None
            max_confidence = 0.0

            for (bbox, text, prob) in results:
                cleaned_text = self._clean_text(text)
                # Add heuristics for what a plate looks like (e.g., length)
                if len(cleaned_text) >= 4 and len(cleaned_text) <= 10: # Example length check
                    if prob > max_confidence:
                        max_confidence = prob
                        best_plate = cleaned_text
            
            if best_plate:
                return best_plate, max_confidence
            else:
                return None, None

        except Exception as e:
            print(f"Error during OCR processing: {e}")
            return None, None

if __name__ == '__main__':
    # This requires an image file for testing, or a running camera feed
    # For now, this is a conceptual test
    processor = OCRProcessor()
    print("OCRProcessor ready. (No image provided for direct test here)")
    # To test properly, you'd need:
    # import cv2
    # img = cv2.imread("path_to_test_image.jpg")
    # plate, conf = processor.detect_plate(img)
    # print(f"Detected: {plate}, Confidence: {conf}")