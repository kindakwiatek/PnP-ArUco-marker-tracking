# server/server.py
#
# This script runs on each Raspberry Pi. It initializes the camera, loads
# calibration data, detects ArUco markers in the video stream, and sends
# their 2D image coordinates to a central client over a network socket.

import cv2
import numpy as np
from picamera2 import Picamera2
import time
import socket
import json
import os
import sys
import logging

# Add the project root to the Python path to allow importing 'config'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

# --- Logging Setup ---
# A separate log file is created for each server instance
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'server_logs')
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, f'server_{socket.gethostname()}.log')),
        logging.StreamHandler()
    ]
)

def load_calibration_data(filepath):
    """
    Loads camera matrix and distortion coefficients from a JSON file.

    Args:
        filepath (str): The path to the calibration data file.

    Returns:
        A tuple containing the camera matrix (np.ndarray) and
        distortion coefficients (np.ndarray). Returns (None, None) on error.
    """
    full_path = os.path.join(os.path.dirname(__file__), '..', filepath)
    
    if not os.path.exists(full_path):
        logging.error(f"Calibration file not found at '{full_path}'")
        logging.error("Please run the calibration process from the client first.")
        return None, None

    try:
        with open(full_path, 'r') as f:
            data = json.load(f)
        camera_matrix = np.array(data['camera_matrix'], dtype=np.float32)
        dist_coeffs = np.array(data['distortion_coefficients'], dtype=np.float32)
        logging.info("Camera intrinsic calibration data loaded successfully.")
        return camera_matrix, dist_coeffs
    except (json.JSONDecodeError, KeyError) as e:
        logging.error(f"Failed to load or parse calibration file: {e}")
        return None, None


def initialize_camera():
    """Initializes and configures the Picamera2 instance for streaming."""
    picam2 = Picamera2()
    # Use a preview configuration for lower latency video streaming
    camera_cfg = picam2.create_preview_configuration(
        main={"size": (config.FRAME_WIDTH, config.FRAME_HEIGHT), "format": "BGR888"},
        controls={"FrameDurationLimits": (33333, 33333)}  # Sets target to ~30 FPS
    )
    picam2.configure(camera_cfg)
    return picam2


def stream_marker_data(conn, picam2, camera_matrix, dist_coeffs, detector):
    """
    Captures frames, detects markers, and sends data to the connected client.
    """
    if not picam2.started:
        picam2.start()
        time.sleep(1.0) # Allow sensor to adjust
        logging.info("Camera started for streaming.")

    # Pre-calculate the optimal new camera matrix for undistortion
    h, w = config.FRAME_HEIGHT, config.FRAME_WIDTH
    new_camera_mtx, roi = cv2.getOptimalNewCameraMatrix(camera_matrix, dist_coeffs, (w, h), 1, (w, h))

    while True:
        frame_raw = picam2.capture_array()
        
        # Apply lens distortion correction
        frame_undistorted = cv2.undistort(frame_raw, camera_matrix, dist_coeffs, None, new_camera_mtx)
        
        # Crop the image to the valid area to remove black borders
        x, y, w_roi, h_roi = roi
        frame = frame_undistorted[y:y + h_roi, x:x + w_roi]

        frame_positions = []
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = detector.detectMarkers(gray)

        if ids is not None:
            for i, marker_id in enumerate(ids.flatten()):
                # Ensure the detected marker ID is within the expected range
                if 0 <= marker_id < config.NUM_MARKERS:
                    marker_corners = corners[i].reshape((4, 2))
                    # Calculate the center of the marker
                    cx = int(np.mean(marker_corners[:, 0]))
                    cy = int(np.mean(marker_corners[:, 1]))
                    
                    position_data = {'id': int(marker_id), 'pos': [cx, cy]}
                    frame_positions.append(position_data)
        
        if frame_positions:
            try:
                # Serialize the list of detected markers to JSON and send
                data_to_send = json.dumps(frame_positions) + '\\n'
                conn.sendall(data_to_send.encode('utf-8'))
            except (BrokenPipeError, ConnectionResetError):
                logging.warning("Client disconnected during stream.")
                break # Exit loop on connection error

def handle_client_connection(conn, addr, picam2, camera_matrix, dist_coeffs, detector):
    """
    Manages a single client connection, listening for commands and handling data streaming.
    """
    logging.info(f"Accepted connection from {addr}")
    try:
        # For this application, we immediately start streaming data upon connection
        stream_marker_data(conn, picam2, camera_matrix, dist_coeffs, detector)
    except Exception as e:
        logging.error(f"An unexpected error occurred in client handler: {e}", exc_info=True)
    finally:
        if picam2.started:
            picam2.stop()
            logging.info("Camera stream stopped.")
        conn.close()
        logging.info(f"Connection with {addr} closed.")


def main():
    """Sets up the server and listens for incoming client connections."""
    logging.info("--- MoCap Server Initializing ---")
    
    camera_matrix, dist_coeffs = load_calibration_data(config.DISTORTION_DATA_FILE)
    if camera_matrix is None or dist_coeffs is None:
        logging.critical("Could not start server due to missing calibration data.")
        sys.exit(1)

    picam2 = initialize_camera()

    aruco_dict = config.ARUCO_DICT
    parameters = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)

    HOST = '0.0.0.0'  # Listen on all available network interfaces
    PORT = config.NETWORK_PORT

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        logging.info(f"Server is live. Waiting for connections on port {PORT}...")

        while True:
            try:
                conn, addr = s.accept()
                # Each client connection is handled sequentially
                handle_client_connection(conn, addr, picam2, camera_matrix, dist_coeffs, detector)
            except KeyboardInterrupt:
                logging.info("Shutdown signal received.")
                break
            except Exception as e:
                logging.error(f"Error in main accept loop: {e}", exc_info=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.critical(f"Server failed to start: {e}", exc_info=True)
    finally:
        logging.info("--- MoCap Server Shut Down ---")

