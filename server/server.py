# server/server.py
#
# This script runs on each Raspberry Pi. It initializes the camera, loads
# calibration data, detects ArUco markers, and streams their 2D coordinates
# to a central client over a network socket. It also listens for commands.

import cv2
import numpy as np
from picamera2 import Picamera2
import time
import socket
import json
import os
import sys
import logging

# Add project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

# --- Logging Setup ---
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
        filepath (str): The path to the calibration data file relative to project root.

    Returns:
        A tuple containing the camera matrix (np.ndarray) and
        distortion coefficients (np.ndarray). Returns (None, None) on error.
    """
    root_filepath = os.path.join(os.path.dirname(__file__), '..', filepath)
    
    if not os.path.exists(root_filepath):
        logging.error(f"Calibration file not found at '{root_filepath}'")
        logging.error("Please run the calibration process from the client first.")
        return None, None

    with open(root_filepath, 'r') as f:
        data = json.load(f)

    camera_matrix = np.array(data['camera_matrix'], dtype=np.float32)
    dist_coeffs = np.array(data['distortion_coefficients'], dtype=np.float32)

    logging.info("Camera intrinsic calibration data loaded.")
    return camera_matrix, dist_coeffs


def initialize_camera():
    """Initializes and configures the Picamera2 instance."""
    picam2 = Picamera2()
    camera_cfg = picam2.create_preview_configuration(
        main={"size": (config.FRAME_WIDTH, config.FRAME_HEIGHT), "format": "BGR888"},
        controls={"FrameDurationLimits": (33333, 33333)}  # Approx. 30 FPS
    )
    picam2.configure(camera_cfg)
    return picam2


def handle_client_connection(conn, addr, picam2, camera_matrix, dist_coeffs, detector):
    """
    Manages a single client connection, processing commands and streaming data.
    """
    logging.info(f"Connected by {addr}")
    is_streaming = False
    conn.settimeout(1.0) # Set a timeout for blocking operations

    try:
        f = conn.makefile('r')
        
        while True:
            try:
                # Check for commands without blocking forever
                command = f.readline().strip()
                if command:
                    logging.info(f"Received command: '{command}'")
                    if command == "start_stream":
                        is_streaming = True
                        if not picam2.started:
                            picam2.start()
                            time.sleep(1.0)
                            logging.info("Camera started for streaming.")
                    elif command == "stop_stream":
                        is_streaming = False
                        logging.info("Streaming paused by client command.")
                    elif command == "pnp":
                        logging.info("PnP command received but not yet implemented.")
                        conn.sendall(b"PnP not implemented\\n")
                elif not is_streaming:
                    # If not streaming and no command, wait a bit
                    time.sleep(0.1)

            except socket.timeout:
                # This is expected when no command is sent
                pass
            except (BrokenPipeError, ConnectionResetError):
                logging.warning(f"Client {addr} disconnected abruptly.")
                break # Exit main loop on connection error
            
            if not is_streaming:
                continue

            # --- Streaming Logic ---
            frame_raw = picam2.capture_array()
            frame = cv2.undistort(frame_raw, camera_matrix, dist_coeffs)

            frame_positions = []
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, _ = detector.detectMarkers(gray)

            if ids is not None:
                for i, marker_id in enumerate(ids.flatten()):
                    if 0 <= marker_id < config.NUM_MARKERS:
                        marker_corners = corners[i].reshape((4, 2))
                        cx = int(np.mean(marker_corners[:, 0]))
                        cy = int(np.mean(marker_corners[:, 1]))
                        
                        position_data = {'id': int(marker_id), 'pos': [cx, cy]}
                        frame_positions.append(position_data)
            
            if frame_positions:
                try:
                    data_to_send = json.dumps(frame_positions) + '\\n'
                    conn.sendall(data_to_send.encode('utf-8'))
                except (BrokenPipeError, ConnectionResetError):
                    logging.warning(f"Client {addr} disconnected during stream.")
                    break # Exit main loop

    except Exception as e:
        logging.error(f"An unexpected error occurred in handle_client_connection: {e}")
    finally:
        if picam2.started:
            picam2.stop()
            logging.info("Camera stream stopped.")
        conn.close()


def main():
    """Sets up the server and handles incoming connections."""
    logging.info("--- Starting MoCap Server ---")
    camera_matrix, dist_coeffs = load_calibration_data(config.DISTORTION_DATA_FILE)
    if camera_matrix is None:
        sys.exit(1)

    picam2 = initialize_camera()

    aruco_dict = config.ARUCO_DICT
    parameters = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)

    HOST = '0.0.0.0'
    PORT = config.NETWORK_PORT

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        logging.info(f"Server is live. Waiting for connections on port {PORT}...")

        while True:
            try:
                conn, addr = s.accept()
                handle_client_connection(conn, addr, picam2, camera_matrix, dist_coeffs, detector)
                logging.info("Connection closed. Ready to accept a new connection.")
            except KeyboardInterrupt:
                logging.info("Shutdown signal received.")
                break
            except Exception as e:
                logging.error(f"Error in main accept loop: {e}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.critical(f"Server failed to start: {e}")
    finally:
        logging.info("--- MoCap Server Shut Down ---")
