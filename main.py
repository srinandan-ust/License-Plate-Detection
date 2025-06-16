import cv2
import time
import queue
import threading
from datetime import datetime

# --- Tkinter GUI Imports ---
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

# --- Project-Specific Imports ---
from camera_utils import Camera
from ocr_utils import get_plate_from_image
from db_utils import init_db, add_plate_log
from log_utils import setup_logging
from flask_server import FlaskServer

# --- Constants ---
GUI_UPDATE_MS = 50 # How often to update the GUI in milliseconds

# --- LPR GUI Class (The Tkinter Dashboard) ---
class LPR_GUI:
    """A Tkinter-based GUI for the License Plate Recognition System."""
    def __init__(self, root, on_close_callback):
        self.root = root
        self.root.title("LPR Dashboard")
        self.root.protocol("WM_DELETE_WINDOW", on_close_callback) # Handle window close

        # --- Video Feed ---
        self.video_label = tk.Label(root)
        self.video_label.pack(padx=10, pady=10)

        # --- Detections Log ---
        log_frame = ttk.LabelFrame(root, text="Last 10 Detections")
        log_frame.pack(fill="both", expand="yes", padx=10, pady=10)

        self.log_listbox = tk.Listbox(log_frame, height=10)
        self.log_listbox.pack(fill="both", expand="yes", padx=5, pady=5)

        # --- Status Bar ---
        self.status_text = tk.StringVar(value="Status: Initializing...")
        status_bar = ttk.Label(root, textvariable=self.status_text, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def update_video_feed(self, frame):
        """Converts a CV2 frame to a Tkinter image and updates the label."""
        try:
            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2image)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)
        except Exception as e:
            print(f"Error updating video feed: {e}")

    def add_log_entry(self, plate_text, confidence):
        """Adds a detection log to the listbox."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] Plate: {plate_text} (Conf: {confidence:.2f}%)"
        self.log_listbox.insert(0, log_message)
        if self.log_listbox.size() > 10:
            self.log_listbox.delete(tk.END)

    def set_status(self, text):
        """Updates the text in the status bar."""
        self.status_text.set(f"Status: {text}")

# --- Detection Worker Thread ---
def detection_worker(camera, data_queue, stop_event, control_event, logger):
    """
    The core detection logic that runs in a background thread.
    It grabs frames, performs OCR, and puts results into a queue.
    """
    logger.info("Detection worker thread started.")
    last_detection_time = 0
    DETECTION_COOLDOWN = 3 # Cooldown in seconds to avoid multiple logs for the same plate

    while not stop_event.is_set():
        try:
            # Pause mechanism: this will block if the event is cleared (paused via web UI)
            control_event.wait() 

            ret, frame = camera.get_frame()
            if not ret:
                logger.warning("Failed to grab frame.")
                time.sleep(1)
                continue

            plate, confidence = get_plate_from_image(frame)
            if plate and (time.time() - last_detection_time > DETECTION_COOLDOWN):
                last_detection_time = time.time()
                logger.info(f"DETECTED: Plate={plate}, Confidence={confidence:.2f}")

                # Save a snapshot with a unique filename
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                image_filename = f"snapshot_{plate}_{timestamp_str}.jpg"
                image_path = f"logs/{image_filename}"
                cv2.imwrite(image_path, frame)
                
                # Log the relative path to the database
                add_plate_log(plate, confidence, image_path)

                # Prepare data for the GUI
                detection_data = {"plate": plate, "confidence": confidence * 100}
            else:
                detection_data = None
            
            # Put data into the queue for the GUI (always send the frame for the live feed)
            data_queue.put({"frame": frame, "detection": detection_data})

            time.sleep(0.05) # Small sleep to prevent 100% CPU usage

        except Exception as e:
            logger.error(f"Error in detection worker: {e}", exc_info=True)
            time.sleep(2)

    logger.info("Detection worker thread stopped.")

# --- Main Application Logic ---
class MainApplication:
    def __init__(self, root):
        self.root = root
        self.logger = setup_logging()
        init_db()

        # --- Setup threading and events ---
        self.data_queue = queue.Queue()
        self.stop_event = threading.Event() # For full application shutdown
        self.detection_control_event = threading.Event() # For pausing/resuming detection
        self.detection_control_event.set() # Start in the "running" state by default

        # --- Initialize Components ---
        # 1. The Tkinter GUI
        self.gui = LPR_GUI(root, self.on_close)
        
        # 2. The Camera
        self.camera = Camera()
        self.gui.set_status("Camera initialized.")
        
        # 3. The Flask Web Server
        self.flask_server = FlaskServer()
        self.flask_server.start(self.detection_control_event, self.logger)

        # --- Start the Detection Worker Thread ---
        self.detection_thread = threading.Thread(
            target=detection_worker,
            args=(self.camera, self.data_queue, self.stop_event, self.detection_control_event, self.logger)
        )
        self.detection_thread.start()
        self.gui.set_status("Detection and Web Server running.")

        # --- Start the GUI update loop ---
        self.root.after(GUI_UPDATE_MS, self.update_gui)

    def update_gui(self):
        """Periodically checks the queue for new data and updates the GUI."""
        # Update GUI status based on the control event from the web UI
        if not self.detection_control_event.is_set() and "Paused" not in self.gui.status_text.get():
             self.gui.set_status("Detection Paused by Web UI")
        elif self.detection_control_event.is_set() and "Paused" in self.gui.status_text.get():
             self.gui.set_status("Detection Resumed by Web UI")

        try:
            # Get the latest data from the worker thread's queue
            data = self.data_queue.get_nowait()
            
            # Update video feed in the GUI
            if data.get("frame") is not None:
                self.gui.update_video_feed(data["frame"])

            # Update detection logs in the GUI if a new plate was found
            detection = data.get("detection")
            if detection:
                self.gui.add_log_entry(detection["plate"], detection["confidence"])
                # Only update status with plate info if not paused
                if self.detection_control_event.is_set():
                    self.gui.set_status(f"Last Plate: {detection['plate']}")
                    
        except queue.Empty:
            pass # No new data, this is normal
        except Exception as e:
            self.logger.error(f"Error in GUI update loop: {e}")

        # Schedule the next GUI update
        if not self.stop_event.is_set():
            self.root.after(GUI_UPDATE_MS, self.update_gui)

    def on_close(self):
        """Gracefully shuts down all parts of the application."""
        self.logger.info("Shutdown initiated by user from Tkinter window.")
        self.gui.set_status("Shutting down...")

        # The Flask server runs in a daemon thread, so it will stop automatically
        # when the main program exits. No explicit stop is needed.

        # Signal the main stop event for all threads
        self.stop_event.set()
        
        # Unblock the detection worker if it's paused so it can see the stop_event
        self.detection_control_event.set() 
        
        # Wait for the detection thread to finish its current loop and exit
        self.detection_thread.join()
        self.logger.info("Detection thread joined.")

        # Release hardware resources
        self.camera.release()
        self.logger.info("Camera released.")

        # Close the Tkinter window
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MainApplication(root)
    root.mainloop() # This starts the entire application by running the Tkinter event loop