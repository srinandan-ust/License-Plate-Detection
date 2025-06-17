import tkinter as tk
import threading
import queue
import logging

# Import project modules
#from . import tkinter_dash
#from . import mqtt_sub_laptop

# Or if running main_laptop.py directly for testing:
import tkinter_dash, mqtt_sub_laptop

# --- Configuration (from mqtt_sub_laptop and others) ---
MQTT_BROKER_LAPTOP = "192.168.3.169" # Or RPi IP, ensure it matches mqtt_sub_laptop
# --- End Configuration ---

def main():
    # Setup basic logging for the laptop application
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    logger.info("Starting Laptop Dashboard Application...")

    # 1. Create a queue for communication between MQTT thread and Tkinter GUI
    data_q = queue.Queue()

    # 2. Initialize MQTT Subscriber
    # Pass the RPi's IP or hostname to the subscriber
    mqtt_sub_laptop.MQTT_BROKER_HOST = MQTT_BROKER_LAPTOP 
    subscriber = mqtt_sub_laptop.MQTTSubscriber(data_queue=data_q)
    
    # Try to connect MQTT client
    subscriber.connect() # This attempts connection, logs success/failure

    # 3. Start MQTT client in a separate thread
    # The subscriber.start() method itself starts a paho-mqtt internal loop thread.
    # So, we just need to call it.
    if subscriber.client: # Check if client object was created
        subscriber.start() # This starts client.loop_start()
        logger.info("MQTT subscriber thread started.")
    else:
        logger.error("MQTT client object not created. Subscriber will not run.")


    # 4. Initialize Tkinter Dashboard
    root = tk.Tk()
    dashboard_app = tkinter_dash.PlateDashboard(root, data_q)
    
    def on_app_closing():
        logger.info("Application closing sequence initiated.")
        if subscriber:
            subscriber.stop() # Gracefully stop MQTT subscriber
        dashboard_app.on_closing() # Perform Tkinter cleanup

    root.protocol("WM_DELETE_WINDOW", on_app_closing)

    # 5. Start Tkinter main loop (this must be in the main thread)
    logger.info("Starting Tkinter main loop...")
    try:
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received in Tkinter loop.")
        on_app_closing() # Ensure cleanup on Ctrl+C if Tkinter catches it
    finally:
        logger.info("Laptop Dashboard Application finished.")


if __name__ == "__main__":
    # For direct execution:
    # import sys
    # import os
    # sys.path.append(os.path.dirname(os.path.abspath(__file__))) # If modules are in same dir
    main()