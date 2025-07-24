# PnP ArUco Marker-Based Motion Capture System

This project implements a multi-camera motion capture system using Raspberry Pis, ArUco markers, and Perspective-n-Point (PnP) for camera pose estimation. It is designed to track the 3D position of markers in real-time.

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Hardware Requirements](#hardware-requirements)
- [Software and Dependencies](#software-and-dependencies)
- [Repository Structure](#repository-structure)
- [Setup Instructions](#setup-instructions)
  - [Step 1: Client Machine Setup](#step-1-client-machine-setup)
  - [Step 2: Initial Pi Setup (microSD Card)](#step-2-initial-pi-setup-microsd-card)
  - [Step 3: Physical Marker Setup](#step-3-physical-marker-setup)
  - [Step 4: Headless Distortion Calibration](#step-4-headless-distortion-calibration)
- [Usage](#usage)
- [Configuration Files](#configuration-files)

## Overview

The system uses multiple Raspberry Pi cameras to detect ArUco markers in their fields of view. A central Jupyter Notebook on a client computer receives 2D marker coordinates from each Pi, performs camera pose estimation, triangulates the points, and calculates the markers' real-time 3D positions in a global coordinate system.

The initial camera positions are unknown. To solve this, the system uses a PnP calibration routine where a set of static, known-location markers are used to determine the precise position and orientation (pose) of each camera relative to a shared world origin.

## How It Works

1.  **Headless Setup:** A `firstrun.sh` script automatically configures each Raspberry Pi on its first boot, setting the hostname, connecting to Wi-Fi, and installing all necessary software from a Git repository.
2.  **Distortion Calibration:** Each camera's lens distortion is corrected. This is done remotely from the client machine using a headless script that analyzes images of a chessboard pattern.
3.  **Server Deployment:** A `server.py` script runs automatically on each Raspberry Pi. It captures the camera feed, detects ArUco markers, and streams their 2D image coordinates over the network.
4.  **Client Control:** The `mocap.ipynb` Jupyter Notebook acts as the central control panel. It connects to all Pi servers to receive data and manage the system.
5.  **PnP Pose Estimation:** The notebook uses a predefined set of ArUco markers with known 3D world coordinates to calculate each camera's pose (rotation and translation vectors) in real-time.
6.  **3D Triangulation and Visualization:** Once at least two cameras have determined their poses, the notebook triangulates the 3D position of any other tracked markers and displays the cameras and markers in a live 3D plot.

## Hardware Requirements

-   **Client Machine:** 1 x Computer (Linux, macOS, or Windows) to run the Jupyter Notebook.
-   **Servers:** 2 or more Raspberry Pi units (Pi 3B+ or newer recommended).
-   **Cameras:** 1 x Raspberry Pi compatible camera for each Pi.
-   **Storage:** 1 x microSD card for each Pi.
-   **Network:** Wi-Fi network that all devices can connect to.
-   **Calibration Patterns:**
    -   A printed chessboard pattern for distortion calibration.
    -   A set of printed ArUco markers for PnP and tracking.

## Software and Dependencies

-   **Operating System:** Raspberry Pi OS Lite (64-bit recommended) for the Pis.
-   **Python:** Python 3.
-   **Jupyter:** A working Jupyter Notebook or JupyterLab environment on the client machine.
-   **Dependencies:** See `requirements.txt`. Install on the client machine using:
    ```bash
    pip install -r requirements.txt
    ```
    The Raspberry Pi servers will install their dependencies automatically.

## Repository Structure

````

.
├── assets/                     \# For client-generated images (markers, chessboard, etc.)
├── server/
│   ├── bootfs/                 \# Scripts for initial Pi configuration
│   │   ├── firstrun.sh
│   │   ├── launcher.sh
│   │   ├── template\_pi\_settings.conf
│   │   └── wifi\_connector.sh
│   ├── distortion\_calibration.py \# Headless script for camera calibration
│   └── server.py               \# Main server application running on each Pi
├── mocap.ipynb                 \# Central client control notebook
├── config.py                   \# Shared system configuration
├── requirements.txt
└── README.md

````

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

### Step 2: Initial Pi Setup (microSD Card)

This project uses a fully headless setup. Repeat these steps for each Raspberry Pi.

1.  **Flash microSD Card:** Flash Raspberry Pi OS Lite onto a microSD card using the **Raspberry Pi Imager**. You must enable SSH and pre-configure a user in the imager settings.
2.  **Copy Boot Files:** After flashing, mount the microSD card. It will contain a partition named `bootfs`. Copy all files from the `server/bootfs` folder in this repository directly into the root of the `bootfs` partition on the microSD card, replacing existing files.
3.  **Configure Unique Hostname:**
    -   On the `bootfs` partition of the microSD card, edit the `pi_settings.conf` file you just copied.
    -   Change the `NEW_HOSTNAME` value to be unique for this Pi (e.g., `pi-mocap-1`). Each Pi must have a unique hostname.

### Step 3: Physical Marker Setup

1.  **Generate and Print Markers:** Use **Part 1** of the `mocap.ipynb` notebook to generate the ArUco markers and the chessboard pattern, then print them. The generated files will be saved in the `assets` directory.
2.  **Define World Coordinates:** Choose at least 4 markers to be your static PnP calibration markers. Place these markers in your capture volume and precisely measure their `(X, Y, Z)` coordinates in centimeters.
3.  **Update Config:** Update the `PNP_MARKER_WORLD_COORDINATES` dictionary in `config.py` with these measured values. This defines your world origin.

### Step 4: Headless Distortion Calibration

For each camera, you must perform a one-time distortion calibration. This is done remotely from the `mocap.ipynb` notebook.

1.  **Power On a Pi:** Insert the prepared microSD card into a single Pi and power it on. Wait for it to connect to the network.
2.  **Launch the Notebook:** On your client machine, start Jupyter and open `mocap.ipynb`.
3.  **Run Calibration:** Follow the instructions in **Part 3** of the notebook (`Headless Distortion Calibration`) to remotely command the Pi to capture images of the chessboard and run the calibration.
4.  **Download Data:** The notebook will automatically download the resulting `distortion_calibration.json` file to your project root. This file can be used for all identical camera models.

## Usage

All system control is handled through the `mocap.ipynb` Jupyter Notebook.

1.  **Start Servers:** Power on all your configured Raspberry Pi servers.
2.  **Run the Notebook:** On your client computer, open and run the cells in `mocap.ipynb`.
3.  **Control the System:**
    -   **Part 1:** Generate assets (markers, chessboard) for printing.
    -   **Part 2:** Perform local tests of marker detection and distortion correction.
    -   **Part 3:** Manage remote servers (reboot, calibrate).
    -   **Part 4:** Launch the live 3D visualization to begin tracking.

## Configuration Files

-   **`config.py`:** Contains shared project parameters like network ports, ArUco marker settings, and the list of server hostnames.
-   **`server/bootfs/pi_settings.conf`:** The master settings file. Contains Pi-specific settings (hostname, Wi-Fi) and global settings (SSH credentials, repository URL).