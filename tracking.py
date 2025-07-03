# Dependencies
import cv2
import numpy as np
from picamera2 import Picamera2
import time
import socket
import json
import os
import config # Import settings from config.py

# --- Function to Load Calibration Data ---
def load_calibration_data(filepath):
    # Load camera matrix and distortion coefficients from the specified JSON file
    if not os.path.exists(filepath):
        print(f"Error: Calibration file not found at '{filepath}'")
        print("Please run the calibration script first to generate this file.")
        raise SystemExit
        
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    camera_matrix = np.array(data['camera_matrix'], dtype=np.float32)
    dist_coeffs = np.array(data['distortion_coefficients'], dtype=np.float32)
    
    print("Calibration data loaded successfully.")
    return camera_matrix, dist_coeffs

# --- Main Program ---

# Step 1: Load the calibration data
camera_matrix, dist_coeffs = load_calibration_data(config.CALIBRATION_DATA_FILE)

# Step 2: Initialize the Pi Camera 2
picam2 = Picamera2()
# Note: Renamed to 'camera_config' to avoid conflict with the 'config' module
camera_config = picam2.create_preview_configuration(
    main={"size": (config.FRAME_WIDTH, config.FRAME_HEIGHT), "format": "BGR888"},
    controls={"FrameDurationLimits": (33333, 33333)} # For ~30 FPS
)
picam2.configure(camera_config)

# Step 3: Initialize the ArUco detector
parameters = cv2.aruco.DetectorParameters()
detector = cv2.aruco.ArucoDetector(config.ARUCO_DICT, parameters)

# Step 4: Set up the network server.
HOST = '0.0.0.0'  # Listen on all available network interfaces
PORT = config.NETWORK_PORT

try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"Server is live. Waiting for a connection on port {PORT}...")
        conn, addr = s.accept() # This is a blocking call

        with conn:
            print(f"Connected by {addr}")
            
            picam2.start()
            time.sleep(1.0) # Allow camera to warm up
            print("Camera started. Streaming 2D coordinate data...")

            while True:
                # Capture a frame
                frame_raw = picam2.capture_array()
                
                # Apply the distortion correction to the frame
                frame = cv2.undistort(frame_raw, camera_matrix, dist_coeffs, None, None)
                
                # --- Detection now runs on the corrected frame ---
                frame_positions = [] # List to hold position data for all visible markers
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                corners, ids, rejected = detector.detectMarkers(gray)

                if ids is not None:
                    for i, marker_id in enumerate(ids.flatten()):
                        if 0 <= marker_id < config.NUM_MARKERS:
                            # Calculate the center of the marker
                            marker_corners = corners[i].reshape((4, 2))
                            cx = int(np.mean(marker_corners[:, 0]))
                            cy = int(np.mean(marker_corners[:, 1]))
                            
                            # Store the position data in a dictionary
                            position_data = {
                                'id': int(marker_id),
                                'pos': [cx, cy]
                            }
                            frame_positions.append(position_data)
                
                # --- Data Transmission ---
                # Serialize the list of positions to a JSON string
                data_to_send = json.dumps(frame_positions) + '\n'
                conn.sendall(data_to_send.encode('utf-8'))

except (BrokenPipeError, ConnectionResetError):
    print("Client disconnected.")
except KeyboardInterrupt:
    print("\nScript interrupted by user.")
finally:
    # --- Cleanup ---
    picam2.stop()
    print("Camera stopped. Server shut down.")
