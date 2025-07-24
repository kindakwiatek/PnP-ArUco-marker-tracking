#!/bin/bash
# ==============================================================================
# launcher.sh
#
# IMPORTANT: If you edit this file on Windows, you MUST save it with
# Unix-style line endings (LF), not Windows-style (CRLF). Use an editor
# like VS Code or Notepad++ to ensure this is correct, otherwise you will get
# syntax errors.
#
# Description:
# This script runs at boot after the network is online. It manages the
# lifecycle of the motion capture application by:
#   1. Reading settings from pi_settings.conf
#   2. Cloning or pulling the latest version from a Git repository
#   3. Installing Python dependencies
#   4. Launching the main server application
#   5. Self-updating from the repository
#
# ==============================================================================

set -e # Exit immediately if a command exits with a non-zero status

# --- Configuration & Logging ---
readonly PI_SETTINGS_FILE="/boot/firmware/pi_settings.conf"
readonly LOG_FILE="/boot/firmware/launcher.log"
readonly LAUNCHER_SCRIPT_NAME="launcher.sh" # The filename of this script

# --- Global variable for the application user ---
# This will be set in main() after sourcing the config
APP_USER=""

# --- Logging Function ---
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# --- Main Functions ---

wait_for_network() {
    log "Waiting for full network connectivity..."
    # Loop until we can successfully ping the GitHub domain
    while ! ping -c 1 -W 1 github.com &> /dev/null; do
        log "Network not ready, waiting..."
        sleep 2
    done
    log "Network connectivity established."
}

update_repository() {
    log "Updating application repository from $REPO_URL..."
    if [ ! -d "$REPO_DIR" ]; then
        log "Repository not found. Cloning into $REPO_DIR..."
        # Clone the repository as the root user
        git clone "$REPO_URL" "$REPO_DIR"
    else
        log "Repository exists. Pulling latest changes..."
        cd "$REPO_DIR"
        # Fetch and reset the repository to the latest version from the main branch
        git fetch origin
        git reset --hard origin/main
        git pull
    fi
    # IMPORTANT: Ensure the application user owns the entire repository directory
    log "Setting ownership of $REPO_DIR to user '$APP_USER'..."
    chown -R "$APP_USER:$APP_USER" "$REPO_DIR"
    cd "$REPO_DIR"
    log "Repository is up-to-date."
}

install_dependencies() {
    log "Installing/updating Python dependencies for user '$APP_USER'..."
    local requirements_file="$REPO_DIR/requirements.txt"
    if [ -f "$requirements_file" ]; then
        # Run pip as the application user to ensure packages are installed in their context
        sudo -u "$APP_USER" python3 -m pip install --upgrade pip
        sudo -u "$APP_USER" python3 -m pip install -r "$requirements_file"
        log "Dependencies installed from requirements.txt."
    else
        log "WARNING: requirements.txt not found. Skipping dependency installation."
    fi
}

update_launcher_script() {
    log "Checking for launcher script updates..."
    local new_launcher_path="$REPO_DIR/server/bootfs/$LAUNCHER_SCRIPT_NAME"
    local current_script_path="/boot/firmware/$LAUNCHER_SCRIPT_NAME"

    if [ -f "$new_launcher_path" ]; then
        # Compare the new script with the current one using checksums for reliability
        if ! cmp -s "$new_launcher_path" "$current_script_path"; then
            log "New launcher version found. Updating..."
            # Overwrite the script on the boot partition
            cp "$new_launcher_path" "$current_script_path"
            # Ensure it remains executable
            chmod +x "$current_script_path"
            log "Launcher script updated. A reboot is required for changes to take effect."
        else
            log "Launcher script is already up-to-date."
        fi
    else
        log "WARNING: New launcher script not found at '$new_launcher_path'."
    fi
}

launch_server() {
    local server_script_path="$REPO_DIR/server/server.py"
    if [ -f "$server_script_path" ]; then
        log "Launching server application as user '$APP_USER': $server_script_path"
        # Change to the repository directory before executing
        cd "$REPO_DIR"
        # Run the server as the application user
        sudo -u "$APP_USER" /usr/bin/python3 "$server_script_path"
    else
        log "ERROR: Server script not found at $server_script_path."
        exit 1
    fi
}

# --- Script Execution ---
main() {
    # Load settings first. This is the source of all configuration
    if [ -f "$PI_SETTINGS_FILE" ]; then
        # Source the file to load variables like REPO_URL, REPO_DIR, and SSH_USERNAME
        source "$PI_SETTINGS_FILE"
    else
        log "FATAL: Configuration file $PI_SETTINGS_FILE not found."
        exit 1
    fi

    # Set the application user from the config file, with a safe fallback
    APP_USER="${SSH_USERNAME:-user}"
    log "Application user set to: '$APP_USER'"

    # Verify essential variables are set
    if [ -z "$REPO_URL" ] || [ -z "$REPO_DIR" ] || [ -z "$SSH_USERNAME" ]; then
        log "FATAL: REPO_URL, REPO_DIR, or SSH_USERNAME is not set in $PI_SETTINGS_FILE."
        exit 1
    fi

    wait_for_network
    update_repository
    install_dependencies
    update_launcher_script # Self-update after pulling new code
    launch_server
}

# Run the main function, redirecting all output to the log file
# Using a subshell to ensure the log file captures everything, even if the script exits
(
    main
) &>> "$LOG_FILE"
