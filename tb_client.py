# raspberry_pi_code/tb_client.py
import paho.mqtt.client as mqtt
import json
import time

class ThingsboardClient:
    def __init__(self, host, port=1883, access_token=None):
        self.host = host
        self.port = port
        self.access_token = access_token # This will be the MQTT username
        self.client_id = f"tb_client_{int(time.time())}" # Unique client ID

        self.client = mqtt.Client(client_id=self.client_id)
        if self.access_token:
            self.client.username_pw_set(self.access_token) # Username is the access token

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.connected = False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"ThingsBoard: Connected to {self.host} successfully.")
            self.connected = True
        else:
            print(f"ThingsBoard: Failed to connect, return code {rc}")
            self.connected = False

    def _on_disconnect(self, client, userdata, rc):
        print(f"ThingsBoard: Disconnected with result code {rc}.")
        self.connected = False

    def connect(self):
        try:
            print(f"ThingsBoard: Attempting to connect to {self.host}:{self.port}")
            self.client.connect(self.host, self.port, 60)
            self.client.loop_start()
        except Exception as e:
            print(f"ThingsBoard: Connection error: {e}")
            self.connected = False

    def publish_telemetry(self, data_dict):
        """
        Publishes telemetry data to ThingsBoard.
        data_dict: A dictionary of key-value pairs, e.g., {"plate": "ABC123", "confidence": 0.9}
        """
        if not self.connected:
            print("ThingsBoard: Not connected. Cannot publish telemetry.")
            return False
        
        topic = "v1/devices/me/telemetry"
        payload = json.dumps(data_dict)
        try:
            result = self.client.publish(topic, payload)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                # print(f"ThingsBoard: Published telemetry to {topic}: {payload}")
                return True
            else:
                print(f"ThingsBoard: Failed to publish telemetry. Error code: {result.rc}")
                return False
        except Exception as e:
            print(f"ThingsBoard: Error publishing telemetry: {e}")
            return False

    def disconnect(self):
        print("ThingsBoard: Disconnecting...")
        self.client.loop_stop()
        self.client.disconnect()
        self.connected = False
        print("ThingsBoard: Disconnected.")

if __name__ == '__main__':
    # Replace with your ThingsBoard host and device access token for testing
    # from config import THINGSBOARD_HOST, THINGSBOARD_PORT, DEVICE_ACCESS_TOKEN
    THINGSBOARD_HOST = "localhost" # or demo.thingsboard.io, etc.
    THINGSBOARD_PORT = 1883
    DEVICE_ACCESS_TOKEN = "YOUR_DEVICE_TOKEN_HERE" 

    if DEVICE_ACCESS_TOKEN == "YOUR_DEVICE_TOKEN_HERE":
        print("Please set your THINGSBOARD_HOST and DEVICE_ACCESS_TOKEN for testing.")
    else:
        tb_cli = ThingsboardClient(THINGSBOARD_HOST, THINGSBOARD_PORT, DEVICE_ACCESS_TOKEN)
        tb_cli.connect()

        timeout = 10
        start_time = time.time()
        while not tb_cli.connected and (time.time() - start_time) < timeout:
            time.sleep(0.1)

        if tb_cli.connected:
            telemetry_data = {"plate": "TBTEST1", "confidence": 0.92, "rpi_temp": 45.5}
            tb_cli.publish_telemetry(telemetry_data)
            print("Test telemetry published to ThingsBoard.")
            time.sleep(1)
            tb_cli.disconnect()
        else:
            print("ThingsBoard test failed: Could not connect.")