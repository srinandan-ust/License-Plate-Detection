from flask import Flask, render_template, jsonify, send_from_directory, request, abort
import threading
import os
import sys

# Add parent directory to path to import utils
# This is needed if you run this file directly for testing.
# When imported by main.py, this is not strictly necessary but doesn't hurt.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db_utils import get_all_logs, DB_FILE

# --- Global variable for Flask app ---
# We define it globally so our route functions can access it.
app = Flask(__name__, template_folder='flask_admin/templates', static_folder='logs')

# --- Shared control events ---
# These will be set by the MainApplication class.
detection_control_event = None
logger = None

# --- Flask Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/logs')
def api_logs():
    """API endpoint to fetch logs as JSON."""
    try:
        logs = get_all_logs()
        # Convert sqlite3.Row objects to dictionaries for JSON serialization
        dict_logs = [dict(row) for row in logs]
        return jsonify(dict_logs)
    except Exception as e:
        logger.error(f"Flask API error in /api/logs: {e}")
        return jsonify({"error": "Could not retrieve logs"}), 500

@app.route('/api/control', methods=['POST'])
def api_control():
    """API endpoint to start/stop detection."""
    global detection_control_event
    if not detection_control_event:
        return jsonify({"status": "error", "message": "Control event not initialized"}), 500
    
    data = request.get_json()
    action = data.get('action')

    if action == 'start':
        detection_control_event.set() # Set event means "run"
        logger.info("Detection START command received via Flask.")
        return jsonify({"status": "success", "message": "Detection started"})
    elif action == 'stop':
        detection_control_event.clear() # Clear event means "pause"
        logger.info("Detection STOP command received via Flask.")
        return jsonify({"status": "success", "message": "Detection stopped"})
    else:
        return jsonify({"status": "error", "message": "Invalid action"}), 400

@app.route('/snapshots/<path:filename>')
def serve_snapshot(filename):
    """Serves the snapshot images from the logs directory."""
    # This is a security risk in a real production environment!
    # For this project, it's acceptable.
    # We use a relative path from the project root.
    snapshot_dir = os.path.join(os.getcwd(), 'logs')
    return send_from_directory(snapshot_dir, filename)


# --- Flask Server Class ---
class FlaskServer:
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.thread = threading.Thread(target=self.run, daemon=True)

    def run(self):
        """Runs the Flask app."""
        # The 'app.run' is blocking, so it will keep the thread alive.
        # Setting debug=False is important when running in a thread from another script.
        try:
            logger.info(f"Starting Flask server on http://{self.host}:{self.port}")
            app.run(host=self.host, port=self.port, debug=False)
        except Exception as e:
            logger.error(f"Flask server failed to start: {e}")

    def start(self, control_event, app_logger):
        """Starts the Flask server thread."""
        global detection_control_event, logger
        detection_control_event = control_event
        logger = app_logger
        self.thread.start()
