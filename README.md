# Red Alert MQTT Desktop Notifier

A Python application that listens to a specified MQTT topic from Home Assistant and displays desktop notifications when alerts are received. Features a system tray icon that provides visual feedback on the connection status. Originally designed for Red Alert notifications in Israel, but can be adapted for any type of alert system that publishes to MQTT topics.

## Features

- Connects to an MQTT broker with authentication
- Listens to a specific topic for alerts
- Displays desktop notifications when alerts are received
- System tray icon shows connection status (green = connected, gray = disconnected, red = alert)
- Right-click menu for testing notifications, reconnecting, and viewing status
- Can run as a systemd service for automatic startup

## Prerequisites

- Python 3
- `notify-send` command (usually pre-installed on Ubuntu)
- PyQt5 (installed automatically by the setup script)

## Installation

1. Clone this repository or download the files to your preferred location.

2. Make the start script executable:
   ```bash
   chmod +x start_notifier.sh
   ```

3. Run the start script to create a virtual environment and install dependencies:
   ```bash
   ./start_notifier.sh
   ```

## Manual Usage

Simply run the start script:
```bash
./start_notifier.sh
```

## Automatic Startup (Optional)

To have the notifier start automatically when you log in:

1. Copy the systemd service file to your user's systemd directory:
   ```bash
   mkdir -p ~/.config/systemd/user/
   cp mqtt-notifier.service ~/.config/systemd/user/
   ```

2. Enable and start the service:
   ```bash
   systemctl --user enable mqtt-notifier.service
   systemctl --user start mqtt-notifier.service
   ```

3. Check the status:
   ```bash
   systemctl --user status mqtt-notifier.service
   ```

## Configuration

Before using this application, you need to configure your MQTT connection details in both the `mqtt_notifier.py` and `mqtt_tray_app.py` files:

```python
# MQTT Configuration
MQTT_BROKER = "192.168.1.100"  # Replace with your Home Assistant IP
MQTT_PORT = 1883
MQTT_USER = "username"  # Replace with your MQTT username
MQTT_PASSWORD = "password"  # Replace with your MQTT password
MQTT_TOPIC = "homeassistant/binary_sensor/alert/state"  # Replace with your alert topic
TRIGGER_VALUES = ["on", "ON", "\"on\"", "\"ON\""]
```

You'll also need to modify the notification message in both files to match your specific use case:

```python
send_notification("Alert Notification", "Emergency alert received! Please check official sources.")
```

And update the service file path in `mqtt-notifier.service` to match your installation location:

```
ExecStart=/bin/bash %h/path/to/Red-Alert-MQTT-Desktop-Notifier/start_notifier.sh
```

## Troubleshooting

If you encounter issues:

1. Check that the MQTT broker is reachable
2. Verify your MQTT credentials
3. Ensure the topic exists and is being published to
4. Check the console output for error messages
