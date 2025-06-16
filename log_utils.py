# raspberry_pi_code/log_utils.py
import logging
import sqlite3
from datetime import datetime

# --- File Logger ---
def setup_file_logger(log_file_path="app.log", logger_name="AppLogger"):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO) # Set default logging level

    # Prevent adding multiple handlers if function is called multiple times
    if not logger.handlers:
        # File handler
        fh = logging.FileHandler(log_file_path)
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        # Console handler (optional, good for debugging)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    return logger

# --- SQLite Logger ---
class LogDBManager:
    def __init__(self, db_path="event_logs.db"):
        self.db_path = db_path
        self._create_log_table_if_not_exists()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _create_log_table_if_not_exists(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS event_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

    def log_event(self, level_str, message):
        conn = self._get_connection()
        cursor = conn.cursor()
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] # Milliseconds
        try:
            cursor.execute('''
                INSERT INTO event_logs (timestamp, level, message)
                VALUES (?, ?, ?)
            ''', (timestamp_str, level_str.upper(), message))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Database error while logging event: {e}")
        finally:
            conn.close()

if __name__ == '__main__':
    # Test file logger
    file_logger = setup_file_logger("test_app.log")
    file_logger.info("This is an info message for file log.")
    file_logger.warning("This is a warning message for file log.")

    # Test DB logger
    log_db_manager = LogDBManager("test_event_logs.db")
    log_db_manager.log_event("INFO", "System started test event.")
    log_db_manager.log_event("ERROR", "A test error occurred.")
    print("Logged events to test_app.log and test_event_logs.db")