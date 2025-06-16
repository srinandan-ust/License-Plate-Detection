# db_utils.py
import sqlite3
from datetime import datetime

DB_FILE = "logs/plates.db"

def init_db():
    """Initializes the database and creates the table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plate_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_text TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            confidence REAL,
            image_path TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_plate_log(plate, confidence, image_path):
    """Adds a new license plate detection to the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO plate_logs (plate_text, timestamp, confidence, image_path) VALUES (?, ?, ?, ?)",
                   (plate, timestamp, confidence, image_path))
    conn.commit()
    conn.close()

def get_all_logs():
    """Retrieves all logs from the database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row # This allows accessing columns by name
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM plate_logs ORDER BY id DESC")
    logs = cursor.fetchall()
    conn.close()
    return logs