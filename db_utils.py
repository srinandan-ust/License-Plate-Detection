# raspberry_pi_code/db_utils.py
import sqlite3
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path="detected_plates.db"):
        self.db_path = db_path
        self._create_table_if_not_exists()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _create_table_if_not_exists(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detected_plates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plate_text TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                confidence REAL
            )
        ''')
        conn.commit()
        conn.close()

    def save_plate(self, plate_text, confidence):
        conn = self._get_connection()
        cursor = conn.cursor()
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            cursor.execute('''
                INSERT INTO detected_plates (plate_text, timestamp, confidence)
                VALUES (?, ?, ?)
            ''', (plate_text, timestamp_str, confidence))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Database error while saving plate: {e}")
        finally:
            conn.close()

    def get_all_plates(self, limit=100, offset=0):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT plate_text, timestamp, confidence 
                FROM detected_plates
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            plates = cursor.fetchall()
            return plates
        except sqlite3.Error as e:
            print(f"Database error while fetching plates: {e}")
            return []
        finally:
            conn.close()

if __name__ == '__main__':
    db_manager = DatabaseManager("test_plates.db")
    db_manager.save_plate("TEST123", 0.95)
    db_manager.save_plate("XYZ789", 0.88)
    print("Saved test plates.")
    plates = db_manager.get_all_plates()
    print("Fetched plates:")
    for plate in plates:
        print(plate)