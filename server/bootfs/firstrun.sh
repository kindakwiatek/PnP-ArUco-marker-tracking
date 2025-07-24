#!/bin/bash
# ==============================================================================
# firstrun.sh - One-Time System Setup Script
# ==============================================================================
#
# IMPORTANT: If you edit this file on Windows, you MUST save it with
# Unix-style line endings (LF), not Windows-style (CRLF).
#
# Description:
# This script runs ONLY ONCE on the first boot to perform all initial
# system and application setup. It is executed with root privileges.
#
# Execution Order:
# 1. Load all settings from pi_settings.conf.
# 2. Perform critical system setup (hostname, user, passwords, locale).
# 3. Set up and enable systemd services for networking and the application.
# 4. Clean itself up to prevent re-running on subsequent boots.
# 5. Reboot the system to apply all changes.
#
# ==============================================================================

# Exit immediately if any command fails
set -e

# Redirect all standard output and error to a log file on the boot partition
exec &> /boot/firmware/firstrun.log

echo "--- Starting firstrun.sh at $(date) ---"

# --- Log Function ---
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# --- Load Configuration ---
PI_SETTINGS_FILE="/boot/firmware/pi_settings.conf"
if [ -f "$PI_SETTINGS_FILE" ]; then
    source "$PI_SETTINGS_FILE"
    log "Successfully loaded settings from $PI_SETTINGS_FILE"
else
    log "FATAL: Configuration file not found at $PI_SETTINGS_FILE. Exiting."
    exit 1
fi

# ==============================================================================
# SECTION 1: CRITICAL SYSTEM CONFIGURATION
# All steps here are completed before any services are set up.
# ==============================================================================

log "--- Starting critical system configuration ---"

# --- Hostname Setup ---
TARGET_HOSTNAME="${NEW_HOSTNAME:-rpi-mocap-1}" # Use default if not set
CURRENT_HOSTNAME=$(hostname)
log "Setting hostname from '$CURRENT_HOSTNAME' to '$TARGET_HOSTNAME'..."
hostnamectl set-hostname "$TARGET_HOSTNAME"
# Update hosts file to map the new hostname to the local loopback address
sed -i "s/127.0.1.1.*$CURRENT_HOSTNAME/127.0.1.1\\t$TARGET_HOSTNAME/g" /etc/hosts
log "Hostname setup complete."

# --- User and Password Setup ---
FIRSTUSER=$(getent passwd 1000 | cut -d: -f1) # Get the default user (e.g., 'pi')
USER_TO_CONFIGURE="${SSH_USERNAME:-user}" # Fallback to 'user' if not set

log "Configuring user '$USER_TO_CONFIGURE'..."
if [ -n "$SSH_USERNAME" ] && [ -n "$SSH_PASSWORD" ]; then
    echo "$FIRSTUSER:$SSH_PASSWORD" | chpasswd
    if [ "$FIRSTUSER" != "$SSH_USERNAME" ]; then
      usermod -l "$SSH_USERNAME" "$FIRSTUSER"
      usermod -m -d "/home/$SSH_USERNAME" "$SSH_USERNAME"
      groupmod -n "$SSH_USERNAME" "$FIRSTUSER"
      # Update sudoers if the default pi-nopasswd file exists
      if [ -f /etc/sudoers.d/010_pi-nopasswd ]; then
          sed -i "s/^$FIRSTUSER /${SSH_USERNAME} /" /etc/sudoers.d/010_pi-nopasswd
      fi
    fi
    log "User '$USER_TO_CONFIGURE' and password configured."
else
    log "WARNING: SSH_USERNAME or SSH_PASSWORD not set. Using default user."
fi
systemctl enable ssh
log "SSH has been enabled."

# --- Locale and Keyboard Setup ---
log "Configuring timezone and keyboard layout..."
# Set timezone (e.g., "Europe/London")
rm -f /etc/localtime
echo "${TIMEZONE:-Etc/UTC}" > /etc/timezone
dpkg-reconfigure -f noninteractive tzdata
log "Timezone set to $(cat /etc/timezone)."

# Set keyboard layout from config
if [ -n "$KEYBOARD_LAYOUT" ]; then
    log "Setting keyboard layout to '$KEYBOARD_LAYOUT'..."
    cat > /etc/default/keyboard <<KBEOF
XKBMODEL="pc105"
XKBLAYOUT="$KEYBOARD_LAYOUT"
XKBVARIANT=""
XKBOPTIONS=""
KBEOF
    dpkg-reconfigure -f noninteractive keyboard-configuration
    log "Keyboard layout set."
else
    log "WARNING: KEYBOARD_LAYOUT not set in config. Skipping keyboard setup."
fi
log "--- Critical system configuration finished ---"

# ==============================================================================
# SECTION 2: SYSTEMD SERVICE SETUP
# These services depend on the system configuration above.
# ==============================================================================

log "--- Starting systemd service setup ---"

# --- Wi-Fi Connection Service Setup ---
WIFI_SCRIPT_PATH="/boot/firmware/wifi_connector.sh"
WIFI_SERVICE_FILE_PATH="/etc/systemd/system/wifi-connector.service"
if [ -f "$WIFI_SCRIPT_PATH" ]; then
    chmod +x "$WIFI_SCRIPT_PATH"
    cat > "$WIFI_SERVICE_FILE_PATH" << WIFICONNECTOREOF
[Unit]
Description=Custom Wi-Fi Connection Script
Wants=network.target
After=network.target

[Service]
Type=oneshot
ExecStart=/bin/bash $WIFI_SCRIPT_PATH
RemainAfterExit=true

[Install]
WantedBy=multi-user.target
WIFICONNECTOREOF
    systemctl enable wifi-connector.service
    log "Wi-Fi connector service created and enabled."
else
    log "WARNING: wifi_connector.sh not found. Skipping Wi-Fi service creation."
fi

# --- Application Launcher Service Setup ---
LAUNCHER_SCRIPT_PATH="/boot/firmware/launcher.sh"
LAUNCHER_SERVICE_FILE_PATH="/etc/systemd/system/launcher.service"
if [ -f "$LAUNCHER_SCRIPT_PATH" ]; then
    chmod +x "$LAUNCHER_SCRIPT_PATH"
    cat > "$LAUNCHER_SERVICE_FILE_PATH" << LAUNCHERSERVICEOF
[Unit]
Description=Application Launcher Service
Wants=network-online.target
After=network-online.target wifi-connector.service

[Service]
Type=simple
User=$USER_TO_CONFIGURE
Group=$USER_TO_CONFIGURE
ExecStart=$LAUNCHER_SCRIPT_PATH
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
LAUNCHERSERVICEOF
    systemctl daemon-reload
    systemctl enable launcher.service
    log "Application launcher service created and enabled."
else
    log "WARNING: launcher.sh not found. Skipping launcher service creation."
fi
log "--- Systemd service setup finished ---"

# ==============================================================================
# SECTION 3: FINAL CLEANUP
# ==============================================================================

log "--- Running final cleanup ---"
# Rename this script to prevent it from running again
if [ -f /boot/firmware/firstrun.sh ]; then
    mv /boot/firmware/firstrun.sh /boot/firmware/firstrun.sh.done
    log "Disabled firstrun.sh by renaming it."
fi
# Clean the command line file used to trigger this script
if [ -f /boot/firmware/cmdline.txt ]; then
    sed -i 's| systemd.run=[^ ]*||g' /boot/firmware/cmdline.txt
    log "Cleaned boot command line in cmdline.txt."
fi

log "--- First run setup is complete. Rebooting now... ---"
# Sync filesystems to ensure all changes are written to disk
sync
# Reboot to apply all changes
reboot
