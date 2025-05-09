#!/bin/bash
# Uninstallation script for MQTT Alert Notifier

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}MQTT Alert Notifier Uninstallation${NC}"
echo "================================="
echo

# Stop and disable the systemd service
echo -e "${GREEN}Stopping and disabling the service...${NC}"
systemctl --user stop mqtt-notifier.service 2>/dev/null || true
systemctl --user disable mqtt-notifier.service 2>/dev/null || true
systemctl --user daemon-reload

# Remove the systemd service file
echo -e "${GREEN}Removing systemd service file...${NC}"
rm -f "$HOME/.config/systemd/user/mqtt-notifier.service"

# Remove desktop shortcut
echo -e "${GREEN}Removing desktop shortcut...${NC}"
rm -f "$HOME/.local/share/applications/mqtt-alert-notifier.desktop"

# Ask if user wants to remove the entire directory
echo
echo -e "${YELLOW}Do you want to remove all files including the virtual environment?${NC}"
read -p "This will delete the entire directory (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Determine the script directory
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    
    # Move up one directory
    cd ..
    
    # Remove the directory
    echo -e "${GREEN}Removing all files...${NC}"
    rm -rf "$SCRIPT_DIR"
    
    echo -e "${GREEN}Uninstallation complete. All files have been removed.${NC}"
else
    echo -e "${GREEN}Uninstallation complete. Files have been kept.${NC}"
    echo "You can manually remove the directory if needed."
fi
