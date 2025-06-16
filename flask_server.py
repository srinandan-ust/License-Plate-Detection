# raspberry_pi_code/flask_server.py
from flask import Flask, jsonify, render_template
from db_utils import DatabaseManager # Assumes db_utils.py is in the same directory orPYTHONPATH
# from config import PLATES_DB_PATH, FLASK_HOST, FLASK_PORT # Use if config.py is setup

# Configuration (fallback if config.py is not used directly here)
PLATES_DB_PATH = "detected_plates.db" 
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000

app = Flask(__name__)
# The DatabaseManager instance should ideally be passed or configured,
# but for simplicity, we'll instantiate it here.
# Be mindful of SQLite's threading limitations if not careful.
# For production, consider Flask-SQLAlchemy or careful connection management.

def get_db_manager():
    # This ensures a new manager (and potentially connection) per request context
    # or you can make db_manager global if it handles connections safely.
    return DatabaseManager(db_path=PLATES_DB_PATH)

@app.route('/')
def admin_panel():
    # This will render an HTML page where you can view data.
    # The data fetching will happen via JavaScript in the HTML (see admin.html)
    return render_template('admin.html', title="License Plate Admin")

@app.route('/api/plates', methods=['GET'])
def get_plates_api():
    db_manager = get_db_manager()
    plates_data = db_manager.get_all_plates(limit=50) # Get latest 50 plates
    
    # Convert list of tuples to list of dicts for JSON
    plates_list = []
    for row in plates_data:
        plates_list.append({
            "plate_text": row[0],
            "timestamp": row[1],
            "confidence": row[2]
        })
    return jsonify(plates_list)

def run_flask_server(host=FLASK_HOST, port=FLASK_PORT, debug=False):
    # 'debug=True' is useful for development but should be False in production
    # 'use_reloader=False' is important if running this in a thread within another main script
    app.run(host=host, port=port, debug=debug, use_reloader=False) 

if __name__ == '__main__':
    print(f"Starting Flask server on http://{FLASK_HOST}:{FLASK_PORT}")
    # Create a dummy templates folder and admin.html for this test to run
    import os
    if not os.path.exists("templates"):
        os.makedirs("templates")
    with open("templates/admin.html", "w") as f:
        f.write("<h1>Test Admin Page</h1><p>Data will load here via JavaScript.</p>")
    
    # You would typically run the main_pi.py which might start this server in a thread.
    # For standalone testing of the Flask app:
    run_flask_server(debug=True)