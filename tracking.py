# Dependencies
import cv2
import numpy as np
from picamera2 import Picamera2
import time
import socket
import json

# --- Configuration ---
# Camera Settings
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

# ArUco Settings
ARUCO_DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_5X5_50)
NUM_MARKERS = 50

# Network Settings
HOST = '0.0.0.0'  # Listen on all available network interfaces
PORT = 65432      # Port to listen on for client connections

# --- Picamera2 Initialization ---
picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"size": (FRAME_WIDTH, FRAME_HEIGHT), "format": "BGR888"},
    controls={"FrameDurationLimits": (33333, 33333)} # For ~30 FPS
)
picam2.configure(config)

# --- ArUco Detector Initialization ---
parameters = cv2.aruco.DetectorParameters()
detector = cv2.aruco.ArucoDetector(ARUCO_DICT, parameters)

# --- Main Server Logic ---
# The script will wait here until a client connects.
try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"Server is live. Waiting for a connection on {HOST}:{PORT}...")
        conn, addr = s.accept() # This is a blocking call

        with conn:
            print(f"Connected by {addr}")
            
            # Start the camera ONLY after a client has connected
            picam2.start()
            time.sleep(1.0) # Allow camera to warm up
            print("Camera started. Streaming data...")

            while True:
                # Capture a frame as a NumPy array
                frame = picam2.capture_array()
                
                # --- ArUco Detection Logic ---
                frame_positions = [None] * NUM_MARKERS
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                corners, ids, rejected = detector.detectMarkers(gray)

                if ids is not None:
                    for i, marker_id in enumerate(ids.flatten()):
                        if 0 <= marker_id < NUM_MARKERS:
                            marker_corners = corners[i].reshape((4, 2))
                            cx = int(np.mean(marker_corners[:, 0]))
                            cy = int(np.mean(marker_corners[:, 1]))
                            frame_positions[marker_id] = (cx, cy)
                
                # --- Data Transmission ---
                # Serialize the list to a JSON string. Add a newline to delimit messages.
                data_to_send = json.dumps(frame_positions) + '\n'
                
                # Send the data, encoded as bytes
                conn.sendall(data_to_send.encode('utf-8'))

except (BrokenPipeError, ConnectionResetError):
    print("Client disconnected.")

finally:
    # --- Cleanup ---
    picam2.stop()
    print("Camera stopped. Server shut down.")