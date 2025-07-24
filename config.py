# config.py
#
# Stores shared configuration settings for the motion capture project.
# This includes network, camera, ArUco marker, and calibration parameters.

import cv2
import os

# --- Asset and Data Paths ---
# The main directory for all generated assets
ASSETS_DIR = "assets"

# --- Network Settings ---
# A list of server hostnames or IP addresses to connect to
# The .local domain is handled by mDNS (Avahi/Bonjour)
SERVER_HOSTS = ['pi-mocap-1.local', 'pi-mocap-2.local', 'pi-mocap-3.local', 'pi-mocap-4.local']
# The network port for communication between the client and servers
NETWORK_PORT = 65432

# --- Camera and Frame Settings ---
FRAME_WIDTH = 1280  # Frame width in pixels for capture
FRAME_HEIGHT = 720  # Frame height in pixels for capture

# --- ArUco Marker Settings ---
# The specific ArUco dictionary to use for marker detection
ARUCO_DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_5X5_50)
# The total number of unique markers in the dictionary being used
NUM_MARKERS = 50
# The size in pixels for the generated marker images (excluding the border)
MARKER_SIZE_PX = 140
# The width of the white border as a percentage of the marker size
MARKER_BORDER_PERCENT = 20
# The folder where generated marker images will be saved
MARKER_FOLDER = os.path.join(ASSETS_DIR, "markers")

# --- PnP Runtime Calibration Settings ---
# This dictionary defines the real-world 3D coordinates for each PnP marker
# It establishes the origin and orientation of the world coordinate system
# Format: {marker_id: [X, Y, Z]} with units in centimeters
#
# IMPORTANT: You must change these values to the measured positions of
# your physical markers. At least 4 markers are required for PnP to function.
PNP_MARKER_WORLD_COORDINATES = {
    0: [0.0, 0.0, 0.0],      # Marker 0 at the origin
    1: [100.0, 0.0, 0.0],    # Marker 1 is 100cm along the X-axis
    2: [0.0, 50.0, 0.0],     # Marker 2 is 50cm along the Y-axis
    3: [100.0, 50.0, 0.0]    # Marker 3 completes the rectangle
}
# Directory to save images captured during the PnP process for debugging
PNP_IMAGES_FOLDER = os.path.join(ASSETS_DIR, "pnp_calibration_images")
# File to save the final calculated camera pose (position and orientation)
# This will be specific to each Pi, e.g., pnp_camera_pose_pi-mocap-1.local.json
PNP_DATA_FILE_PREFIX = "pnp_camera_pose"

# --- Initial Distortion Calibration Settings ---
# The dimensions of the physical chessboard pattern (number of inner corners)
CHESSBOARD_DIMENSIONS = (9, 6)
# The dimensions for the generated chessboard image (number of squares)
CHESSBOARD_SQUARES = (10, 7)
# The size of each square in the generated chessboard image, in pixels
CHESSBOARD_SQUARE_SIZE_PX = 80
# The filename for the generated chessboard image
CHESSBOARD_FILENAME = os.path.join(ASSETS_DIR, "chessboard.png")
# The directory where chessboard calibration images are stored
DISTORTION_IMAGES_FOLDER = os.path.join(ASSETS_DIR, "distortion_calibration_images")
# The file where the camera's intrinsic matrix and distortion coefficients are stored
DISTORTION_DATA_FILE = "distortion_calibration.json"
