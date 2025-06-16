# raspberry_pi_code/main_pi.py
import cv2
import time
from datetime import datetime
import threading # For running Flask server in background

# Import utility modules
from camera_utils import Camera
from ocr_utils import OCRProcessor
from db_utils import DatabaseManager
from log_utils import setup_file_logger, LogDBManager
from mqtt_utils import MQTTClient
from tb_client import ThingsboardClient
from flask_server import run_flask_server # Import the function to run Flask

# --- Configuration (Consider moving to a config.py or using environment variables) ---
# MQTT Broker Settings

MQTT_BROKER_HOST = "192.168.127.169"  # Replace! e.g., "localhost" or actual IP
MQTT_BROKER_PORT = 1883
MQTT_TOPIC_PLATES = "rpi/license_plates"

# Thingsboard Settings
#mosquitto_pub -d -q 1 -h mqtt.thingsboard.cloud -p 1883 -t v1/devices/me/telemetry -u "k0NlFw3ZFTkXqjm8tsLN" -m "{temperature:25}"
#curl -v -X POST http://thingsboard.cloud/api/v1/aaFRkbzTxvZr8vwbtsBC/telemetry --header Content-Type:application/json --data "{temperature:25}"
THINGSBOARD_HOST = "mqtt.thingsboard.cloud" # Replace! e.g., "localhost" or "demo.thingsboard.io"
THINGSBOARD_PORT = 1883
DEVICE_ACCESS_TOKEN = "aaFRkbzTxvZr8vwbtsBC" # Replace!

# Database and Log Paths
PLATES_DB_PATH = "detected_plates.db"
LOG_DB_PATH = "event_logs.db"
LOG_FILE_PATH = "app.log"

# Camera Settings
CAMERA_INDEX = 0 # 0 for default USB webcam

# Flask Server Settings
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000

# OCR Settings
OCR_GPU = False # Set to True if you have a compatible GPU and EasyOCR GPU support installed

# --- Global Variables / Flags ---
# For future control (e.g., via Flask or MQTT command topic)
processing_enabled = True 
# ---

def main():
    global processing_enabled

    # 1. Initialize Loggers
    file_logger = setup_file_logger(LOG_FILE_PATH)
    log_db_manager = LogDBManager(LOG_DB_PATH)
    
    file_logger.info("System startup: Initializing components.")
    log_db_manager.log_event("INFO", "System startup: Initializing components.")

    # 2. Initialize Camera
    camera = Camera(camera_index=CAMERA_INDEX)
    if not camera.cap:
        file_logger.error("Failed to initialize camera. Exiting.")
        log_db_manager.log_event("ERROR", "Failed to initialize camera. Exiting.")
        return

    # 3. Initialize OCR Processor
    try:
        ocr_processor = OCRProcessor(gpu=OCR_GPU)
    except Exception as e:
        file_logger.error(f"Failed to initialize OCR Processor: {e}. Exiting.")
        log_db_manager.log_event("ERROR", f"Failed to initialize OCR Processor: {e}. Exiting.")
        camera.release()
        return

    # 4. Initialize Plate Database Manager
    plate_db_manager = DatabaseManager(db_path=PLATES_DB_PATH)

    # 5. Initialize MQTT Client for general publishing
    mqtt_publisher = MQTTClient(MQTT_BROKER_HOST, MQTT_BROKER_PORT)
    mqtt_publisher.connect()

    # 6. Initialize Thingsboard Client
    tb_cli = None
    if DEVICE_ACCESS_TOKEN and DEVICE_ACCESS_TOKEN != "YOUR_DEVICE_ACCESS_TOKEN":
        tb_cli = ThingsboardClient(THINGSBOARD_HOST, THINGSBOARD_PORT, DEVICE_ACCESS_TOKEN)
        tb_cli.connect()
    else:
        file_logger.warning("ThingsBoard Access Token not set. ThingsBoard client will not be initialized.")
        log_db_manager.log_event("WARNING", "ThingsBoard Access Token not set. ThingsBoard client inactive.")

    # 7. Start Flask server in a separate thread
    # This allows the main loop to continue processing frames
    flask_thread = threading.Thread(target=run_flask_server, 
                                    args=(FLASK_HOST, FLASK_PORT), 
                                    kwargs={'debug': False}, # Important: use_reloader=False is default in imported func
                                    daemon=True) # Daemon thread exits when main program exits
    flask_thread.start()
    file_logger.info(f"Flask server started in a background thread on http://{FLASK_HOST}:{FLASK_PORT}")
    log_db_manager.log_event("INFO", f"Flask server started on http://{FLASK_HOST}:{FLASK_PORT}")


    # --- Main Processing Loop ---
    file_logger.info("Starting main processing loop.")
    log_db_manager.log_event("INFO", "Starting main processing loop.")
    
    try:
        while processing_enabled:
            frame = camera.get_frame()
            if frame is None:
                file_logger.warning("Failed to get frame from camera. Skipping iteration.")
                log_db_manager.log_event("WARNING", "Failed to get frame from camera.")
                time.sleep(1) # Wait a bit before retrying
                continue

            # --- OCR Processing ---
            # For performance, you might want to process frames at a lower rate than capture rate
            # e.g., process every Nth frame or use a timer.
            plate_text, confidence = ocr_processor.detect_plate(frame)

            if plate_text:
                current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                file_logger.info(f"Plate Detected: {plate_text}, Confidence: {confidence:.2f}")
                log_db_manager.log_event("INFO", f"Plate Detected: {plate_text}, Confidence: {confidence:.2f}")

                # 1. Save to SQLite Plate Database
                plate_db_manager.save_plate(plate_text, confidence)

                # 2. Prepare MQTT Payload
                payload = {
                    "plate": plate_text,
                    "timestamp": current_time_str,
                    "confidence": round(confidence, 4) if confidence else None
                }

                # 3. Publish to general MQTT topic
                if mqtt_publisher.connected:
                    mqtt_publisher.publish(MQTT_TOPIC_PLATES, payload)
                else:
                    file_logger.warning("MQTT publisher not connected. Could not send plate data.")
                    # Attempt to reconnect MQTT publisher if disconnected
                    if not mqtt_publisher.connected:
                        mqtt_publisher.connect()


                # 4. Publish to Thingsboard
                if tb_cli and tb_cli.connected:
                    # Thingsboard expects simple key-value for telemetry
                    tb_payload = {"plate": plate_text, "confidence": round(confidence, 2) if confidence else 0.0}
                    tb_cli.publish_telemetry(tb_payload)
                elif tb_cli and not tb_cli.connected:
                    file_logger.warning("ThingsBoard client not connected. Could not send telemetry.")
                    # Attempt to reconnect TB client if disconnected
                    tb_cli.connect()


            # Control processing rate (e.g., process 1 frame per second)
            time.sleep(0.5) # Adjust as needed for performance/CPU usage

            # (Optional) Display frame with detections for local debugging
            # cv2.imshow("Frame", frame) # Needs a display server (X11)
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     processing_enabled = False # Allow quitting via 'q' key if display is on
            #     break

    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Shutting down...")
        file_logger.info("KeyboardInterrupt: System shutting down.")
        log_db_manager.log_event("INFO", "KeyboardInterrupt: System shutting down.")
    except Exception as e:
        file_logger.error(f"An unhandled exception occurred in main loop: {e}", exc_info=True)
        log_db_manager.log_event("ERROR", f"Unhandled exception in main loop: {e}")
    finally:
        # --- Cleanup ---
        file_logger.info("Performing cleanup operations.")
        log_db_manager.log_event("INFO", "Performing cleanup operations.")

        processing_enabled = False # Ensure loop terminates if error occurred

        if camera:
            camera.release()
            file_logger.info("Camera released.")
        
        if mqtt_publisher:
            mqtt_publisher.disconnect()
            file_logger.info("MQTT publisher disconnected.")

        if tb_cli:
            tb_cli.disconnect()
            file_logger.info("ThingsBoard client disconnected.")
        
        # Flask thread is a daemon, will exit when main thread exits.
        # No explicit stop needed here for daemon threads.

        # if 'cv2' in globals() and cv2.getWindowProperty("Frame", 0) >= 0: # Check if window exists
        #    cv2.destroyAllWindows()

        file_logger.info("System shutdown complete.")
        log_db_manager.log_event("INFO", "System shutdown complete.")
        print("System shutdown complete.")

if __name__ == "__main__":
    # Critical: Replace placeholders in CONFIGURATION section above before running!
    if MQTT_BROKER_HOST == "your_mqtt_broker_ip" or \
       THINGSBOARD_HOST == "your_thingsboard_host_or_ip" or \
       (DEVICE_ACCESS_TOKEN == "YOUR_DEVICE_ACCESS_TOKEN" and THINGSBOARD_HOST != "your_thingsboard_host_or_ip"): # Allow if TB not used
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! CRITICAL: Please update placeholder values in main_pi.py configuration section !!!")
        print("!!! (MQTT_BROKER_HOST, THINGSBOARD_HOST, DEVICE_ACCESS_TOKEN)            !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    else:
        main()