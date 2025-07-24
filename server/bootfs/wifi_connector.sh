#!/bin/bash
# ==============================================================================
# wifi_connector.sh - Wi-Fi Connection Script
# ==============================================================================
#
# IMPORTANT: If you edit this file on Windows, you MUST save it with
# Unix-style line endings (LF), not Windows-style (CRLF).
#
# Description:
# This script runs on boot to establish a Wi-Fi connection using NetworkManager.
# It reads all network configuration from /boot/firmware/pi_settings.conf
# and prioritizes standard WPA/WPA2-PSK connections, falling back to
# WPA2-Enterprise if a standard password is not provided.
#
# ==============================================================================

set -e # Exit immediately if a command fails

LOG_FILE="/boot/firmware/wifi_connect.log"
PI_SETTINGS_FILE="/boot/firmware/pi_settings.conf"
WIFI_INTERFACE="wlan0"

# Safe logging function
log() {
    # Prepend timestamp and append to log file
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# --- Main Logic ---
# Clear previous log and start fresh
echo "--- Starting wifi_connector.sh at $(date) ---" > "$LOG_FILE"

# 1. Load configuration
if [ ! -f "$PI_SETTINGS_FILE" ]; then
    log "FATAL: Settings file not found at '$PI_SETTINGS_FILE'. Cannot connect."
    exit 1
fi
source "$PI_SETTINGS_FILE"
log "Configuration loaded from '$PI_SETTINGS_FILE'."

# 2. Check if required SSID setting is present
if [ -z "$WIFI_SSID" ]; then
    log "FATAL: WIFI_SSID is not set in '$PI_SETTINGS_FILE'."
    exit 1
fi

# Sanitize variables to remove potential Windows carriage returns
WIFI_SSID_CLEAN=$(echo "$WIFI_SSID" | tr -d '\r')
WIFI_PASSWORD_CLEAN=$(echo "$WIFI_PASSWORD" | tr -d '\r')
WIFI_ENTERPRISE_USERNAME_CLEAN=$(echo "$WIFI_ENTERPRISE_USERNAME" | tr -d '\r')
WIFI_ENTERPRISE_PASSWORD_CLEAN=$(echo "$WIFI_ENTERPRISE_PASSWORD" | tr -d '\r')

# 3. Check if the connection profile already exists and is active
log "Checking if connection '$WIFI_SSID_CLEAN' is already active..."
if nmcli -t --fields GENERAL.STATE connection show "$WIFI_SSID_CLEAN" 2>/dev/null | grep -q "activated"; then
    log "Connection '$WIFI_SSID_CLEAN' is already active. No action needed."
    echo "--- wifi_connector.sh finished ---" >> "$LOG_FILE"
    exit 0
fi
log "Connection not active. Proceeding with setup."

# 4. If the connection profile does not exist, create it
if ! nmcli connection show "$WIFI_SSID_CLEAN" > /dev/null 2>&1; then
    log "Connection profile '$WIFI_SSID_CLEAN' not found. Creating it now..."

    # Prioritize standard WPA/WPA2-PSK connections as they are more common
    if [ -n "$WIFI_PASSWORD_CLEAN" ]; then
        log "Found standard WPA/WPA2 password. Creating WPA-PSK profile."
        nmcli connection add type wifi con-name "$WIFI_SSID_CLEAN" ifname "$WIFI_INTERFACE" ssid "$WIFI_SSID_CLEAN" -- \
            wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$WIFI_PASSWORD_CLEAN"
    
    # Fallback to Enterprise credentials if a standard password is not set
    elif [ -n "$WIFI_ENTERPRISE_USERNAME_CLEAN" ] && [ -n "$WIFI_ENTERPRISE_PASSWORD_CLEAN" ]; then
        log "No standard password found. Found Enterprise credentials. Creating WPA2-EAP profile."
        nmcli connection add type wifi con-name "$WIFI_SSID_CLEAN" ifname "$WIFI_INTERFACE" ssid "$WIFI_SSID_CLEAN" -- \
            wifi-sec.key-mgmt wpa-eap 802-1x.eap ttls 802-1x.phase2-auth mschapv2 \
            802-1x.identity "$WIFI_ENTERPRISE_USERNAME_CLEAN" 802-1x.password "$WIFI_ENTERPRISE_PASSWORD_CLEAN"
    
    # If no passwords are provided at all
    else
        log "FATAL: No password provided. Neither WIFI_PASSWORD nor Enterprise credentials were found in settings."
        exit 1
    fi

    if [ $? -ne 0 ]; then
        log "FATAL: Failed to create the connection profile with nmcli."
        exit 1
    fi
    log "Profile '$WIFI_SSID_CLEAN' created successfully."
fi

# 5. Attempt to bring the connection up
log "Activating connection '$WIFI_SSID_CLEAN'..."
if nmcli connection up "$WIFI_SSID_CLEAN"; then
    log "Success: Connection is now active."
else
    log "ERROR: Failed to activate the connection. Please check credentials and network availability."
    # We don't exit with an error here, as the network may just be temporarily unavailable
    # The service will retry on the next boot
fi

log "--- wifi_connector.sh finished ---"
exit 0
