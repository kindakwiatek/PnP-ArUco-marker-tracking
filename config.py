import cv2

# This file stores the configuration settings for the project

# --- Network Settings ---
NETWORK_HOST = 'pi-mocap-1.local' # IMPORTANT: Change this to your Raspberry Pi's IP address or hostname (as defined in user_script)
NETWORK_PORT = 65432 # The port must match the server's port

# --- Camera and Frame Settings ---
FRAME_WIDTH = 1280 # [px]
FRAME_HEIGHT = 720 # [px]

# --- ArUco Marker Settings ---
# The specific ArUco dictionary to use for detection
ARUCO_DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_5X5_50)
# The total number of unique markers the system should look for
NUM_MARKERS = 50

# --- Calibration Settings ---
# The dimensions of your chessboard (number of squares, not internal corners)
CHESSBOARD_DIMENSIONS = (10, 7) # (squares_wide, squares_high)
# The folder where camera calibration images are stored
CALIBRATION_IMAGES_FOLDER = "calibration-images"
# The file where camera calibration results are stored
CALIBRATION_DATA_FILE = "calibration_data.json"