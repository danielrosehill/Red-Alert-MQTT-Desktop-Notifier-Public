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
from PyQt5 import QtWidgets, QtGui, QtCore
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

# MQTT Configuration
MQTT_BROKER = "192.168.1.100"  # Replace with your Home Assistant IP
MQTT_PORT = 1883
MQTT_USER = "username"  # Replace with your MQTT username
MQTT_PASSWORD = "password"  # Replace with your MQTT password
MQTT_TOPIC = "homeassistant/binary_sensor/alert/state"  # Replace with your alert topic
TRIGGER_VALUES = ["on", "ON", "\"on\"", "\"ON\""]

# Get the directory of the current script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

class MQTTClient(threading.Thread):
    def __init__(self, app):
        threading.Thread.__init__(self)
        self.daemon = True
        self.app = app
        self.connected = False
        self.client = mqtt.Client()
        self.client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.last_alert_time = 0
        self.running = True
    
    def run(self):
        try:
            logger.info(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
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
            client.subscribe(MQTT_TOPIC)
            logger.info(f"Subscribed to topic: {MQTT_TOPIC}")
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
        
        # Create default icons if they don't exist
        self.create_default_icons()
        
        # Set initial icon
        self.setIcon(self.icon_disconnected)
        
        # Create menu
        self.menu = QtWidgets.QMenu(parent)
        
        # Add status indicator
        self.status_action = QtWidgets.QAction("Status: Disconnected")
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)
        
        self.menu.addSeparator()
        
        # Add actions
        self.reconnect_action = QtWidgets.QAction("Reconnect")
        self.reconnect_action.triggered.connect(self.reconnect)
        self.menu.addAction(self.reconnect_action)
        
        self.test_notification_action = QtWidgets.QAction("Test Notification")
        self.test_notification_action.triggered.connect(self.test_notification)
        self.menu.addAction(self.test_notification_action)
        
        self.menu.addSeparator()
        
        # Add about action
        about_action = QtWidgets.QAction("About")
        about_action.triggered.connect(self.show_about)
        self.menu.addAction(about_action)
        
        # Add quit action
        quit_action = QtWidgets.QAction("Quit")
        quit_action.triggered.connect(self.quit)
        self.menu.addAction(quit_action)
        
        # Set the menu
        self.setContextMenu(self.menu)
        
        # Show the icon
        self.show()
        
        # Start MQTT client in a separate thread
        self.mqtt_client = MQTTClient(self)
        self.mqtt_client.start()
        
        # Set up a timer to check connection status periodically
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.check_connection)
        self.timer.start(30000)  # Check every 30 seconds
        
        # Set up a timer to reset icon after alert
        self.alert_timer = QtCore.QTimer()
        self.alert_timer.timeout.connect(self.reset_icon_after_alert)
        self.alert_timer.setSingleShot(True)
    
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
            "Connected to: " + MQTT_BROKER + "\n"
            "Topic: " + MQTT_TOPIC
        )
    
    def quit(self):
        """Quit the application."""
        if self.mqtt_client:
            self.mqtt_client.stop()
        QtWidgets.QApplication.quit()


if __name__ == "__main__":
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running when no windows are open
    
    # Create and display the system tray icon
    tray_icon = SystemTrayApp()
    
    # Start the application event loop
    sys.exit(app.exec_())
