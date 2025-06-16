# laptop_dashboard/tkinter_dashboard.py
import tkinter as tk
from tkinter import ttk, scrolledtext
import json
from datetime import datetime

class TkinterDashboard(tk.Tk):
    def __init__(self, title="License Plate Dashboard"):
        super().__init__()
        self.title(title)
        self.geometry("600x400")

        self.plate_var = tk.StringVar(value="N/A")
        self.timestamp_var = tk.StringVar(value="N/A")
        self.confidence_var = tk.StringVar(value="N/A")
        
        self.max_log_entries = 100
        self.log_entries = []

        self._setup_ui()

    def _setup_ui(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Current Plate Display
        info_frame = ttk.LabelFrame(main_frame, text="Last Detected Plate", padding="10")
        info_frame.pack(fill=tk.X, pady=5)

        ttk.Label(info_frame, text="Plate:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, textvariable=self.plate_var, font=("Arial", 14, "bold")).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_frame, text="Timestamp:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, textvariable=self.timestamp_var).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(info_frame, text="Confidence:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, textvariable=self.confidence_var).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)

        # Log Display
        log_frame = ttk.LabelFrame(main_frame, text="Detection Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10, state=tk.DISABLED)
        self.log_text_area.pack(fill=tk.BOTH, expand=True)

    def update_data(self, topic, payload_bytes):
        try:
            payload_str = payload_bytes.decode('utf-8')
            data = json.loads(payload_str)
            
            plate = data.get("plate", "Error")
            timestamp = data.get("timestamp", "Error")
            confidence = data.get("confidence")

            self.plate_var.set(plate)
            self.timestamp_var.set(timestamp)
            if confidence is not None:
                self.confidence_var.set(f"{confidence:.2f}")
            else:
                self.confidence_var.set("N/A")

            # Update log area (newest on top)
            log_entry = f"{timestamp} - Plate: {plate}, Conf: {self.confidence_var.get()}"
            self.log_entries.insert(0, log_entry) # Add to beginning
            if len(self.log_entries) > self.max_log_entries:
                self.log_entries.pop() # Remove oldest

            self.log_text_area.config(state=tk.NORMAL)
            self.log_text_area.delete('1.0', tk.END)
            for entry in self.log_entries:
                self.log_text_area.insert(tk.END, entry + "\n")
            self.log_text_area.config(state=tk.DISABLED)

        except json.JSONDecodeError:
            print(f"Dashboard: Error decoding JSON: {payload_str}")
            self.log_text_area.config(state=tk.NORMAL)
            self.log_text_area.insert(tk.END, f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Error decoding message\n")
            self.log_text_area.config(state=tk.DISABLED)
        except Exception as e:
            print(f"Dashboard: Error updating UI: {e}")
            self.log_text_area.config(state=tk.NORMAL)
            self.log_text_area.insert(tk.END, f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - UI Update Error: {e}\n")
            self.log_text_area.config(state=tk.DISABLED)


    def on_closing(self, mqtt_sub_instance):
        print("Dashboard: Closing application...")
        if mqtt_sub_instance:
            mqtt_sub_instance.stop_listening()
        self.destroy()

if __name__ == '__main__':
    app = TkinterDashboard()
    
    # Simulate receiving a message for testing UI
    def simulate_message():
        test_payload = json.dumps({
            "plate": "SIM123", 
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
            "confidence": 0.88
        }).encode('utf-8')
        app.update_data("rpi/license_plates", test_payload)
        app.after(5000, simulate_message_2) # Schedule next update

    def simulate_message_2():
        test_payload_2 = json.dumps({
            "plate": "XYZ789", 
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
            "confidence": 0.75
        }).encode('utf-8')
        app.update_data("rpi/license_plates", test_payload_2)
        app.after(5000, simulate_message) # Loop back

    app.after(1000, simulate_message) # Start simulation
    app.protocol("WM_DELETE_WINDOW", lambda: app.on_closing(None)) # Handle window close
    app.mainloop()