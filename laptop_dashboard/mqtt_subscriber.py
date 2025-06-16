# laptop_dashboard/mqtt_subscriber.py
import paho.mqtt.client as mqtt
import time

class MQTTSubscriber:
    def __init__(self, broker_host, broker_port, topic, on_message_callback, client_id_prefix="laptop_dash_sub"):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic = topic
        self.on_message_callback = on_message_callback
        self.client_id = f"{client_id_prefix}-{int(time.time())}"
        self.client = mqtt.Client(client_id=self.client_id)

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.connected = False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"MQTT Sub: Connected to broker {self.broker_host} successfully.")
            client.subscribe(self.topic)
            print(f"MQTT Sub: Subscribed to topic: {self.topic}")
            self.connected = True
        else:
            print(f"MQTT Sub: Failed to connect, return code {rc}")
            self.connected = False

    def _on_message(self, client, userdata, msg):
        # print(f"MQTT Sub: Received message on {msg.topic}: {msg.payload.decode()}")
        if self.on_message_callback:
            self.on_message_callback(msg.topic, msg.payload)

    def _on_disconnect(self, client, userdata, rc):
        print(f"MQTT Sub: Disconnected from broker with result code {rc}.")
        self.connected = False
        # Optional: Implement reconnection logic here if desired

    def connect(self):
        try:
            print(f"MQTT Sub: Attempting to connect to {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, 60)
        except Exception as e:
            print(f"MQTT Sub: Connection error: {e}")
            self.connected = False

    def start_listening(self):
        # Starts a blocking loop. For Tkinter, usually run in a separate thread,
        # or use loop_start() for a background thread.
        print("MQTT Sub: Starting network loop (loop_start).")
        self.client.loop_start() # Use non-blocking loop_start for Tkinter

    def stop_listening(self):
        print("MQTT Sub: Stopping network loop.")
        self.client.loop_stop()
        self.client.disconnect()
        self.connected = False
        print("MQTT Sub: Disconnected.")

if __name__ == '__main__':
    # Replace with your actual broker IP for testing
    # from config import MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_TOPIC_PLATES (if config is shared)
    MQTT_BROKER_HOST = "localhost" # or your broker's IP
    MQTT_BROKER_PORT = 1883
    MQTT_TOPIC_PLATES = "rpi/license_plates" # Must match topic used by Pi

    def test_callback(topic, payload):
        print(f"Test Callback - Topic: {topic}, Payload: {payload.decode()}")

    subscriber = MQTTSubscriber(MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_TOPIC_PLATES, test_callback)
    subscriber.connect()
    subscriber.start_listening() # Starts background thread

    print("MQTT Subscriber listening in background. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1) # Keep main thread alive for testing
    except KeyboardInterrupt:
        print("Stopping subscriber...")
    finally:
        subscriber.stop_listening()