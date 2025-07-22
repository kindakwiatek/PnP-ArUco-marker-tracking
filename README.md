# PnP ArUco Marker-Based Motion Capture System

This project implements a multi-camera motion capture system using Raspberry Pis, ArUco markers, and Perspective-n-Point (PnP) for camera pose estimation. It is designed to track the 3D position of objects in real-time.

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Hardware Requirements](#hardware-requirements)
- [Software & Dependencies](#software--dependencies)
- [Repository Structure](#repository-structure)
- [Setup Instructions](#setup-instructions)
  - [Step 1: Client Machine Setup](#step-1-client-machine-setup)
  - [Step 2: Initial Pi Setup (SD Card)](#step-2-initial-pi-setup-sd-card)
  - [Step 3: Physical Marker Setup](#step-3-physical-marker-setup)
  - [Step 4: Camera Distortion Calibration](#step-4-camera-distortion-calibration)
  - [Step 5: System Deployment](#step-5-system-deployment)
- [Usage](#usage)
- [Remote Management](#remote-management)
- [Configuration Files](#configuration-files)


## Overview

The system uses multiple Raspberry Pi cameras to detect ArUco markers in their fields of view. A central client computer receives 2D marker coordinates from each Pi, triangulates these points, and calculates the markers' real-time 3D positions in a world coordinate system.

The initial camera positions are unknown. To solve this, the system uses a PnP calibration routine where a set of static, known-location markers are used to determine the precise position and orientation (pose) of each camera relative to a shared world origin.

## How It Works

1.  **Distortion Calibration:** Each camera is first calibrated to correct for lens distortion using a standard chessboard pattern. This generates an intrinsic camera matrix and distortion coefficients.
2.  **Server Deployment:** A `server.py` script runs on each Raspberry Pi. It captures the camera feed, detects ArUco markers, and streams their 2D image coordinates over the network.
3.  **Client Control:** A `client.py` script runs on a central computer. It connects to all Pi servers to receive their data streams.
4.  **PnP Pose Estimation (Future Implementation):** The client can command the servers to perform PnP calibration. The servers use a predefined set of ArUco markers with known 3D world coordinates to calculate their own camera pose (rotation and translation vectors). This pose data is saved locally on each Pi.
5.  **3D Triangulation:** Once at least two cameras have determined their poses and are streaming data, the client uses the 2D coordinates from multiple viewpoints to triangulate the 3D position of any tracked marker.

## Hardware Requirements

-   **Client Machine:** 1 x Computer (Linux, macOS, or Windows) to run the main client.
-   **Servers:** 2 or more Raspberry Pi units (Pi 3B+ or newer recommended).
-   **Cameras:** 1 x Raspberry Pi compatible camera for each Pi server.
-   **Storage:** 1 x MicroSD card for each Pi.
-   **Network:** A Wi-Fi network that all devices can connect to.
-   **Calibration Patterns:**
    -   A printed chessboard pattern for distortion calibration.
    -   A set of printed ArUco markers (from a 5x5 dictionary) for PnP and tracking.

## Software & Dependencies

-   **Operating System:** Raspberry Pi OS Lite (64-bit recommended) for the Pis.
-   **Python:** Python 3.
-   **Dependencies:** See `requirements.txt`. Versions are pinned for reproducibility. Install on both the client and the Pi servers using:
    ```bash
    pip install -r requirements.txt
    ```

## Repository Structure

```
.
├── bootfs/
│   ├── firstrun.sh
│   ├── launcher.sh
│   ├── template_pi_settings.conf   # Template for Pi-specific settings
│   └── wifi_connect.sh
├── client.py
├── config.py
├── distortion_calibration.py
├── remote_reset.py                 # Utility to remotely reboot/shutdown all Pis
├── server.py
├── template_client_settings.py     # Template for client-side settings
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
3.  **Configure Client Settings:**
    -   Rename `template_client_settings.py` to `client_settings.py`.
    -   Edit `client_settings.py` and enter the SSH username and password for your Raspberry Pi devices. This file is ignored by git.

### Step 2: Initial Pi Setup (SD Card)

This project supports a headless setup where the Raspberry Pi configures itself on the first boot. Repeat for each Pi.

1.  **Flash SD Card:** Flash Raspberry Pi OS Lite onto a microSD card using the Raspberry Pi Imager.
2.  **Enable SSH & First Run:** In the Imager settings, enable SSH, set the same user/password you entered in `client_settings.py`, and under "Advanced options", set "Run first-run script" to point to the `firstrun.sh` script from this repository.
3.  **Copy Files to Boot Partition:** After flashing, the SD card will have a `boot` or `firmware` partition. Copy the entire `bootfs` directory from this repository into that partition.
4.  **Configure Pi-Specific Settings:**
    -   Navigate into the copied `bootfs` directory on the SD card.
    -   Rename `template_pi_settings.conf` to `pi_settings.conf`.
    -   Edit `pi_settings.conf` to set your unique `NEW_HOSTNAME` for this specific Pi and your `WIFI_SSID` and credentials. **Each Pi must have a unique hostname.**

### Step 3: Physical Marker Setup

1.  **Print Markers:** Print the ArUco markers you intend to use from the `DICT_5X5_50` dictionary.
2.  **Define World Coordinates:** Choose at least 4 markers to be your static PnP calibration markers.
3.  **Measure and Record:** Place these markers in your capture volume and precisely measure their `(X, Y, Z)` coordinates in centimeters. Update the `PNP_MARKER_WORLD_COORDINATES` dictionary in `config.py` with these measured values. This defines your world origin.

### Step 4: Camera Distortion Calibration

For each Raspberry Pi camera, you must perform a one-time distortion calibration.

1.  **Connect a Display:** Temporarily connect a monitor and keyboard to the Pi.
2.  **Run the Script:** From a terminal on the Pi, navigate to the repository directory and run:
    ```bash
    python3 distortion_calibration.py
    ```
3.  **Capture Images:** Follow the on-screen instructions. Show the camera a chessboard pattern from many different angles and distances, pressing `SPACE` to capture images.
4.  **Calibrate:** Once you have at least 15 images, press `c` to perform the calibration. This will generate a `distortion_calibration.json` file.
5.  **Distribute Calibration File:** Copy this JSON file to every other Pi server and to the client machine, as it contains the intrinsic properties of the cameras you are using (assuming all cameras are the same model).

### Step 5: System Deployment

1.  **Insert SD Cards:** Insert the configured SD cards into each Pi and power them on.
2.  **First Boot:** On the first boot, the `firstrun.sh` script will:
    -   Set the hostname.
    -   Connect to Wi-Fi.
    -   Set up the `launcher.service` to automatically start the application on boot.
    -   Reboot.
3.  **Automatic Start:** On subsequent boots, the `launcher.sh` script will run automatically. It will:
    -   Pull the latest code from the GitHub repository.
    -   Install Python dependencies.
    -   Launch `server.py`.

## Usage

1.  **Start Servers:** Power on all Raspberry Pi servers.
2.  **Run Client:** On your central computer, navigate to the project directory and run:
    ```bash
    python3 client.py
    ```
3.  **Control the System:** Use the commands in the client terminal:
    -   `stream`: Tells all servers to start detecting markers and streaming their 2D coordinates.
    -   `stop`: Pauses the data stream from all servers.
    -   `pnp`: (Future Implementation) Initiates PnP calibration.
    -   `quit`: Disconnects from all servers and shuts down the client.

## Remote Management

You can remotely reboot or shut down all servers at once using the `remote_reset.py` script. It uses the credentials you provided in `client_settings.py`.

**Usage:**

From your client machine, run one of the following commands:

```bash
# To reboot all servers
python3 remote_reset.py reboot

# To shut down all servers
python3 remote_reset.py shutdown
```

## Configuration Files

-   **`config.py`:** Contains shared project parameters like network ports, marker settings, and the list of server hostnames.
-   **`bootfs/pi_settings.conf`:** Pi-specific settings for headless boot (hostname, Wi-Fi). Lives on each Pi's boot partition.
-   **`client_settings.py`:** Client-specific settings (SSH credentials). Lives on the client machine and is ignored by git.
