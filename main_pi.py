import cv2
import time
from datetime import datetime
import logging
import threading

# Import for LED control
from gpiozero import LED, GPIOPinMissing # Import LED and error class
from gpiozero.exc import GPIOZeroError # Broader GPIOZero exceptions

# Import project modules
import ocr_utils
import db_utils
import log_utils
import mqtt_client_pi
import tb_client
import camera_utils
import flask_server

# --- Configuration (Copied from previous, ensure consistency) ---
# mosquitto_pub -d -q 1 -h mqtt.thingsboard.cloud -p 1883 -t v1/devices/me/telemetry -u "aaFRkbzTxvZr8vwbtsBC" -m "{temperature:25}"
DB_FILE = "detected_plates.db"
LOG_FILE = "app.log"
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_PLATE_TOPIC = "rpi/plate_detection/plate"
THINGSBOARD_HOST_MAIN = "mqtt.thingsboard.cloud"
THINGSBOARD_TOKEN_MAIN = "aaFRkbzTxvZr8vwbtsBC" # CRITICAL
CAMERA_ID = 0
FRAME_PROCESS_INTERVAL = 1 # seconds, for OCR processing
# --- LED Configuration ---
LED_PIN = 26  # BCM Pin GPIO26 (Physical Pin 37)
LED_CONFIDENCE_THRESHOLD = 0.60
# --- End Configuration ---

# Global variable for the latest frame for Flask streaming and its lock
latest_frame_for_flask_stream = None
frame_stream_lock = threading.Lock()

# Global LED object
plate_detected_led = None

def get_latest_frame_for_flask():
    """Provides the latest captured frame to Flask, thread-safe."""
    with frame_stream_lock:
        if latest_frame_for_flask_stream is not None:
            # Return a copy to prevent issues if the frame is modified elsewhere
            # or if Flask holds onto it for too long.
            return latest_frame_for_flask_stream.copy()
    return None

def blink_led_on_detection(led_object, times=2, on_time=0.2, off_time=0.2):
    """Blinks the LED a specified number of times."""
    if led_object:
        try:
            # GPIO Zero's blink is blocking by default.
            # To make it non-blocking, we'd run this in a separate thread.
            # For simplicity now, a short blocking blink is okay.
            # If main loop timing is critical, consider threading this.
            led_object.blink(on_time=on_time, off_time=off_time, n=times, background=False) # background=False makes it blocking for 'n' times
        except GPIOZeroError as e:
            logger.error(f"GPIOZero error during LED blink: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during LED blink: {e}")
    else:
        logger.warning("LED object not initialized, cannot blink.")


def main():
    global plate_detected_led # Allow modification of the global LED object

    logger = log_utils.setup_logger(LOG_FILE)
    logger.info("Starting Number Plate Detection System on Raspberry Pi (with LED indicator)...")

    # --- Initialize LED ---
    try:
        plate_detected_led = LED(LED_PIN)
        plate_detected_led.off() # Ensure LED is off at start
        logger.info(f"LED initialized on GPIO{LED_PIN}.")
    except GPIOPinMissing:
        logger.error(f"GPIO Pin {LED_PIN} not found. Is GPIO support enabled or pin correct? LED will not function.")
        plate_detected_led = None # Ensure it's None if init fails
    except GPIOZeroError as e:
        logger.error(f"GPIOZero library error initializing LED on GPIO{LED_PIN}: {e}. LED will not function.")
        plate_detected_led = None
    except Exception as e: # Catch any other unexpected error during LED init
        logger.error(f"Unexpected error initializing LED on GPIO{LED_PIN}: {e}. LED will not function.")
        plate_detected_led = None


    if THINGSBOARD_TOKEN_MAIN == "YOUR_RPI_DEVICE_ACCESS_TOKEN":
        logger.error("CRITICAL: THINGSBOARD_DEVICE_TOKEN is not set. ThingsBoard will not work.")

    db_conn = db_utils.create_connection(DB_FILE)
    if not db_conn:
        logger.error("Failed to connect to database. Exiting.")
        if plate_detected_led: plate_detected_led.close()
        return
    db_utils.create_table(db_conn)

    ocr_reader = ocr_utils.get_ocr_reader()
    if not ocr_reader:
        logger.warning("Failed to initialize OCR Reader. OCR will not function.")

    pi_mqtt_client = mqtt_client_pi.create_mqtt_client()
    # ... (set MQTT params if different from defaults in mqtt_client_pi) ...
    mqtt_client_pi.connect_mqtt(pi_mqtt_client)

    tb_mqtt_client = tb_client.create_thingsboard_client()
    # ... (set TB params if different from defaults in tb_client) ...
    tb_client.THINGSBOARD_HOST = THINGSBOARD_HOST_MAIN
    tb_client.THINGSBOARD_DEVICE_TOKEN = THINGSBOARD_TOKEN_MAIN
    tb_client.connect_thingsboard(tb_mqtt_client)
    
    # --- Crucial: Set the frame provider for Flask BEFORE starting Flask thread ---
    flask_server.set_frame_provider(get_latest_frame_for_flask)

    # Start Flask server in a separate thread
    # flask_server.app.processing_active will be the master control.
    flask_thread = threading.Thread(target=flask_server.run_flask_app, daemon=True)
    flask_thread.start()
    logger.info("Flask server started in a background thread.")

    cap = camera_utils.init_camera(CAMERA_ID)
    if not cap:
        logger.error("Failed to initialize camera. Main loop cannot run effectively.")
        # Attempt to signal flask to stop or show error if this is critical path
        flask_server.app.processing_active = False # Signal an issue
        # Clean up other resources
        # ... (db_conn.close(), mqtt disconnects etc.) ...
        return

    logger.info("Main detection loop starting...")
    last_ocr_processed_time = time.time()
    global latest_frame_for_flask_stream # Ensure we modify the global one

    try:
        while True:
            # Main loop is controlled by the flag in flask_server.app
            if not flask_server.app.processing_active:
                logger.info("Main loop: Processing paused by admin command (via Flask app).")
                # When paused, ensure camera is released or handled to prevent issues
                # And clear the frame for streaming so Flask shows "Paused"
                with frame_stream_lock:
                    latest_frame_for_flask_stream = None 
                
                # Optionally release camera if paused for long, but then re-init is needed
                # if cap and cap.isOpened():
                #    logger.info("Releasing camera while paused.")
                #    camera_utils.release_camera(cap)
                #    cap = None
                time.sleep(1) 
                continue # Skip the rest of the loop

            # If paused and camera was released, try to reinitialize
            if cap is None or not cap.isOpened():
                logger.info("Main loop: Camera not open, attempting to re-initialize...")
                cap = camera_utils.init_camera(CAMERA_ID)
                if not cap:
                    logger.error("Main loop: Failed to re-initialize camera. Will retry.")
                    with frame_stream_lock: # Ensure no stale frame is streamed
                        latest_frame_for_flask_stream = None
                    time.sleep(5) # Wait longer before retrying camera
                    continue
                logger.info("Main loop: Camera re-initialized.")
            
            ret, frame = camera_utils.capture_frame(cap)
            
            if not ret or frame is None:
                logger.warning("Failed to capture frame. Retrying.")
                with frame_stream_lock: # Clear shared frame on error
                    latest_frame_for_flask_stream = None
                # Consider releasing and re-initializing camera on persistent errors
                camera_utils.release_camera(cap) 
                cap = None # Signal to re-initialize in next iteration
                time.sleep(1)
                continue

            # Update frame for Flask stream (do this for every valid frame)
            with frame_stream_lock:
                latest_frame_for_flask_stream = frame # .copy() is done in getter

            # --- OCR Processing (throttled) ---
            current_time = time.time()
            if ocr_reader and (current_time - last_ocr_processed_time) >= FRAME_PROCESS_INTERVAL:
                last_ocr_processed_time = current_time
                # Process 'frame' for OCR. Consider doing OCR on a copy if frame is large or processing is slow
                # to avoid holding up the frame_stream_lock for too long if OCR is part of it.
                # For this setup, OCR is outside the lock of latest_frame_for_flask_stream.
                detections = ocr_utils.detect_plate_text(frame.copy(), ocr_reader) # Process a copy
                if detections:
                    # ... (existing OCR logic, DB save, MQTT publish, TB publish) ...
                    # (Copied from your original main_pi.py)
                    logger.info(f"Detected {len(detections)} potential texts.")
                    for (bbox, text, prob) in detections:
                        cleaned_text = ocr_utils.clean_plate_text(text)
                        if cleaned_text:
                            timestamp_str = datetime.now().isoformat()
                            # --- LED Control Logic ---
                            if prob >= LED_CONFIDENCE_THRESHOLD:
                                logger.info(f"High confidence plate: {cleaned_text} (Conf: {prob:.2f}). Blinking LED.")
                                if plate_detected_led:
                                    # Run blink in a new thread to avoid blocking main loop significantly
                                    # If blink_led_on_detection is very short, direct call might be okay.
                                    # For responsive system, threading is better for I/O like LED blink sequences.
                                    led_thread = threading.Thread(target=blink_led_on_detection, args=(plate_detected_led, 2, 0.15, 0.15))
                                    led_thread.daemon = True # Allows main program to exit even if thread is running
                                    led_thread.start()
                            # --- End LED Control ---

                            logger.info(f"Plate: {cleaned_text}, Confidence: {prob:.2f}, Time: {timestamp_str}")
                            #logger.info(f"plate: {cleaned_text}, confidence: {prob:.2f}, timestamp: {timestamp_str}")
                            plate_data_dict = {
                                "plate": cleaned_text, "timestamp": timestamp_str, "confidence": float(prob)
                            }
                            db_utils.save_plate(db_conn, cleaned_text, timestamp_str, prob)
                            if pi_mqtt_client.is_connected():
                                mqtt_client_pi.publish_plate_data(pi_mqtt_client, plate_data_dict)
                            if tb_mqtt_client.is_connected():
                                #telemetry_for_tb = {"plate_number": cleaned_text, "confidence": float(prob)}
                                telemetry_for_tb = {"plate": cleaned_text, "timestamp": timestamp_str, "confidence": float(prob)}
                                tb_client.publish_telemetry_to_thingsboard(tb_mqtt_client, telemetry_for_tb)
                        else:
                            logger.debug(f"Raw text '{text}' rejected by cleaning function.")
            elif not ocr_reader and (current_time - last_ocr_processed_time) >= FRAME_PROCESS_INTERVAL:
                 last_ocr_processed_time = current_time # Still update time to avoid spamming warning
                 logger.warning("OCR Reader not available, skipping text detection.")

            # No cv2.imshow here for X11, streaming is via Flask.
            time.sleep(0.01) # Small sleep to yield CPU, actual frame rate driven by camera and stream sleep

    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Shutting down...")
        flask_server.app.processing_active = False # Signal Flask to stop activities if it checks
    except Exception as e:
        logger.error(f"An unhandled exception occurred in the main loop: {e}", exc_info=True)
        flask_server.app.processing_active = False
    finally:
        logger.info("Cleaning up resources...")
        with frame_stream_lock: # Ensure no one tries to access it during cleanup
            latest_frame_for_flask_stream = None
        if cap:
            camera_utils.release_camera(cap)
        if db_conn:
            db_conn.close()
            logger.info("Database connection closed.")
        if pi_mqtt_client and pi_mqtt_client.is_connected():
            mqtt_client_pi.disconnect_mqtt(pi_mqtt_client)
        if tb_mqtt_client and tb_mqtt_client.is_connected():
            tb_client.disconnect_thingsboard(tb_mqtt_client)
        
        # --- Release LED ---
        if plate_detected_led:
            try:
                plate_detected_led.off() # Ensure LED is off on exit
                plate_detected_led.close() # Release GPIO resources
                logger.info(f"LED on GPIO{LED_PIN} closed.")
            except GPIOZeroError as e:
                logger.error(f"GPIOZero error closing LED: {e}")
        
        logger.info("System shutdown complete.")

if __name__ == "__main__":
    main()