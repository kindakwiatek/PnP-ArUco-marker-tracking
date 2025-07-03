import cv2
import numpy as np
import os
import json
from picamera2 import Picamera2
import time
import config # Import the new configuration file

# You need a chessboard pattern. The numbers here are the number of *internal* corners
# This is calculated automatically from the CHESSBOARD_DIMENSIONS in the config file
chessboard_corners = (config.CHESSBOARD_DIMENSIONS[0] - 1, config.CHESSBOARD_DIMENSIONS[1] - 1)

# --- Picamera2 Initialization ---
print("Initializing Picamera2...")
picam2 = Picamera2()
# Create a camera configuration for preview and capture, using settings from the config file
# Note: The variable is named 'camera_config' to avoid conflict with the imported 'config' module
camera_config = picam2.create_preview_configuration(
    main={"size": (config.FRAME_WIDTH, config.FRAME_HEIGHT), "format": "BGR888"}
)
picam2.configure(camera_config)
# Start the camera stream
picam2.start()
print("Camera started. Allowing 2 seconds for sensor to settle...")
time.sleep(2.0)


# --- Main Calibration Logic ---
print("\nStarting Camera Calibration...")
print(f"--> Looking for a {chessboard_corners[0]}x{chessboard_corners[1]} chessboard pattern.")
print("--> Point the camera at the chessboard.")
print("--> Press the [SPACE] bar to capture an image.")
print("--> You need at least 15 good images from different angles and distances.")
print("--> Press [c] to calibrate once you have enough images.")
print("--> Press [q] to quit at any time.")

# Create the output folder for images if it doesn't exist
if not os.path.exists(config.CALIBRATION_IMAGES_FOLDER):
    os.makedirs(config.CALIBRATION_IMAGES_FOLDER)
    print(f"Folder '{config.CALIBRATION_IMAGES_FOLDER}' created.")

# Termination criteria for the corner sub-pixel algorithm
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

# Prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(8,5,0)
objp = np.zeros((chessboard_corners[0] * chessboard_corners[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:chessboard_corners[0], 0:chessboard_corners[1]].T.reshape(-1, 2)

# Arrays to store object points and image points from all the images
objpoints = []  # 3d point in real world space
imgpoints = []  # 2d points in image plane

images_captured = 0
window_name = 'Calibration'

try:
    while True:
        # Capture a frame from the Picamera2 stream
        frame = picam2.capture_array()

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Display the current frame
        display_frame = frame.copy()
        cv2.putText(display_frame, f"Images Captured: {images_captured}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
        cv2.imshow(window_name, display_frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord(' '):  # Space bar to capture
            # Find the chess board corners
            ret, corners = cv2.findChessboardCorners(gray, chessboard_corners, None)

            # If found, add object points, image points (after refining them)
            if ret:
                # Save the captured frame BEFORE drawing on it
                image_filename = os.path.join(config.CALIBRATION_IMAGES_FOLDER, f"calibration-image-{images_captured}.png")
                cv2.imwrite(image_filename, frame)

                images_captured += 1
                print(f"SUCCESS: Image {images_captured} captured and saved to {image_filename}.")

                objpoints.append(objp)

                # Refine corner locations for better accuracy
                corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
                imgpoints.append(corners2)

                # Draw and display the corners on the frame for visualization
                cv2.drawChessboardCorners(frame, chessboard_corners, corners2, ret)
                cv2.imshow('Last Capture', frame)
            else:
                print("FAILURE: Could not find chessboard. Try a different angle or lighting.")

        elif key == ord('c'):
            if images_captured >= 15:
                print("\nCalibrating camera... this may take a moment.")

                # Perform camera calibration
                ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)

                if ret:
                    print("Calibration successful!")
                    # Create a dictionary to hold the calibration data
                    # Convert numpy arrays to lists to make them JSON serializable
                    calibration_data = {
                        'camera_matrix': mtx.tolist(),
                        'distortion_coefficients': dist.tolist()
                    }

                    # Save the data to a JSON file
                    with open(config.CALIBRATION_DATA_FILE, 'w') as f:
                        json.dump(calibration_data, f, indent=4)

                    print(f"Calibration data saved to '{config.CALIBRATION_FILE}'")
                    break  # Exit the loop after successful calibration
                else:
                    print("Calibration failed. Please try again with more diverse images.")
            else:
                print(f"Calibration requires at least 15 images. You only have {images_captured}.")


        elif key == ord('q'):
            print("Quitting calibration process.")
            break

        # Check if the window was closed by the user
        try:
            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                break
        except cv2.error:
            # This can happen if the window is closed while the script is busy
            break

finally:
    # --- Cleanup ---
    print("Shutting down.")
    picam2.stop()
    cv2.destroyAllWindows()
