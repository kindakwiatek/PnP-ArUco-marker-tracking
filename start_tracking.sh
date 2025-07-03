#!/bin/bash

# This script pulls and launches 'tracking.py' from the GitHub repository

echo "Tracking launcher script is running."

# Define repository details
REPO_DIR="/home/pi/PnP-ArUco-marker-tracking"
PYTHON_SCRIPT_PATH="$REPO_DIR/tracking.py"

# Navigate to the home directory
cd /home/pi || exit

# Check if the repository directory exists
if [ -d "$REPO_DIR" ]; then
    echo "Repository exists. Pulling latest changes..."
    cd "$REPO_DIR" || exit
    # Stash any local changes before pulling
    git stash
    git pull
else
    echo "Repository not found. Cloning from GitHub..."
    git clone "https://github.com/kindakwiatek/PnP-ArUco-marker-tracking.git"
fi

# Check if the Python script exists
if [ -f "$PYTHON_SCRIPT_PATH" ]; then
    echo "Found tracking.py. Installing dependencies..."
    # Ensure dependencies are installed (add other packages if needed)
    # The -q flag makes pip run quietly.
    pip install -q opencv-python numpy

    echo "Launching tracking.py..."
    /usr/bin/python3 "$PYTHON_SCRIPT_PATH"
else
    echo "Error: tracking.py not found after clone/pull."
    exit 1
fi
