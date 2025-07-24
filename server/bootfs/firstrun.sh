#!/bin/bash
# ==============================================================================
# firstrun.sh - One-Time System Setup
# ==============================================================================
#
# IMPORTANT: If you edit this file on Windows, you MUST save it with
# Unix-style line endings (LF), not Windows-style (CRLF). Use an editor
# like VS Code or Notepad++ to ensure this is correct, otherwise you will get
# syntax errors.
#
# Description:
# This script runs ONLY ONCE on the first boot
# 1. It sets the hostname specified in pi_settings.conf
# 2. It sets up a permanent systemd service for the main launcher
# 3. It cleans itself up to prevent re-running
#
# ==============================================================================

# Redirect all output to a log file on the boot partition
exec &> /boot/firmware/firstrun.log

echo "--- Starting firstrun.sh at $(date) ---"

# --- Configuration File ---
PI_SETTINGS_FILE="/boot/firmware/pi_settings.conf"
if [ -f "$PI_SETTINGS_FILE" ]; then
    source "$PI_SETTINGS_FILE"
    echo "Loaded settings from $PI_SETTINGS_FILE"
else
    echo "ERROR: Configuration file not found at $PI_SETTINGS_FILE. Exiting."
    exit 1
fi

# --- Wi-Fi Connection Service Setup ---
echo "--- Creating Permanent Wi-Fi Connector Service ---"
WIFI_SCRIPT_PATH="/boot/firmware/wifi_connect.sh"
WIFI_SERVICE_FILE_PATH="/etc/systemd/system/wifi-connector.service"

if [ ! -f "$WIFI_SCRIPT_PATH" ]; then
    echo "WARNING: wifi_connect.sh not found. Skipping Wi-Fi service creation."
else
    chmod +x "$WIFI_SCRIPT_PATH"
    cat > "$WIFI_SERVICE_FILE_PATH" << WIFICONNECTOREOF
[Unit]
Description=Custom Wi-Fi Connection Script
Wants=network.target
After=network.target

[Service]
Type=oneshot
ExecStart=/bin/bash /boot/firmware/wifi_connect.sh
RemainAfterExit=true

[Install]
WantedBy=multi-user.target
WIFICONNECTOREOF
    systemctl enable wifi-connector.service
    echo "--- Wi-Fi connector service created and enabled ---"
fi

# --- Hostname and User Setup ---
TARGET_HOSTNAME="rpi-1" # Default fallback
if [ ! -z "$NEW_HOSTNAME" ]; then
    TARGET_HOSTNAME="$NEW_HOSTNAME"
fi

echo "Setting hostname to $TARGET_HOSTNAME..."
CURRENT_HOSTNAME=$(cat /etc/hostname | tr -d " \t\n\r")
hostnamectl set-hostname "$TARGET_HOSTNAME"
sed -i "s/127.0.1.1.*$CURRENT_HOSTNAME/127.0.1.1\t$TARGET_HOSTNAME/g" /etc/hosts
echo "Hostname setup complete."

FIRSTUSER=$(getent passwd 1000 | cut -d: -f1)
systemctl enable ssh

if [ -n "$SSH_USERNAME" ] && [ -n "$SSH_PASSWORD" ]; then
    echo "$FIRSTUSER:$SSH_PASSWORD" | chpasswd
    if [ "$FIRSTUSER" != "$SSH_USERNAME" ]; then
      usermod -l "$SSH_USERNAME" "$FIRSTUSER"
      usermod -m -d "/home/$SSH_USERNAME" "$SSH_USERNAME"
      groupmod -n "$SSH_USERNAME" "$FIRSTUSER"
      if [ -f /etc/sudoers.d/010_pi-nopasswd ]; then
          sed -i "s/^$FIRSTUSER /${SSH_USERNAME} /" /etc/sudoers.d/010_pi-nopasswd
      fi
    fi
    USER_TO_CONFIGURE="$SSH_USERNAME"
else
    echo "$FIRSTUSER:"'$5$0.Nw85NyXw$iPnXhIXDwXT1z5ZST5oIERhhKVR/kZppfTEeTzaeahD' | chpasswd -e
    if [ "$FIRSTUSER" != "user" ]; then
      usermod -l "user" "$FIRSTUSER"
      usermod -m -d "/home/user" "user"
      groupmod -n "user" "$FIRSTUSER"
    fi
    USER_TO_CONFIGURE="user"
fi
echo "User and SSH setup complete."

# ==================== PERMANENT LAUNCHER SERVICE SETUP ====================
echo "--- Creating Permanent Launcher Service ---"

LAUNCHER_SCRIPT_PATH="/boot/firmware/launcher.sh"
LAUNCHER_SERVICE_FILE_PATH="/etc/systemd/system/launcher.service"

if [ ! -f "$LAUNCHER_SCRIPT_PATH" ]; then
    echo "INFO: launcher.sh not found at $LAUNCHER_SCRIPT_PATH. Skipping launcher service creation."
else
    chmod +x "$LAUNCHER_SCRIPT_PATH"
    cat > "$LAUNCHER_SERVICE_FILE_PATH" << LAUNCHERSERVICEOF
[Unit]
Description=Custom Application Launcher Service
Wants=network-online.target
After=network-online.target wifi-connector.service

[Service]
Type=simple
User=$USER_TO_CONFIGURE
Group=$USER_TO_CONFIGURE
ExecStart=/boot/firmware/launcher.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
LAUNCHERSERVICEOF
    systemctl daemon-reload
    systemctl enable launcher.service
    echo "--- Permanent launcher service created and enabled. ---"
fi
# ================= END OF PERMANENT LAUNCHER SERVICE SETUP =================

# --- Locale and Keyboard Setup ---
echo "Configuring locale and keyboard..."
rm -f /etc/localtime
echo "Europe/London" >/etc/timezone
dpkg-reconfigure -f noninteractive tzdata
echo "Locale and keyboard setup complete."

# --- Final Cleanup ---
echo "--- Running final cleanup ---"
if [ -f /boot/firmware/firstrun.sh ]; then
    mv /boot/firmware/firstrun.sh /boot/firmware/firstrun.sh.done
    echo "Disabled firstrun.sh by renaming it."
fi
if [ -f /boot/firmware/cmdline.txt ]; then
    sed -i 's| systemd.run=[^ ]*||g' /boot/firmware/cmdline.txt
    echo "Cleaned /boot/firmware/cmdline.txt"
fi
echo "--- Cleanup finished ---"

echo "--- firstrun.sh finished at $(date). Rebooting... ---"
sync
reboot
