# config.py
#
# Stores shared configuration settings for the motion capture project
# This includes network, camera, ArUco marker, and calibration parameters

import cv2

# --- Network Settings ---
# A list of server hostnames or IP addresses to connect to
# The .local domain is handled by mDNS (Avahi/Bonjour)
SERVER_HOSTS = ['pi_mocap_1.local', 'pi_mocap_2.local', 'pi_mocap_3.local', 'pi_mocap_4.local']
# The network port for communication between the client and servers
NETWORK_PORT = 65432

# --- Camera and Frame Settings ---
FRAME_WIDTH = 1280  # Frame width in pixels
FRAME_HEIGHT = 720  # Frame height in pixels

# --- ArUco Marker Settings ---
# The specific ArUco dictionary to use for marker detection
ARUCO_DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_5X5_50)
# The total number of unique markers the system is configured to track
NUM_MARKERS = 50

# --- PnP Runtime Calibration Settings ---
# The number of markers used to establish the world coordinate system
# These markers must have IDs from 0 to (NUM_PNP_MARKERS - 1)
NUM_PNP_MARKERS = 10
# The number of consecutive frames to analyze for a stable PnP calibration
NUM_PNP_FRAMES = 50
# Directory to save images captured during the PnP process for debugging
PNP_IMAGES_FOLDER = "pnp_calibration_images"
# File to save the final calculated camera pose (position and orientation)
# This will be specific to each Pi, e.g., pnp_camera_pose_pi-mocap-1.local.json
PNP_DATA_FILE_PREFIX = "pnp_camera_pose"

# IMPORTANT: Define the real-world 3D coordinates for each PnP marker
# This establishes the origin and orientation of your world coordinate system
# Format: {marker_id: [X, Y, Z]} with units in centimeters
#
# EXAMPLE: Markers 0, 1, 2, and 3 form a 100cm x 50cm rectangle on the
# floor (Z=0). You MUST change these values to the measured positions of
# your physical markers.
PNP_MARKER_WORLD_COORDINATES = {
    0: [0.0, 0.0, 0.0],      # Marker 0 at the origin
    1: [100.0, 0.0, 0.0],    # Marker 1 is 100cm along the X-axis
    2: [0.0, 50.0, 0.0],     # Marker 2 is 50cm along the Y-axis
    3: [100.0, 50.0, 0.0]    # Marker 3 completes the rectangle
}

# --- Initial Distortion Calibration Settings ---
# The dimensions of your chessboard pattern (number of squares, not internal corners)
CHESSBOARD_DIMENSIONS = (10, 7)  # (squares_wide, squares_high)
# The directory where chessboard calibration images are stored on the server
DISTORTION_IMAGES_FOLDER = "distortion_calibration_images"
# The file where the camera's intrinsic matrix and distortion coefficients are stored
DISTORTION_DATA_FILE = "distortion_calibration.json"
