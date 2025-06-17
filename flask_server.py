from flask import Flask, jsonify, render_template, Response, request, send_file, redirect, url_for, session # Added request, send_file, redirect, url_for, session

import logging
import cv2
import time
import numpy as np
import db_utils
import csv
from datetime import datetime
import os

# Optional password login
from functools import wraps

# If running flask_server.py standalone for testing, adjust import:
# import db_utils as db_utils_standalone # and use db_utils_standalone

logger = logging.getLogger(__name__)

DB_NAME_FLASK = "detected_plates.db" # Ensure this matches db_utils

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for sessions

# Master control flag for the entire system's processing state
# main_pi.py will read this flag to control its loop.
app.processing_active = True # Default to active

# Global variable to hold the function that gets frames from main_pi.py
_get_frame_function = None

# Optional password login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('logged_in') != True:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def set_frame_provider(frame_getter_func):
    """
    Called by main_pi.py to provide the function that retrieves the latest frame.
    """
    global _get_frame_function
    _get_frame_function = frame_getter_func
    logger.info("Frame provider function set for Flask video stream.")

def generate_frames():
    """Generator function for video streaming."""
    global _get_frame_function

    frame_read_errors = 0
    max_frame_read_errors = 30 # e.g., stop if no valid frame for ~1 second at 30fps attempt

    while True:
        if not app.processing_active:
            # If processing is stopped, send a "Paused" image
            paused_img = np.zeros((480, 640, 3), dtype=np.uint8) # Adjust size as needed
            cv2.putText(paused_img, "Detection Paused", (150, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 2)
            ret_enc, buffer = cv2.imencode('.jpg', paused_img)
            if ret_enc:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.5) # Send "paused" image periodically
            continue # Skip trying to get live frames

        if _get_frame_function is None:
            logger.warning("Video stream: Frame provider not set. Sending placeholder.")
            placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(placeholder, "No Video Signal", (160, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
            ret_enc, buffer = cv2.imencode('.jpg', placeholder)
            if ret_enc:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(1) # Send placeholder every second
            continue

        frame = _get_frame_function() # Call the function from main_pi to get the frame

        if frame is None:
            # logger.debug("Video stream: No frame available from provider.")
            frame_read_errors += 1
            if frame_read_errors > max_frame_read_errors:
                logger.warning("Video stream: Too many errors getting frame. Sending error image and pausing for client.")
                error_img = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(error_img, "Stream Error", (180, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 2)
                ret_enc, buffer = cv2.imencode('.jpg', error_img)
                if ret_enc:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                time.sleep(5) # Wait before client might retry or show error longer
                # Optionally, break here if the client should disconnect
            time.sleep(0.03) # Wait a bit if no frame is available
            continue

        frame_read_errors = 0 # Reset error count on successful frame read

        try:
            # Encode frame as JPEG. Adjust quality vs. performance.
            # Lower quality (e.g., 70) reduces CPU load and bandwidth.
            ret_enc, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            if not ret_enc:
                logger.warning("Video stream: JPEG encoding failed.")
                continue

            frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        except Exception as e:
            logger.error(f"Error in generate_frames encoding/yielding: {e}")
            break # Exit the generator loop for this client on error

        # Control frame rate of the stream (e.g., target 10-20 FPS for web view)
        # This sleep is important to not overload the Pi or the network.
        time.sleep(1/20) # Approx 20 FPS

@app.route('/video_feed')
def video_feed():
    """Video streaming route."""
    if not _get_frame_function: # Check if main_pi has set the provider
        logger.error("Video feed request but frame provider not set by main application.")
        return "Error: Video service not ready or frame provider not configured.", 503

    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
@login_required
def index():
    """Serves the admin panel HTML page, passing the current processing status."""
    return render_template('admin_panel.html', processing_status=app.processing_active)

@app.route('/api/plates', methods=['GET'])
@login_required
def get_plates_data():
    """API endpoint to get detected plates from the database."""
    # Ensure db_utils is correctly imported and DB_NAME_FLASK is set
    conn = db_utils.create_connection(DB_NAME_FLASK)
    if conn:
        plates = db_utils.get_recent_plates(conn, limit=50) # Get recent 50
        conn.close()
        plates_list = [{"plate_number": p[0], "timestamp": p[1], "confidence": f"{p[2]:.2f}"} for p in plates]
        return jsonify(plates_list)
    return jsonify({"error": "Could not retrieve data from database"}), 500

@app.route('/api/control/status', methods=['GET'])
@login_required
def get_status():
    return jsonify({"processing_active": app.processing_active})

@app.route('/api/control/start', methods=['POST'])
@login_required
def start_processing():
    app.processing_active = True
    logger.info("Admin command: START processing (flag set to True)")
    return jsonify({"status": "processing_started", "processing_active": app.processing_active})

@app.route('/api/control/stop', methods=['POST'])
@login_required
def stop_processing():
    app.processing_active = False
    logger.info("Admin command: STOP processing (flag set to False)")
    return jsonify({"status": "processing_stopped", "processing_active": app.processing_active})

# New routes for admin panel functionalities
@app.route('/logs')
@login_required
def view_logs():
    # Placeholder for log viewing functionality.  In a real application, you'd read from log files.
    # For a simple example, you might read the last N lines of a specified log file.
    logs = ["Log entry 1: [INFO] System started.", "Log entry 2: [DEBUG] Frame processed.", "Log entry 3: [ERROR] Database write failed."] # Replace with actual log reading
    return render_template('logs.html', logs=logs)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        # Placeholder for settings saving. You'd likely save these to a config file (e.g., JSON, YAML) or a dedicated settings table in your database.
        threshold = request.form.get('threshold')
        detection_mode = request.form.get('detection_mode')
        mqtt_broker = request.form.get('mqtt_broker')
        mqtt_topic = request.form.get('mqtt_topic')

        logger.info(f"Settings updated: Threshold={threshold}, Mode={detection_mode}, MQTT Broker={mqtt_broker}, MQTT Topic={mqtt_topic}")
        # Add your code here to save these settings persistently
        # For example: save_config({'threshold': threshold, 'detection_mode': detection_mode, 'mqtt_broker': mqtt_broker, 'mqtt_topic': mqtt_topic})
        return redirect(url_for('settings')) # Redirect to avoid resubmission
    
    # Placeholder values. Replace with reading from your actual config/database.
    current_threshold = 0.85
    current_detection_mode = "realtime" # or "batch"
    current_mqtt_broker = "mqtt.example.com"
    current_mqtt_topic = "plate/detections"

    return render_template('settings.html', 
                           threshold=current_threshold, 
                           detection_mode=current_detection_mode, 
                           mqtt_broker=current_mqtt_broker, 
                           mqtt_topic=current_mqtt_topic)

@app.route('/export')
@login_required
def export_logs():
    conn = db_utils.create_connection(DB_NAME_FLASK)
    if not conn:
        logger.error("Export: Database connection failed.")
        return "Database connection failed", 500
 
    plates = db_utils.get_all_plates(conn)
    conn.close()
 
    if not plates:
         logger.warning("Export: No data to export.")
         return "No data to export", 404 # Browser might show this message
 
    csv_data = [("Plate Number", "Timestamp", "Confidence")]  # Header
    csv_data.extend(plates)
    # ... rest of your code

@app.route('/clear_data', methods=['POST'])
@login_required
def clear_data():
    conn = db_utils.create_connection(DB_NAME_FLASK)
    if not conn:
        return jsonify({"message": "Database connection failed"}), 500

    db_utils.clear_except_last_n(conn, n=10) # Keeps the last 10 entries
    conn.close()
    return jsonify({"message": "Database cleared, keeping last 10 entries."})

# Optional password login
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        # !!! IMPORTANT: Change 'admin' and 'password' to secure credentials !!!
        if request.form['username'] != 'admin' or request.form['password'] != 'password':  
            error = 'Invalid Credentials. Please try again.'
        else:
            session['logged_in'] = True
            return redirect(url_for('index'))
    return render_template('login.html', error=error)

@app.route('/logout')
@login_required
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

def run_flask_app(host='0.0.0.0', port=5000):
    """Runs the Flask app."""
    logger.info(f"Starting Flask server on {host}:{port}")
    # threaded=True allows Flask to handle multiple requests concurrently (e.g., API and video stream)
    # use_reloader=False is important when Flask is run in a thread managed by another script.
    app.run(host=host, port=port, threaded=True, use_reloader=False, debug=False)

if __name__ == '__main__':
    # For standalone testing of Flask server
    logging.basicConfig(level=logging.INFO)
    # Make sure db_utils can be imported if you use its functions here for testing
    # e.g. import db_utils as dbu_test
    # Setup a dummy frame provider for testing /video_feed
    def dummy_frame_getter():
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(img, f"Flask Test Mode: {time.strftime('%H:%M:%S')}", (50,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,0), 2)
        return img
    set_frame_provider(dummy_frame_getter)

    run_flask_app(debug=True) # debug=True enables reloader for standalone