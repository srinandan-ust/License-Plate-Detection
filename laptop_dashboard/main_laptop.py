# laptop_dashboard/main_laptop.py
from tkinter_dashboard import TkinterDashboard
from mqtt_subscriber import MQTTSubscriber
import signal # For graceful shutdown

# --- Configuration (Consider moving to a config.py or using environment variables) ---
# MQTT Broker Settings - Must match the Pi's publisher settings
MQTT_BROKER_HOST = "localhost"  # Replace! e.g., "localhost" or actual IP
MQTT_BROKER_PORT = 1883
MQTT_TOPIC_PLATES = "rpi/license_plates" # Must match topic used by Pi
# ---

# Global references for cleanup
app = None
mqtt_subscriber = None

def graceful_shutdown(signum, frame):
    print("Shutdown signal received. Cleaning up...")
    if app:
        app.on_closing(mqtt_subscriber) # This will also stop MQTT subscriber
    # If app.on_closing doesn't handle everything or if app is None
    elif mqtt_subscriber:
        mqtt_subscriber.stop_listening()
    
    # In a more complex app, you might exit explicitly after cleanup
    # For Tkinter, destroying the main window usually ends the app.
    # sys.exit(0) # Not strictly necessary if Tkinter handles exit

def main():
    global app, mqtt_subscriber

    # Create the Tkinter dashboard
    app = TkinterDashboard(title="RPi License Plate Monitor")

    # Create and configure the MQTT subscriber
    # The callback from MQTT subscriber will call app.update_data
    mqtt_subscriber = MQTTSubscriber(
        broker_host=MQTT_BROKER_HOST,
        broker_port=MQTT_BROKER_PORT,
        topic=MQTT_TOPIC_PLATES,
        on_message_callback=app.update_data # Pass the method reference
    )
    
    # Connect and start listening in a background thread
    mqtt_subscriber.connect()
    if mqtt_subscriber.connected: # Check if initial connection was successful
        mqtt_subscriber.start_listening()
    else:
        print("Failed to connect to MQTT broker initially. Dashboard may not receive updates.")
        # You might want to add a retry mechanism or status display in the GUI

    # Set up graceful shutdown for Ctrl+C
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    # Set the close window behavior for Tkinter
    app.protocol("WM_DELETE_WINDOW", lambda: graceful_shutdown(None, None))

    # Start the Tkinter event loop
    try:
        app.mainloop()
    except Exception as e:
        print(f"Error in Tkinter mainloop: {e}")
    finally:
        # Ensure cleanup if mainloop exits unexpectedly
        print("Tkinter mainloop exited. Final cleanup...")
        if mqtt_subscriber and mqtt_subscriber.connected:
             mqtt_subscriber.stop_listening()


if __name__ == "__main__":
    if MQTT_BROKER_HOST == "your_mqtt_broker_ip":
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! CRITICAL: Please update MQTT_BROKER_HOST in main_laptop.py !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    else:
        main()