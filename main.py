# main.py
import cv2
import time
from datetime import datetime

from camera_utils import Camera
from ocr_utils import get_plate_from_image
from db_utils import init_db, add_plate_log
from log_utils import setup_logging

# --- Setup ---
logger = setup_logging()
init_db()
camera = Camera()
logger.info("System Initialized. Starting detection loop.")

# --- Main Loop ---
try:
    while True:
        ret, frame = camera.get_frame()
        if not ret:
            logger.warning("Failed to grab frame.")
            break

        # For efficiency, you might run detection every N frames
        # or when motion is detected. For now, we do it continuously.
        plate, confidence = get_plate_from_image(frame)

        if plate:
            print(f"Detected Plate: {plate} with confidence: {confidence:.2f}")
            logger.info(f"DETECTED: Plate={plate}, Confidence={confidence:.2f}")
            
            # Save a snapshot
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = f"logs/snapshot_{plate}_{timestamp_str}.jpg"
            cv2.imwrite(image_path, frame)
            
            # Log to database
            add_plate_log(plate, confidence, image_path)

        # Display the frame (optional, for debugging)
        cv2.imshow('License Plate Detection', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        time.sleep(0.1) # Small delay

except KeyboardInterrupt:
    logger.info("Program interrupted by user.")
finally:
    camera.release()
    cv2.destroyAllWindows()
    logger.info("System shutting down.")