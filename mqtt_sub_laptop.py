import paho.mqtt.client as mqtt
import json
import logging
import queue # For thread-safe communication with Tkinter

logger = logging.getLogger(__name__)

# --- Configuration ---
MQTT_BROKER_HOST = "192.168.3.169"  # Or RPi's IP address
MQTT_BROKER_PORT = 1883
MQTT_TOPIC_PLATE_SUB = "rpi/plate_detection/plate" # Must match publisher's topic
CLIENT_ID_SUB = "laptop_plate_subscriber"
# --- End Configuration ---

class MQTTSubscriber:
    def __init__(self, data_queue):
        self.client = mqtt.Client(client_id=CLIENT_ID_SUB)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.data_queue = data_queue # Queue to pass data to Tkinter
        self.connected = False

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Connected to MQTT Broker: {MQTT_BROKER_HOST}")
            client.subscribe(MQTT_TOPIC_PLATE_SUB)
            logger.info(f"Subscribed to topic: {MQTT_TOPIC_PLATE_SUB}")
            self.connected = True
        else:
            logger.error(f"Failed to connect to MQTT, return code {rc}")
            self.connected = False

    def on_message(self, client, userdata, msg):
        try:
            payload_str = msg.payload.decode('utf-8')
            logger.info(f"Received message on {msg.topic}: {payload_str}")
            data = json.loads(payload_str)
            # Put the received data into the queue for Tkinter to process
            self.data_queue.put(data)
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON: {msg.payload.decode('utf-8')}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def on_disconnect(self, client, userdata, rc):
        logger.warning(f"Disconnected from MQTT Broker with result code {rc}")
        self.connected = False
        # Optional: Add reconnection logic here if desired

    def connect(self):
        try:
            self.client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
            logger.info(f"Attempting to connect to MQTT broker at {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
        except ConnectionRefusedError:
            logger.error(f"MQTT Connection Refused. Is broker running at {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}?")
        except Exception as e:
            logger.error(f"Error connecting to MQTT: {e}")


    def start(self):
        """Starts the MQTT client loop in a non-blocking way."""
        self.client.loop_start() # Starts a new thread for network events

    def stop(self):
        """Stops the MQTT client loop and disconnects."""
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("MQTT subscriber stopped and disconnected.")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # Example usage:
    q = queue.Queue()
    subscriber = MQTTSubscriber(data_queue=q)
    subscriber.connect()
    subscriber.start()

    print("Listening for MQTT messages... Press Ctrl+C to stop.")
    try:
        while True:
            try:
                message = q.get(timeout=1) # Check queue for new messages
                print(f"Data from queue: {message}")
            except queue.Empty:
                pass # No message
            except KeyboardInterrupt:
                break
    finally:
        subscriber.stop()