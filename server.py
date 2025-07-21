"""
server.py

This script runs on the Raspberry Pi. It performs the following actions:
- Initializes the PiCamera.
- Loads the camera's intrinsic calibration data.
- Detects ArUco markers in the camera feed.
- Establishes a network connection to a client.
- Streams the 2D coordinates of detected markers to the client.
- Responds to commands from the client (e.g., for PnP calibration).
"""

import cv2
import numpy as np
from picamera2 import Picamera2
import time
import socket
import json
import os
import threading
import config  # Import settings from config.py


def load_calibration_data(filepath):
    """
    Loads camera matrix and distortion coefficients from a JSON file.

    Args:
        filepath (str): The path to the calibration data file.

    Returns:
        tuple: A tuple containing the camera matrix (np.ndarray) and
               distortion coefficients (np.ndarray).
    
    Raises:
        SystemExit: If the calibration file is not found.
    """
    if not os.path.exists(filepath):
        print(f"Error: Calibration file not found at '{filepath}'")
        print("Please run the distortion_calibration.py script first.")
        raise SystemExit
        
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    camera_matrix = np.array(data['camera_matrix'], dtype=np.float32)
    dist_coeffs = np.array(data['distortion_coefficients'], dtype=np.float32)
    
    print("Camera intrinsic calibration data loaded successfully.")
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
    Manages a single client connection, handling command processing and data streaming.
    """
    print(f"Connected by {addr}")
    is_streaming = False
    
    try:
        with conn:
            # Create a file-like object for reading commands line-by-line
            f = conn.makefile()
            
            while True:
                # Non-blocking check for incoming commands
                # This part would need to be adapted for a more robust command handling system
                # For this example, we assume commands are sent and then streaming starts.

                # This is a placeholder for a more robust command loop.
                # In a real application, you would use select() or a separate
                # thread for non-blocking command reads.
                # For now, we will assume a simple start/stop flow.

                # --- Main Streaming Loop ---
                if not is_streaming: # Simplified start condition
                    picam2.start()
                    time.sleep(1.0) # Allow camera to warm up
                    print("Camera started. Streaming 2D coordinate data...")
                    is_streaming = True

                frame_raw = picam2.capture_array()
                
                # Undistort the frame using the calibration data
                frame = cv2.undistort(frame_raw, camera_matrix, dist_coeffs)
                
                # --- ArUco Marker Detection ---
                frame_positions = []
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                corners, ids, _ = detector.detectMarkers(gray)

                if ids is not None:
                    for i, marker_id in enumerate(ids.flatten()):
                        if 0 <= marker_id < config.NUM_MARKERS:
                            marker_corners = corners[i].reshape((4, 2))
                            # Calculate the center of the marker
                            cx = int(np.mean(marker_corners[:, 0]))
                            cy = int(np.mean(marker_corners[:, 1]))
                            
                            position_data = {'id': int(marker_id), 'pos': [cx, cy]}
                            frame_positions.append(position_data)
                
                # --- Data Transmission ---
                if frame_positions:
                    data_to_send = json.dumps(frame_positions) + '\n'
                    conn.sendall(data_to_send.encode('utf-8'))

    except (BrokenPipeError, ConnectionResetError):
        print(f"Client {addr} disconnected.")
    finally:
        if picam2.started:
            picam2.stop()
            print("Camera stream stopped due to client disconnection.")


def main():
    """Main function to set up the server and handle connections."""
    # Step 1: Load camera calibration data
    camera_matrix, dist_coeffs = load_calibration_data(config.DISTORTION_DATA_FILE)

    # Step 2: Initialize the camera
    picam2 = initialize_camera()

    # Step 3: Initialize the ArUco detector
    aruco_dict = config.ARUCO_DICT
    parameters = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)

    # Step 4: Set up the network server
    HOST = '0.0.0.0'  # Listen on all available network interfaces
    PORT = config.NETWORK_PORT

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"Server is live. Waiting for connections on port {PORT}...")

        while True:
            # This loop allows the server to accept new connections if a client disconnects.
            conn, addr = s.accept() # This is a blocking call
            # Each client connection can be handled in a new thread for concurrency
            # For this project, a single client is assumed.
            handle_client_connection(conn, addr, picam2, camera_matrix, dist_coeffs, detector)
            print("Ready to accept a new connection.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScript interrupted by user. Shutting down.")
    except SystemExit as e:
        print(f"System exit: {e}")
    finally:
        print("Server shut down.")