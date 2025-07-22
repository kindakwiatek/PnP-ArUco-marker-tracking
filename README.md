# PnP ArUco Marker-Based Motion Capture System

This project implements a multi-camera motion capture system using Raspberry Pis, ArUco markers, and Perspective-n-Point (PnP) for camera pose estimation. It is designed to track the 3D position of objects in real-time.

## Table of Contents

* [Overview](#overview)
* [How It Works](#how-it-works)
* [Hardware Requirements](#hardware-requirements)
* [Software & Dependencies](#software--dependencies)
* [Repository Structure](#repository-structure)
* [Setup Instructions](#setup-instructions)
  * [Step 1: Client Machine Setup](#step-1-client-machine-setup)
  * [Step 2: Initial Pi Setup (SD Card)](#step-2-initial-pi-setup-sd-card)
  * [Step 3: Physical Marker Setup](#step-3-physical-marker-setup)
  * [Step 4: Headless Distortion Calibration](#step-4-headless-distortion-calibration)
  * [Step 5: System Deployment](#step-5-system-deployment)
* [Usage](#usage)
* [Configuration Files](#configuration-files)


## Overview

The system uses multiple Raspberry Pi cameras to detect ArUco markers in their fields of view. A central Jupyter Notebook on a client computer receives 2D marker coordinates from each Pi, performs camera pose estimation, triangulates the points, and calculates the markers' real-time 3D positions in a world coordinate system.

The initial camera positions are unknown. To solve this, the system uses a PnP calibration routine where a set of static, known-location markers are used to determine the precise position and orientation (pose) of each camera relative to a shared world origin.

## How It Works

1.  **Headless Setup:** A `firstrun.sh` script automatically configures each Raspberry Pi on its first boot, setting the hostname, connecting to Wi-Fi, and installing all necessary software from a Git repository.
2.  **Distortion Calibration:** Each camera's lens distortion is corrected. This is done remotely from the client machine using a headless script that analyzes images of a chessboard pattern.
3.  **Server Deployment:** A `server.py` script runs automatically on each Raspberry Pi. It captures the camera feed, detects ArUco markers, and streams their 2D image coordinates over the network.
4.  **Client Control:** The `motion_capture.ipynb` Jupyter Notebook acts as the central control panel. It connects to all Pi servers to receive data and manage the system.
5.  **PnP Pose Estimation:** The notebook uses a predefined set of ArUco markers with known 3D world coordinates to calculate each camera's pose (rotation and translation vectors) in real-time.
6.  **3D Triangulation & Visualization:** Once at least two cameras have determined their poses, the notebook triangulates the 3D position of any other tracked markers and displays the cameras and markers in a live 3D plot.

## Hardware Requirements

-   **Client Machine:** 1 x Computer (Linux, macOS, or Windows) to run the Jupyter Notebook.
-   **Servers:** 2 or more Raspberry Pi units (Pi 3B+ or newer recommended).
-   **Cameras:** 1 x Raspberry Pi compatible camera for each Pi.
-   **Storage:** 1 x MicroSD card for each Pi.
-   **Network:** A Wi-Fi network that all devices can connect to.
-   **Calibration Patterns:**
    -   A printed chessboard pattern for distortion calibration.
    -   A set of printed ArUco markers (from a 5x5 dictionary) for PnP and tracking.

## Software & Dependencies

-   **Operating System:** Raspberry Pi OS Lite (64-bit recommended) for the Pis.
-   **Python:** Python 3.
-   **Jupyter:** A working Jupyter Notebook or JupyterLab environment on the client machine.
-   **Dependencies:** See `requirements.txt`. Install on the client machine using:
    ```bash
    pip install -r requirements.txt
    ```
    The Raspberry Pi servers will install their dependencies automatically.

## Repository Structure

```
.
├── server/
│   ├── bootfs/
│   │   ├── firstrun.sh                 # Initial Pi setup script
│   │   ├── launcher.sh                 # Starts the server on boot
│   │   ├── template_pi_settings.conf   # Template for all settings
│   │   └── wifi_connect.sh             # Wi-Fi connection script
│   ├── distortion_calibration.py
│   └── server.py
├── motion_capture.ipynb                # Main client control notebook
├── config.py
├── requirements.txt
└── README.md
```

## Setup Instructions

### Step 1: Client Machine Setup

1.  **Clone Repository:** Clone this repository to your central computer.
2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Create Settings File:**
    -   Navigate to the `server/bootfs/` directory.
    -   Rename `template_pi_settings.conf` to `pi_settings.conf`.
    -   Edit `pi_settings.conf` and fill in your `WIFI_SSID`, Wi-Fi credentials, and the `SSH_USERNAME` and `SSH_PASSWORD` you will use for the Pis. The `firstrun.sh` script will automatically create a user with these credentials.

### Step 2: Initial Pi Setup (SD Card)

This project uses a fully headless setup. Repeat these steps for each Raspberry Pi.

1.  **Flash SD Card:** Flash Raspberry Pi OS Lite onto a microSD card using the **Raspberry Pi Imager**. **Do not configure any settings in the Imager's advanced options.** The `firstrun.sh` script will handle all setup tasks.
2.  **Copy Boot Files:** After flashing, mount the microSD card. It will contain a partition named `bootfs`. Copy all files from the `server/bootfs` folder in this repository directly into the root of that `bootfs` partition.
3.  **Configure Unique Hostname:**
    -   On the `bootfs` partition of the SD card, edit the `pi_settings.conf` file you just copied.
    -   Change the `NEW_HOSTNAME` value to be unique for this Pi (e.g., `pi-mocap-1`, `pi-mocap-2`).
    -   **Each Pi must have a unique hostname.**

### Step 3: Physical Marker Setup

1.  **Print Markers:** Print the ArUco markers you intend to use from the `DICT_5X5_50` dictionary.
2.  **Define World Coordinates:** Choose at least 4 markers to be your static PnP calibration markers.
3.  **Measure and Record:** Place these markers in your capture volume and precisely measure their `(X, Y, Z)` coordinates in centimeters. Update the `PNP_MARKER_WORLD_COORDINATES` dictionary in `config.py` with these measured values. This defines your world origin.

### Step 4: Headless Distortion Calibration

For each camera, you must perform a one-time distortion calibration. This is done remotely from the `motion_capture.ipynb` notebook.

1.  **Power On a Pi:** Insert the prepared SD card into a single Pi and power it on. Wait a few minutes for it to connect to the network.
2.  **Launch the Notebook:** On your client machine, start Jupyter and open `motion_capture.ipynb`.
3.  **Run Calibration Cells:** Follow the instructions in **Section 3** of the notebook to remotely command the Pi to capture images of the chessboard and run the calibration.
4.  **Download Data:** The notebook will automatically download the resulting `distortion_calibration.json` file to your project root. This file is used for all identical camera models.
5.  Repeat the process if you have different models of cameras.

### Step 5: System Deployment

1.  **Insert SD Cards:** Insert the configured SD cards into each Pi and power them on.
2.  **First Boot:** On the first boot, `firstrun.sh` will:
    -   Set the unique hostname.
    -   Configure and connect to your Wi-Fi network.
    -   Set up the SSH user and password from `pi_settings.conf`.
    -   Set up the `launcher.service` to automatically start the application on boot.
    -   Reboot.
3.  **Automatic Start:** On all subsequent boots, the `launcher.sh` script will run automatically. It will:
    -   Pull the latest code from the GitHub repository specified in `pi_settings.conf`.
    -   Install/update Python dependencies.
    -   Launch the `server.py` application.

## Usage

All system control is handled through the `motion_capture.ipynb` Jupyter Notebook.

1.  **Start Servers:** Power on all your configured Raspberry Pi servers.
2.  **Run the Notebook:** On your client computer, open and run the cells in `motion_capture.ipynb`.
3.  **Control the System:**
    -   **Section 2:** Remotely reboot or shut down all servers.
    -   **Section 3:** Perform headless distortion calibration for a new camera.
    -   **Section 4:** Launch the live 3D visualization to begin tracking.

## Configuration Files

-   **`config.py`:** Contains shared project parameters like network ports, ArUco marker settings, and the list of server hostnames.
-   **`server/bootfs/pi_settings.conf`:** The master settings file. Contains Pi-specific settings (hostname, Wi-Fi) and global settings (SSH credentials, repository URL). A copy of this file on each Pi's `bootfs` partition controls its behavior.
