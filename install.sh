#!/bin/bash
# Installation script for MQTT Alert Notifier

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Determine the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo -e "${GREEN}MQTT Alert Notifier Installation${NC}"
echo "==============================="
echo

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed.${NC}"
    echo "Please install Python 3 and try again."
    exit 1
fi

# Check if notify-send is installed
if ! command -v notify-send &> /dev/null; then
    echo -e "${YELLOW}Warning: notify-send is not installed.${NC}"
    echo "Installing notify-send (libnotify-bin)..."
    sudo apt-get update
    sudo apt-get install -y libnotify-bin
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${GREEN}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Make scripts executable
echo -e "${GREEN}Making scripts executable...${NC}"
chmod +x mqtt_notifier.py
chmod +x mqtt_tray_app.py
chmod +x start_notifier.sh

# Create desktop shortcut
echo -e "${GREEN}Creating desktop shortcut...${NC}"
DESKTOP_FILE="$HOME/.local/share/applications/mqtt-alert-notifier.desktop"

mkdir -p "$HOME/.local/share/applications"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=MQTT Alert Notifier
Comment=Displays notifications for MQTT alerts
Exec=$SCRIPT_DIR/start_notifier.sh
Icon=$SCRIPT_DIR/icons/connected.png
Terminal=false
Categories=Utility;
StartupNotify=true
X-GNOME-Autostart-enabled=true
EOF

# Set up systemd service
echo -e "${GREEN}Setting up systemd service...${NC}"
SYSTEMD_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_DIR"
cp mqtt-notifier.service "$SYSTEMD_DIR/"

# Enable and start the service
echo -e "${GREEN}Enabling and starting the service...${NC}"
systemctl --user daemon-reload
systemctl --user enable mqtt-notifier.service
systemctl --user start mqtt-notifier.service

# Check service status
echo -e "${GREEN}Checking service status...${NC}"
systemctl --user status mqtt-notifier.service

echo
echo -e "${GREEN}Installation complete!${NC}"
echo "The MQTT Alert Notifier is now installed and running."
echo "You should see the system tray icon in your notification area."
echo
echo "To start the application manually, you can:"
echo "  1. Run ./start_notifier.sh from this directory"
echo "  2. Click on the MQTT Alert Notifier icon in your applications menu"
echo
echo "To uninstall, run ./uninstall.sh"
