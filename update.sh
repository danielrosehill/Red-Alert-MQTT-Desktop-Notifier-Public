#!/bin/bash
# Update script for MQTT Alert Notifier

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Determine the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo -e "${GREEN}MQTT Alert Notifier Update${NC}"
echo "=========================="
echo

# Check if the application is installed
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Running full installation instead...${NC}"
    echo
    ./install.sh
    exit 0
fi

# Stop the service if it's running
echo -e "${GREEN}Stopping the service if running...${NC}"
systemctl --user stop mqtt-notifier.service 2>/dev/null || true

# Check for git repository and pull latest changes if available
if [ -d ".git" ]; then
    echo -e "${GREEN}Updating from git repository...${NC}"
    git pull
    echo
fi

# Update virtual environment and dependencies
echo -e "${GREEN}Updating dependencies...${NC}"
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Make scripts executable
echo -e "${GREEN}Making scripts executable...${NC}"
chmod +x mqtt_notifier.py
chmod +x mqtt_tray_app.py
chmod +x start_notifier.sh
chmod +x install.sh
chmod +x uninstall.sh
chmod +x update.sh

# Create sounds directory if it doesn't exist
echo -e "${GREEN}Checking sounds directory...${NC}"
mkdir -p sounds

# Create icons directory if it doesn't exist
echo -e "${GREEN}Checking icons directory...${NC}"
mkdir -p icons

# Update desktop shortcut
echo -e "${GREEN}Updating desktop shortcut...${NC}"
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

# Update systemd service
echo -e "${GREEN}Updating systemd service...${NC}"
SYSTEMD_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_DIR"
cp mqtt-notifier.service "$SYSTEMD_DIR/"

# Reload systemd
systemctl --user daemon-reload

# Restart the service
echo -e "${GREEN}Restarting the service...${NC}"
systemctl --user restart mqtt-notifier.service

# Check service status
echo -e "${GREEN}Checking service status...${NC}"
systemctl --user status mqtt-notifier.service

echo
echo -e "${GREEN}Update complete!${NC}"
echo "The MQTT Alert Notifier has been updated and restarted."
echo "You should see the system tray icon in your notification area."
