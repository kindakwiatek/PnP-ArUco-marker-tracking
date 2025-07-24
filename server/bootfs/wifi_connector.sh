#!/bin/bash
# ==============================================================================
# wifi_connect.sh - Permanent WiFi Connection Script
# ==============================================================================
#
# IMPORTANT: If you edit this file on Windows, you MUST save it with
# Unix-style line endings (LF), not Windows-style (CRLF). Use an editor
# like VS Code or Notepad++ to ensure this is correct, otherwise you will get
# syntax errors.
#
# Description:
# This script runs on boot to establish a Wi-Fi connection. It reads all
# network configuration from /boot/firmware/pi_settings.conf.
#
# ==============================================================================

LOG_FILE="/boot/firmware/wifi_connect.log"
PI_SETTINGS_FILE="/boot/firmware/pi_settings.conf"
WIFI_INTERFACE="wlan0"

# Safe logging function
log() {
    echo "$(date): $1" >> "$LOG_FILE"
}

echo "--- Starting wifi-connect.sh at $(date) ---" > "$LOG_FILE"

# --- Main Logic ---
log "Initial delay to allow system to settle."
sleep 5

# 1. Load configuration
if [ ! -f "$PI_SETTINGS_FILE" ]; then
    log "ERROR: Settings file not found at '$PI_SETTINGS_FILE'. Cannot connect."
    exit 1
fi
source "$PI_SETTINGS_FILE"
log "Configuration loaded."

# Sanitize potential Windows line endings
USERNAME=${WIFI_USERNAME//$'\r'/}
PASSWORD=${WIFI_PASSWORD//$'\r'/}
CONNECTION_NAME=${WIFI_SSID//$'\r'/}

# 2. Check if required settings are present
if [ -z "$CONNECTION_NAME" ]; then
    log "ERROR: WIFI_SSID is not set in '$PI_SETTINGS_FILE'."
    exit 1
fi

# 3. Check if connection is already active
log "Checking if connection '$CONNECTION_NAME' is already active..."
if nmcli -t --fields GENERAL.STATE connection show "$CONNECTION_NAME" 2>/dev/null | grep -q "activated"; then
    log "Connection '$CONNECTION_NAME' is already active. Nothing to do."
    echo "--- wifi-connect.sh finished ---" >> "$LOG_FILE"
    exit 0
fi
log "Connection not active. Proceeding."

# 4. Check if the connection profile exists. If not, create it.
if ! nmcli connection show "$CONNECTION_NAME" > /dev/null 2>&1; then
    log "Connection profile '$CONNECTION_NAME' not found. Creating it..."

    # Check for Enterprise credentials
    if [ -n "$USERNAME" ] && [ -n "$PASSWORD" ]; then
        log "Found Enterprise credentials. Creating WPA2-EAP profile."
        nmcli connection add type wifi con-name "$CONNECTION_NAME" ifname "$WIFI_INTERFACE" ssid "$WIFI_SSID" -- \
            wifi-sec.key-mgmt wpa-eap 802-1x.eap ttls 802-1x.phase2-auth mschapv2 \
            802-1x.identity "$USERNAME" 802-1x.password "$PASSWORD" >> "$LOG_FILE" 2>&1
    else
        log "No Enterprise credentials. Creating standard WPA2-PSK profile (will prompt for password if needed)."
        nmcli connection add type wifi con-name "$CONNECTION_NAME" ifname "$WIFI_INTERFACE" ssid "$WIFI_SSID" >> "$LOG_FILE" 2>&1
    fi

    if [ $? -ne 0 ]; then
        log "ERROR: Failed to create connection profile."
        exit 1
    fi
    log "Profile created successfully."
fi

# 5. Attempt to bring the connection up
log "Activating connection '$CONNECTION_NAME'..."
if nmcli connection up "$CONNECTION_NAME" >> "$LOG_FILE" 2>&1; then
    log "Success: Connection is now active."
else
    log "ERROR: Failed to activate the connection. Check credentials and network."
    exit 1
fi

log "--- wifi-connect.sh finished ---"
exit 0
