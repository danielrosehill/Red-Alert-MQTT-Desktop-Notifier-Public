#!/bin/bash
# Script to start the MQTT notifier

# Determine the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists, create if it doesn't
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install or update dependencies
echo "Installing dependencies..."
python -m pip install -r requirements.txt

# Run the notifier with system tray icon
echo "Starting MQTT notifier with system tray icon..."
python mqtt_tray_app.py
