#!/bin/bash
# ==============================================================================
# firstrun.sh - One-Time System Setup
# ==============================================================================
#
# Description:
# This script runs ONLY ONCE on the first boot.
# 1. It sets the hostname from pi_settings.conf.
# 2. It sets up a permanent systemd service for the main launcher.
# 3. It cleans itself up to prevent re-running.
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

# --- Hostname and User Setup ---
TARGET_HOSTNAME="rpi-1" # Default fallback
if [ ! -z "$NEW_HOSTNAME" ]; then
    TARGET_HOSTNAME="$NEW_HOSTNAME"
fi

echo "Setting hostname to $TARGET_HOSTNAME..."
CURRENT_HOSTNAME=$(cat /etc/hostname | tr -d " \t\n\r")
if [ -f /usr/lib/raspberrypi-sys-mods/imager_custom ]; then
    /usr/lib/raspberrypi-sys-mods/imager_custom set_hostname "$TARGET_HOSTNAME"
else
    echo "$TARGET_HOSTNAME" > /etc/hostname
    sed -i "s/127.0.1.1.*$CURRENT_HOSTNAME/127.0.1.1\t$TARGET_HOSTNAME/g" /etc/hosts
fi
echo "Hostname setup complete."

# (User setup remains unchanged)
FIRSTUSER=$(getent passwd 1000 | cut -d: -f1)
if [ -f /usr/lib/raspberrypi-sys-mods/imager_custom ]; then
    /usr/lib/raspberrypi-sys-mods/imager_custom enable_ssh
else
    systemctl enable ssh
fi
if [ -f /usr/lib/userconf-pi/userconf ]; then
    /usr/lib/userconf-pi/userconf 'user' '$5$0.Nw85NyXw$iPnXhIXDwXT1z5ZST5oIERhhKVR/kZppfTEeTzaeahD'
else
    echo "$FIRSTUSER:"'$5$0.Nw85NyXw$iPnXhIXDwXT1z5ZST5oIERhhKVR/kZppfTEeTzaeahD' | chpasswd -e
    if [ "$FIRSTUSER" != "user" ]; then
      usermod -l "user" "$FIRSTUSER"
      usermod -m -d "/home/user" "user"
      groupmod -n "user" "$FIRSTUSER"
    fi
fi
echo "User and SSH setup complete."


# ==================== PERMANENT LAUNCHER SERVICE SETUP ====================
echo "--- Creating Permanent Launcher Service ---"

LAUNCHER_SCRIPT_PATH="/boot/firmware/launcher.sh"
LAUNCHER_SERVICE_FILE_PATH="/etc/systemd/system/launcher.service"

if [ ! -f "$LAUNCHER_SCRIPT_PATH" ]; then
    echo "INFO: launcher.sh not found at $LAUNCHER_SCRIPT_PATH. Skipping launcher service creation."
else
    # Make the launcher script executable
    chmod +x "$LAUNCHER_SCRIPT_PATH"

    # Create the systemd service file
    echo "Creating systemd service file at $LAUNCHER_SERVICE_FILE_PATH..."
    cat > "$LAUNCHER_SERVICE_FILE_PATH" << 'LAUNCHERSERVICEOF'
[Unit]
Description=Custom Application Launcher Service
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=user
Group=user
ExecStart=/boot/firmware/launcher.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
LAUNCHERSERVICEOF

    # Enable the new permanent service
    echo "Enabling permanent launcher service..."
    systemctl enable launcher.service
    echo "--- Permanent launcher service created and enabled. ---"
fi
# ================= END OF PERMANENT LAUNCHER SERVICE SETUP =================

# (Locale and Keyboard setup remains unchanged)
echo "Configuring locale and keyboard..."
if [ -f /usr/lib/raspberrypi-sys-mods/imager_custom ]; then
    /usr/lib/raspberrypi-sys-mods/imager_custom set_keymap 'gb'
    /usr/lib/raspberrypi-sys-mods/imager_custom set_timezone 'Europe/London'
else
    rm -f /etc/localtime
    echo "Europe/London" >/etc/timezone
    dpkg-reconfigure -f noninteractive tzdata
fi
echo "Locale and keyboard setup complete."

# (Final Cleanup remains unchanged)
echo "--- Running final cleanup ---"
if [ -f /boot/firmware/firstrun.sh ]; then
    rm -f /boot/firmware/firstrun.sh
    echo "Deleted /boot/firmware/firstrun.sh"
fi
if [ -f /boot/firmware/cmdline.txt ]; then
    sed -i 's| systemd.run.*||g' /boot/firmware/cmdline.txt
    echo "Cleaned /boot/firmware/cmdline.txt"
fi
echo "--- Cleanup finished ---"

echo "--- firstrun.sh finished at $(date) ---"
exit 0
