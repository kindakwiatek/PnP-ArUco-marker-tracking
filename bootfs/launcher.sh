#!/bin/bash
# ==============================================================================
#
# launcher.sh (Revised)
#
# Description:
# This script runs at boot after the network is online. It manages the
# lifecycle of the motion capture application by:
#   1. Reading settings from a central config file.
#   2. Cloning or pulling the latest version from a Git repository.
#   3. Installing Python dependencies.
#   4. Launching the main server application.
#   5. Self-updating from the repository.
#
# ==============================================================================

set -e # Exit immediately if a command exits with a non-zero status.

# --- Configuration & Logging ---
readonly USER_SETTINGS_FILE="/boot/firmware/user_settings.conf"
readonly LOG_FILE="/boot/firmware/launcher.log"
readonly LAUNCHER_SCRIPT_NAME="launcher.sh" # The name of this script

# --- Logging Function ---
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# --- Main Functions ---

wait_for_network() {
    log "Waiting for full network connectivity..."
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
        git clone "$REPO_URL" "$REPO_DIR"
    else
        log "Repository exists. Pulling latest changes..."
        cd "$REPO_DIR"
        git fetch origin
        # Reset to the main branch to avoid conflicts
        git reset --hard origin/main # Use 'main' or 'master' as appropriate
        git pull
    fi
    # Ensure correct ownership of files
    chown -R user:user "$(dirname "$REPO_DIR")"
    cd "$REPO_DIR"
    log "Repository is up-to-date."
}

install_dependencies() {
    log "Installing/updating Python dependencies..."
    if [ -f "$REPO_DIR/requirements.txt" ]; then
        # Run pip as the 'user' to avoid permission issues
        sudo -u user python3 -m pip install --upgrade pip
        sudo -u user python3 -m pip install -r "$REPO_DIR/requirements.txt"
        log "Dependencies installed from requirements.txt."
    else
        log "WARNING: requirements.txt not found. Skipping dependency installation."
    fi
}

update_launcher_script() {
    log "Checking for launcher script updates..."
    local new_launcher_path="$REPO_DIR/$LAUNCHER_SCRIPT_NAME"
    local current_script_path="/boot/firmware/$LAUNCHER_SCRIPT_NAME"

    if [ -f "$new_launcher_path" ]; then
        if ! cmp -s "$new_launcher_path" "$current_script_path"; then
            log "New launcher version found. Updating..."
            # Overwrite the script on the boot partition
            cp "$new_launcher_path" "$current_script_path"
            chmod +x "$current_script_path"
            log "Launcher script updated. Reboot for changes to take effect."
        else
            log "Launcher script is already up-to-date."
        fi
    fi
}

launch_server() {
    local server_script_path="$REPO_DIR/server.py"
    if [ -f "$server_script_path" ]; then
        log "Launching server application: $server_script_path"
        # Run the server as the 'user'
        cd "$REPO_DIR"
        sudo -u user /usr/bin/python3 "$server_script_path"
    else
        log "ERROR: Server script not found at $server_script_path."
        exit 1
    fi
}

# --- Script Execution ---
main() {
    # Load settings first
    if [ -f "$USER_SETTINGS_FILE" ]; then
        source "$USER_SETTINGS_FILE"
    else
        log "FATAL: Configuration file $USER_SETTINGS_FILE not found."
        exit 1
    fi
    
    # Verify essential variables are set
    if [ -z "$REPO_URL" ] || [ -z "$REPO_DIR" ]; then
        log "FATAL: REPO_URL or REPO_DIR is not set in user_settings.conf."
        exit 1
    fi

    wait_for_network
    update_repository
    install_dependencies
    update_launcher_script # Self-update after pulling new code
    launch_server
}

# Run the main function, redirecting all output to the log
main &>> "$LOG_FILE"