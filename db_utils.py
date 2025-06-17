import sqlite3
import logging
from datetime import datetime
 
logger = logging.getLogger(__name__)
DB_NAME = "detected_plates.db" # Or import from a config file
 
def create_connection(db_file=DB_NAME):
    """Create a database connection to the SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except sqlite3.Error as e:
        logger.error(f"Error connecting to database: {e}")
    return conn
 
def create_table(conn):
    """Create the license_plates table if it doesn't exist."""
    sql_create_plates_table = """ CREATE TABLE IF NOT EXISTS license_plates (
                                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                                            plate_number TEXT NOT NULL,
                                            timestamp TEXT NOT NULL,
                                            confidence REAL
                                        ); """
    try:
        c = conn.cursor()
        c.execute(sql_create_plates_table)
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Error creating table: {e}")
 
def save_plate(conn, plate_number, timestamp, confidence):
    """Save a new detected plate into the license_plates table."""
    sql = ''' INSERT INTO license_plates(plate_number, timestamp, confidence)
              VALUES(?,?,?) '''
    cur = conn.cursor()
    try:
        cur.execute(sql, (plate_number, timestamp, confidence))
        conn.commit()
        logger.info(f"Saved to DB: {plate_number}, {timestamp}, {confidence:.2f}")
        return cur.lastrowid
    except sqlite3.Error as e:
        logger.error(f"Error saving plate to DB: {e}")
        return None
 
def get_all_plates(conn):
    """Query all rows in the license_plates table."""
    cur = conn.cursor()
    try:
        cur.execute("SELECT plate_number, timestamp, confidence FROM license_plates ORDER BY timestamp DESC")
        rows = cur.fetchall()
        return rows
    except sqlite3.Error as e:
        logger.error(f"Error fetching all plates: {e}")
        return []
 
def get_recent_plates(conn, limit=10):
    """Query a limited number of recent plates."""
    cur = conn.cursor()
    try:
        cur.execute("SELECT plate_number, timestamp, confidence FROM license_plates ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        return rows
    except sqlite3.Error as e:
        logger.error(f"Error fetching recent plates: {e}")
        return []
 
def clear_except_last_n(conn, n=10):
    """
    Deletes all but the last `n` entries (by timestamp descending) from license_plates.
    """
    try:
        cursor = conn.cursor()
        # Keep latest `n` entries
        cursor.execute(f"""
            DELETE FROM license_plates
            WHERE id NOT IN (
                SELECT id FROM license_plates
                ORDER BY timestamp DESC
                LIMIT ?
            )
        """, (n,))
        conn.commit()
        logger.info(f"Cleared database, kept last {n} entries.")
    except Exception as e:
        logger.error(f"Error clearing entries: {e}")
 
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    conn = create_connection()
    if conn:
        create_table(conn)
        # Test save
        save_plate(conn, "TEST1234", datetime.now().isoformat(), 0.95)
        save_plate(conn, "XYZ567", datetime.now().isoformat(), 0.88)

        print("All plates:")
        plates = get_all_plates(conn)
        for plate in plates:
            print(plate)

        conn.close()