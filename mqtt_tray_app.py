#!/usr/bin/env python3
"""
MQTT Desktop Notifier with System Tray Icon
Listens to a specified MQTT topic and displays desktop notifications when alerts are received.
Provides a system tray icon to show the application is running.
"""

import sys
import os
import signal
import logging
import subprocess
import threading
import time
import urllib.request
import json
from PyQt5 import QtWidgets, QtGui, QtCore, QtMultimedia
import paho.mqtt.client as mqtt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Get the directory of the current script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Settings file path
SETTINGS_FILE = os.path.join(SCRIPT_DIR, 'settings.json')

# Default MQTT Configuration
DEFAULT_MQTT_BROKER = "192.168.1.100"  # Replace with your Home Assistant IP
DEFAULT_MQTT_PORT = 1883
DEFAULT_MQTT_USER = "username"  # Replace with your MQTT username
DEFAULT_MQTT_PASSWORD = "password"  # Replace with your MQTT password
DEFAULT_MQTT_TOPIC = "homeassistant/binary_sensor/alert/state"  # Replace with your alert topic
TRIGGER_VALUES = ["on", "ON", "\"on\"", "\"ON\""]

# Settings class to manage MQTT configuration
class Settings:
    def __init__(self):
        self.broker = DEFAULT_MQTT_BROKER
        self.port = DEFAULT_MQTT_PORT
        self.user = DEFAULT_MQTT_USER
        self.password = DEFAULT_MQTT_PASSWORD
        self.topic = DEFAULT_MQTT_TOPIC
        self.load()
    
    def load(self):
        """Load settings from file"""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)
                    self.broker = settings.get('broker', DEFAULT_MQTT_BROKER)
                    self.port = settings.get('port', DEFAULT_MQTT_PORT)
                    self.user = settings.get('user', DEFAULT_MQTT_USER)
                    self.password = settings.get('password', DEFAULT_MQTT_PASSWORD)
                    self.topic = settings.get('topic', DEFAULT_MQTT_TOPIC)
                    logger.info(f"Loaded settings from {SETTINGS_FILE}")
            except Exception as e:
                logger.error(f"Error loading settings: {e}")
    
    def save(self):
        """Save settings to file"""
        settings = {
            'broker': self.broker,
            'port': self.port,
            'user': self.user,
            'password': self.password,
            'topic': self.topic
        }
        
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(settings, f, indent=4)
            logger.info(f"Saved settings to {SETTINGS_FILE}")
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False

# Create settings instance
settings = Settings()

class MQTTClient(threading.Thread):
    def __init__(self, app):
        threading.Thread.__init__(self)
        self.daemon = True
        self.app = app
        self.connected = False
        self.client = mqtt.Client()
        self.client.username_pw_set(settings.user, settings.password)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.last_alert_time = 0
        self.running = True
    
    def run(self):
        try:
            logger.info(f"Connecting to MQTT broker at {settings.broker}:{settings.port}...")
            self.client.connect(settings.broker, settings.port, 60)
            self.client.loop_start()
            
            # Keep the thread alive
            while self.running:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            self.app.mqtt_connection_failed()
    
    def stop(self):
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT broker")
            self.connected = True
            client.subscribe(settings.topic)
            logger.info(f"Subscribed to topic: {settings.topic}")
            self.app.mqtt_connected()
        else:
            logger.error(f"Failed to connect to MQTT broker with code: {rc}")
            self.connected = False
            self.app.mqtt_connection_failed()
    
    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode().strip().lower()
        logger.info(f"Message received on topic {msg.topic}: {payload}")
        
        if payload in [v.lower() for v in TRIGGER_VALUES]:
            # Avoid duplicate alerts within 10 seconds
            current_time = time.time()
            if current_time - self.last_alert_time > 10:
                self.last_alert_time = current_time
                self.app.show_alert_notification()
    
    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected disconnection from MQTT broker with code: {rc}")
            self.app.mqtt_disconnected()
        else:
            logger.info("Disconnected from MQTT broker")


class SystemTrayApp(QtWidgets.QSystemTrayIcon):
    def __init__(self, parent=None):
        QtWidgets.QSystemTrayIcon.__init__(self, parent)
        self.setToolTip('MQTT Alert Notifier')
        
        # Set up icons
        self.icon_connected = QtGui.QIcon(os.path.join(SCRIPT_DIR, 'icons', 'connected.png'))
        self.icon_disconnected = QtGui.QIcon(os.path.join(SCRIPT_DIR, 'icons', 'disconnected.png'))
        self.icon_alert = QtGui.QIcon(os.path.join(SCRIPT_DIR, 'icons', 'alert.png'))
        
        # Set up sound paths
        self.sounds_dir = os.path.join(SCRIPT_DIR, 'sounds')
        os.makedirs(self.sounds_dir, exist_ok=True)
        self.alert_sound_path = os.path.join(self.sounds_dir, 'alert.mp3')
        self.fallback_sound_path = os.path.join(self.sounds_dir, 'fallback_alert.mp3')
        
        # Create default icons if they don't exist
        self.create_default_icons()
        
        # Set initial icon
        self.setIcon(self.icon_disconnected)
        
        # Create menu
        self.menu = QtWidgets.QMenu()
        
        # Add status item (non-clickable)
        self.status_action = QtWidgets.QAction("Status: Disconnected")
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)
        
        self.menu.addSeparator()
        
        # Add reconnect option
        reconnect_action = QtWidgets.QAction("Reconnect")
        reconnect_action.triggered.connect(self.reconnect)
        self.menu.addAction(reconnect_action)
        
        # Add test notification option
        test_action = QtWidgets.QAction("Test Notification")
        test_action.triggered.connect(self.test_notification)
        self.menu.addAction(test_action)
        
        # Add settings option
        settings_action = QtWidgets.QAction("Settings")
        settings_action.triggered.connect(self.show_settings)
        self.menu.addAction(settings_action)
        
        self.menu.addSeparator()
        
        # Add about option
        about_action = QtWidgets.QAction("About")
        about_action.triggered.connect(self.show_about)
        self.menu.addAction(about_action)
        
        # Add quit option
        quit_action = QtWidgets.QAction("Quit")
        quit_action.triggered.connect(self.quit)
        self.menu.addAction(quit_action)
        
        # Set the menu
        self.setContextMenu(self.menu)
        
        # Show the icon
        self.show()
        
        # Set up a timer to reset the icon after an alert
        self.alert_timer = QtCore.QTimer(self)
        self.alert_timer.setSingleShot(True)
        self.alert_timer.timeout.connect(self.reset_icon_after_alert)
        
        # Set up a timer to check connection status
        self.connection_timer = QtCore.QTimer(self)
        self.connection_timer.setInterval(60000)  # Check every minute
        self.connection_timer.timeout.connect(self.check_connection)
        self.connection_timer.start()
        
        # Start MQTT client
        self.mqtt_client = MQTTClient(self)
        self.mqtt_client.start()
    
    def create_default_icons(self):
        """Create default icons if they don't exist."""
        icons_dir = os.path.join(SCRIPT_DIR, 'icons')
        os.makedirs(icons_dir, exist_ok=True)
        
        # Define icon paths
        connected_icon_path = os.path.join(icons_dir, 'connected.png')
        disconnected_icon_path = os.path.join(icons_dir, 'disconnected.png')
        alert_icon_path = os.path.join(icons_dir, 'alert.png')
        
        # Create connected icon if it doesn't exist
        if not os.path.exists(connected_icon_path):
            pixmap = QtGui.QPixmap(32, 32)
            pixmap.fill(QtCore.Qt.transparent)
            painter = QtGui.QPainter(pixmap)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QBrush(QtGui.QColor(0, 128, 0)))  # Green
            painter.drawEllipse(8, 8, 16, 16)
            painter.end()
            pixmap.save(connected_icon_path)
        
        # Create disconnected icon if it doesn't exist
        if not os.path.exists(disconnected_icon_path):
            pixmap = QtGui.QPixmap(32, 32)
            pixmap.fill(QtCore.Qt.transparent)
            painter = QtGui.QPainter(pixmap)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QBrush(QtGui.QColor(128, 128, 128)))  # Gray
            painter.drawEllipse(8, 8, 16, 16)
            painter.end()
            pixmap.save(disconnected_icon_path)
        
        # Create alert icon if it doesn't exist
        if not os.path.exists(alert_icon_path):
            pixmap = QtGui.QPixmap(32, 32)
            pixmap.fill(QtCore.Qt.transparent)
            painter = QtGui.QPainter(pixmap)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 0, 0)))  # Red
            painter.drawEllipse(8, 8, 16, 16)
            painter.end()
            pixmap.save(alert_icon_path)
        
        # Reload the icons
        self.icon_connected = QtGui.QIcon(connected_icon_path)
        self.icon_disconnected = QtGui.QIcon(disconnected_icon_path)
        self.icon_alert = QtGui.QIcon(alert_icon_path)
    
    def mqtt_connected(self):
        """Called when MQTT client connects successfully."""
        self.setIcon(self.icon_connected)
        self.status_action.setText("Status: Connected")
        self.showMessage('MQTT Alert Notifier', 'Connected to MQTT broker', self.icon_connected, 3000)
    
    def mqtt_disconnected(self):
        """Called when MQTT client disconnects."""
        self.setIcon(self.icon_disconnected)
        self.status_action.setText("Status: Disconnected")
    
    def mqtt_connection_failed(self):
        """Called when MQTT client fails to connect."""
        self.setIcon(self.icon_disconnected)
        self.status_action.setText("Status: Connection Failed")
        self.showMessage('MQTT Alert Notifier', 'Failed to connect to MQTT broker', self.icon_disconnected, 3000)
    
    def check_connection(self):
        """Periodically check if the MQTT client is still connected."""
        if self.mqtt_client and not self.mqtt_client.connected:
            logger.info("Connection check: Not connected. Attempting to reconnect...")
            self.reconnect()
    
    def reconnect(self):
        """Reconnect to the MQTT broker."""
        if self.mqtt_client:
            self.mqtt_client.stop()
        
        self.mqtt_client = MQTTClient(self)
        self.mqtt_client.start()
    
    def show_alert_notification(self):
        """Show alert notification and change icon."""
        self.setIcon(self.icon_alert)
        self.showMessage(
            'Alert Notification', 
            'Emergency alert received! Please check official sources.',
            self.icon_alert,
            10000  # Show for 10 seconds
        )
        
        # Play alert sound
        self.play_alert_sound()
        
        # Reset icon after 30 seconds
        self.alert_timer.start(30000)
    
    def reset_icon_after_alert(self):
        """Reset icon to connected state after alert."""
        if self.mqtt_client and self.mqtt_client.connected:
            self.setIcon(self.icon_connected)
        else:
            self.setIcon(self.icon_disconnected)
    
    def test_notification(self):
        """Test the notification system."""
        self.show_alert_notification()
    
    def show_about(self):
        """Show about dialog."""
        QtWidgets.QMessageBox.about(
            None,
            "About MQTT Alert Notifier",
            "MQTT Alert Notifier v1.0\n\n"
            "This application listens to MQTT alerts and displays desktop notifications.\n\n"
            "Connected to: " + settings.broker + "\n"
            "Topic: " + settings.topic
        )
    
    def show_settings(self):
        """Show settings dialog."""
        # Create dialog
        dialog = QtWidgets.QDialog(None)
        dialog.setWindowTitle("MQTT Alert Notifier Settings")
        dialog.setMinimumWidth(400)
        
        # Create form layout
        layout = QtWidgets.QVBoxLayout()
        form_layout = QtWidgets.QFormLayout()
        
        # MQTT Broker
        broker_label = QtWidgets.QLabel("MQTT Broker IP:")
        broker_input = QtWidgets.QLineEdit(settings.broker)
        form_layout.addRow(broker_label, broker_input)
        
        # MQTT Port
        port_label = QtWidgets.QLabel("MQTT Port:")
        port_input = QtWidgets.QSpinBox()
        port_input.setRange(1, 65535)
        port_input.setValue(settings.port)
        form_layout.addRow(port_label, port_input)
        
        # MQTT Username
        user_label = QtWidgets.QLabel("MQTT Username:")
        user_input = QtWidgets.QLineEdit(settings.user)
        form_layout.addRow(user_label, user_input)
        
        # MQTT Password
        password_label = QtWidgets.QLabel("MQTT Password:")
        password_input = QtWidgets.QLineEdit(settings.password)
        password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        form_layout.addRow(password_label, password_input)
        
        # MQTT Topic
        topic_label = QtWidgets.QLabel("MQTT Topic:")
        topic_input = QtWidgets.QLineEdit(settings.topic)
        form_layout.addRow(topic_label, topic_input)
        
        # Add form to layout
        layout.addLayout(form_layout)
        
        # Add buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        
        # Show dialog and process result
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            # Get values from form
            new_broker = broker_input.text().strip()
            new_port = port_input.value()
            new_user = user_input.text().strip()
            new_password = password_input.text()
            new_topic = topic_input.text().strip()
            
            # Validate inputs
            if not new_broker:
                QtWidgets.QMessageBox.warning(None, "Error", "MQTT Broker IP cannot be empty.")
                return
            
            if not new_topic:
                QtWidgets.QMessageBox.warning(None, "Error", "MQTT Topic cannot be empty.")
                return
            
            # Update settings
            settings.broker = new_broker
            settings.port = new_port
            settings.user = new_user
            settings.password = new_password
            settings.topic = new_topic
            
            # Save settings
            if settings.save():
                # Show confirmation
                QtWidgets.QMessageBox.information(
                    None, 
                    "Settings Saved", 
                    "Settings have been saved. Reconnecting to apply changes..."
                )
                
                # Reconnect with new settings
                self.reconnect()
            else:
                QtWidgets.QMessageBox.warning(
                    None, 
                    "Error", 
                    "Failed to save settings. Check permissions and try again."
                )
    
    def quit(self):
        """Quit the application."""
        if self.mqtt_client:
            self.mqtt_client.stop()
        QtWidgets.QApplication.quit()
        
    def play_alert_sound(self):
        """Play the alert sound."""
        try:
            # Check if the custom alert sound file exists
            if os.path.exists(self.alert_sound_path):
                sound_file = self.alert_sound_path
                logger.info(f"Using custom alert sound: {sound_file}")
            else:
                # If custom sound doesn't exist, use fallback
                logger.warning(f"Custom alert sound not found at {self.alert_sound_path}")
                
                # Check if fallback sound exists, if not download a default one
                if not os.path.exists(self.fallback_sound_path):
                    logger.info("Fallback sound not found. Downloading a default one...")
                    try:
                        # URL for a sample alert sound
                        sound_url = "https://www.soundjay.com/mechanical/sounds/alarm-1.mp3"
                        urllib.request.urlretrieve(sound_url, self.fallback_sound_path)
                        logger.info(f"Downloaded alert sound to {self.fallback_sound_path}")
                    except Exception as download_error:
                        logger.error(f"Failed to download alert sound: {download_error}")
                
                sound_file = self.fallback_sound_path
            
            # Use system audio player to play the sound
            subprocess.Popen(['paplay', sound_file])
            
            # Play the sound multiple times for emphasis
            for _ in range(2):
                # Wait a bit between plays
                QtCore.QTimer.singleShot(1500, lambda: subprocess.Popen(['paplay', sound_file]))
                
        except Exception as e:
            logger.error(f"Failed to play alert sound: {e}")
            # Fallback to system beep
            QtWidgets.QApplication.beep()


if __name__ == "__main__":
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running when no windows are open
    
    # Create and display the system tray icon
    tray_icon = SystemTrayApp()
    
    # Start the application event loop
    sys.exit(app.exec_())
