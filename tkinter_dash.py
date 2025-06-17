import tkinter as tk
from tkinter import ttk, scrolledtext
import queue # For receiving data from MQTT subscriber

class PlateDashboard:
    def __init__(self, root, data_queue):
        self.root = root
        self.data_queue = data_queue # Queue to get data from MQTT subscriber
        self.root.title("License Plate Dashboard")
        self.root.geometry("600x400")

        self.create_widgets()
        self.check_queue_periodically() # Start checking the queue

    def create_widgets(self):
        # Frame for displaying plates
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(expand=True, fill=tk.BOTH)

        ttk.Label(main_frame, text="Detected License Plates:", font=("Arial", 14)).pack(pady=5)

        # Using a ScrolledText widget for easy display and scrolling
        self.plate_display = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=15, width=70)
        self.plate_display.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        self.plate_display.configure(state='disabled') # Make it read-only initially

        # Status bar (optional)
        self.status_var = tk.StringVar()
        self.status_var.set("Awaiting data...")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def add_plate_to_display(self, plate_data):
        """Adds plate information to the text display."""
        try:
            plate = plate_data.get('plate', 'N/A')
            timestamp = plate_data.get('timestamp', 'N/A')
            confidence = plate_data.get('confidence', 'N/A')
            
            display_text = f"Plate: {plate}, Time: {timestamp}, Confidence: {confidence:.2f}\n"
            
            self.plate_display.configure(state='normal') # Enable editing
            self.plate_display.insert(tk.END, display_text)
            self.plate_display.see(tk.END) # Scroll to the end
            self.plate_display.configure(state='disabled') # Disable editing
            
            self.status_var.set(f"Last received: {plate} at {timestamp.split('T')[1].split('.')[0]}")
        except Exception as e:
            print(f"Error updating dashboard UI: {e}")
            self.plate_display.configure(state='normal')
            self.plate_display.insert(tk.END, f"Error processing data: {plate_data}\n")
            self.plate_display.see(tk.END)
            self.plate_display.configure(state='disabled')


    def check_queue_periodically(self):
        """Checks the queue for new messages and updates UI if any."""
        try:
            while True: # Process all messages currently in queue
                message = self.data_queue.get_nowait() # Non-blocking get
                self.add_plate_to_display(message)
        except queue.Empty:
            pass # No new messages
        finally:
            # Schedule this method to be called again after 100ms
            self.root.after(100, self.check_queue_periodically)

    def on_closing(self):
        """Handle window close event."""
        print("Dashboard closing.")
        self.root.destroy()


if __name__ == '__main__':
    # For standalone testing of the dashboard UI
    import logging
    logging.basicConfig(level=logging.INFO) # For MQTT subscriber if tested here
    
    root_tk = tk.Tk()
    test_data_queue = queue.Queue()
    app = PlateDashboard(root_tk, test_data_queue)

    # Simulate receiving data
    def simulate_data_arrival():
        import random, time
        from datetime import datetime
        
        sim_data = {
            'plate': f"SIM{random.randint(100,999)}",
            'timestamp': datetime.now().isoformat(),
            'confidence': random.uniform(0.7, 0.99)
        }
        test_data_queue.put(sim_data)
        root_tk.after(3000, simulate_data_arrival) # Add new data every 3 seconds

    root_tk.after(1000, simulate_data_arrival) # Start simulation after 1 sec
    root_tk.protocol("WM_DELETE_WINDOW", app.on_closing)
    root_tk.mainloop()