# tkinter_dashboard.py
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import threading
# You'll need to integrate this with your main loop logic.

class LPR_GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LPR Dashboard")

        # Frame for video feed
        self.video_label = tk.Label(root)
        self.video_label.pack()

        # Frame for logs
        self.log_frame = ttk.LabelFrame(root, text="Detections")
        self.log_frame.pack(fill="both", expand="yes")

        self.log_text = tk.Listbox(self.log_frame)
        self.log_text.pack(fill="both", expand="yes")

    def update_video_feed(self, frame):
        # Convert CV2 frame to a Tkinter-compatible photo image
        cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(cv2image)
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)

    def add_log_entry(self, log_message):
        self.log_text.insert(0, log_message) # Insert at the top
        if self.log_text.size() > 10:
            self.log_text.delete(tk.END) # Keep only last 10

# To integrate:
# In your main.py, you would create a separate thread for the Tkinter GUI.
# The main detection loop would then call `gui.update_video_feed(frame)` and
# `gui.add_log_entry(f"{plate} - {confidence}")` using a thread-safe queue.