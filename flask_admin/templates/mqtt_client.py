# mqtt_client.py
import paho.mqtt.client as mqtt
import json

class MQTTClient:
    def __init__(self, broker, port, topic, username=None, password=None):
        self.broker = broker
        self.port = port
        self.topic = topic
        self.client = mqtt.Client()
        if username and password:
            self.client.username_pw_set(username, password)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print(f"Failed to connect, return code {rc}\n")

    def on_disconnect(self, client, userdata, rc):
        print("Disconnected from MQTT Broker.")

    def connect(self):
        self.client.connect(self.broker, self.port, 60)
        self.client.loop_start()

    def publish(self, payload):
        # Payload should be a dict
        json_payload = json.dumps(payload)
        result = self.client.publish(self.topic, json_payload)
        return result.is_published()

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()