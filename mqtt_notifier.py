#!/usr/bin/env python3
"""
MQTT Desktop Notifier
Listens to a specified MQTT topic and displays desktop notifications when alerts are received.
"""

import paho.mqtt.client as mqtt
import subprocess
import logging
import sys
import time
import signal
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# MQTT Configuration
MQTT_BROKER = "192.168.1.100"  # Replace with your Home Assistant IP
MQTT_PORT = 1883
MQTT_USER = "username"  # Replace with your MQTT username
MQTT_PASSWORD = "password"  # Replace with your MQTT password
MQTT_TOPIC = "homeassistant/binary_sensor/alert/state"  # Replace with your alert topic
TRIGGER_VALUES = ["on", "ON", "\"on\"", "\"ON\""]

def send_notification(title, message):
    """Send a desktop notification using notify-send."""
    try:
        subprocess.run(["notify-send", title, message])
        logger.info(f"Notification sent: {title} - {message}")
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")

def on_connect(client, userdata, flags, rc):
    """Callback for when the client connects to the MQTT broker."""
    if rc == 0:
        logger.info("Connected to MQTT broker")
        client.subscribe(MQTT_TOPIC)
        logger.info(f"Subscribed to topic: {MQTT_TOPIC}")
    else:
        logger.error(f"Failed to connect to MQTT broker with code: {rc}")

def on_message(client, userdata, msg):
    """Callback for when a message is received from the MQTT broker."""
    payload = msg.payload.decode().strip().lower()
    logger.info(f"Message received on topic {msg.topic}: {payload}")
    
    if payload in [v.lower() for v in TRIGGER_VALUES]:
        send_notification("Alert Notification", "Emergency alert received! Please check official sources.")

def on_disconnect(client, userdata, rc):
    """Callback for when the client disconnects from the MQTT broker."""
    if rc != 0:
        logger.warning(f"Unexpected disconnection from MQTT broker with code: {rc}")
    else:
        logger.info("Disconnected from MQTT broker")

def signal_handler(sig, frame):
    """Handle keyboard interrupts gracefully."""
    logger.info("Shutting down MQTT notifier...")
    client.disconnect()
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create MQTT client
    client = mqtt.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    
    # Set up callbacks
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    # Connect to MQTT broker
    try:
        logger.info(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
    except Exception as e:
        logger.error(f"Failed to connect to MQTT broker: {e}")
        sys.exit(1)
    
    # Start the MQTT client loop
    try:
        logger.info("MQTT notifier started. Press Ctrl+C to exit.")
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down MQTT notifier...")
        client.disconnect()
        sys.exit(0)
