# raspberry_pi_code/mqtt_utils.py
import paho.mqtt.client as mqtt
import json
import time

class MQTTClient:
    def __init__(self, broker_host, broker_port, client_id_prefix="rpi_plate_publisher"):
        self.broker_host = broker_host
        self.broker_port = broker_port
        # Ensure unique client ID if multiple instances run
        self.client_id = f"{client_id_prefix}-{int(time.time())}" 
        self.client = mqtt.Client(client_id=self.client_id)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.connected = False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"MQTT: Connected to broker {self.broker_host} successfully.")
            self.connected = True
        else:
            print(f"MQTT: Failed to connect, return code {rc}")
            self.connected = False

    def _on_disconnect(self, client, userdata, rc):
        print(f"MQTT: Disconnected from broker with result code {rc}. Attempting to reconnect...")
        self.connected = False
        # Simple reconnect logic, could be more robust
        # self.connect() # Be careful with immediate reconnect loops

    def connect(self):
        try:
            print(f"MQTT: Attempting to connect to {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start() # Start a background thread for network traffic
        except Exception as e:
            print(f"MQTT: Connection error: {e}")
            self.connected = False

    def publish(self, topic, payload_dict):
        if not self.connected:
            print("MQTT: Not connected. Cannot publish.")
            # Optionally, try to reconnect here or queue messages
            # self.connect() # Attempt reconnect, might lead to issues if broker is truly down
            return False
        try:
            payload_json = json.dumps(payload_dict)
            result = self.client.publish(topic, payload_json)
            # result.wait_for_publish() # Uncomment if you need to ensure message is sent
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                # print(f"MQTT: Published to {topic}: {payload_json}")
                return True
            else:
                print(f"MQTT: Failed to publish to {topic}. Error code: {result.rc}")
                return False
        except Exception as e:
            print(f"MQTT: Error publishing message: {e}")
            return False

    def disconnect(self):
        print("MQTT: Disconnecting...")
        self.client.loop_stop() # Stop the background thread
        self.client.disconnect()
        self.connected = False
        print("MQTT: Disconnected.")

if __name__ == '__main__':
    # Replace with your actual broker IP for testing
    # from config import MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_TOPIC_PLATES
    MQTT_BROKER_HOST = "localhost" # or your broker's IP
    MQTT_BROKER_PORT = 1883
    MQTT_TOPIC_PLATES = "rpi/test_plates"

    mqtt_publisher = MQTTClient(MQTT_BROKER_HOST, MQTT_BROKER_PORT)
    mqtt_publisher.connect()
    
    # Wait for connection to establish
    timeout = 10  # seconds
    start_time = time.time()
    while not mqtt_publisher.connected and (time.time() - start_time) < timeout:
        time.sleep(0.1)

    if mqtt_publisher.connected:
        test_payload = {"plate": "TESTMQTT", "timestamp": time.time(), "confidence": 0.99}
        mqtt_publisher.publish(MQTT_TOPIC_PLATES, test_payload)
        print(f"Test message published to {MQTT_TOPIC_PLATES}")
        time.sleep(1) # Give time for message to send
        mqtt_publisher.disconnect()
    else:
        print("MQTT test failed: Could not connect to broker.")