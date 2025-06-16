# flask_admin/app.py
from flask import Flask, render_template, jsonify, request, redirect, url_for
import sys
import os

# Add parent directory to path to import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db_utils import get_all_logs

app = Flask(__name__)

@app.route('/')
def index():
    return redirect(url_for('logs'))

@app.route('/logs')
def logs():
    log_entries = get_all_logs()
    return render_template('index.html', logs=log_entries)

# Add other routes from spec: /settings, /export, /start, /stop
# These will require more complex logic to control the main script
# (e.g., using a shared state file or a process management library).

if __name__ == '__main__':
    # Use 0.0.0.0 to make it accessible on your LAN
    app.run(host='0.0.0.0', port=5000, debug=True)