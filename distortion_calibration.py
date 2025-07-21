"""
distortion_calibration.py

A standalone script to perform camera intrinsic calibration.

This script captures images of a chessboard pattern from various angles
and distances. It then uses these images to calculate the camera's
intrinsic matrix and distortion coefficients, which are essential for
correcting image distortion in the main application.

The results are saved to a JSON file specified in config.py.

Usage:
    Run this script directly from the command line on the Raspberry Pi
    with a display connected. Follow the on-screen instructions.
"""

import cv2
import numpy as np
import os
import json
from picamera2 import Picamera2
import time
import config


def main():
    """Main function to run the calibration process."""
    # The number of internal corners of the chessboard.
    chessboard_corners = (config.CHESSBOARD_DIMENSIONS[0] - 1, config.CHESSBOARD_DIMENSIONS[1] - 1)

    # --- Picamera2 Initialization ---
    print("Initializing Picamera2...")
    picam2 = Picamera2()
    camera_cfg = picam2.create_preview_configuration(
        main={"size": (config.FRAME_WIDTH, config.FRAME_HEIGHT), "format": "BGR888"}
    )
    picam2.configure(camera_cfg)
    picam2.start()
    print("Camera started. Allowing sensor to settle...")
    time.sleep(2.0)

    # --- Main Calibration Logic ---
    print("\n--- Camera Distortion Calibration ---")
    print(f"--> Looking for a {chessboard_corners[0]}x{chessboard_corners[1]} chessboard pattern.")
    print("--> Point the camera at the chessboard from various angles.")
    print("--> Press [SPACE] to capture an image for calibration.")
    print("--> A minimum of 15 good images is recommended.")
    print("--> Press [c] to perform calibration once enough images are captured.")
    print("--> Press [q] to quit without saving.")

    # Create the output folder for calibration images if it doesn't exist.
    if not os.path.exists(config.DISTORTION_IMAGES_FOLDER):
        os.makedirs(config.DISTORTION_IMAGES_FOLDER)
        print(f"Created directory: '{config.DISTORTION_IMAGES_FOLDER}'")

    # Termination criteria for the corner sub-pixel algorithm.
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

    # Prepare object points, like (0,0,0), (1,0,0), ..., (8,5,0).
    objp = np.zeros((chessboard_corners[0] * chessboard_corners[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:chessboard_corners[0], 0:chessboard_corners[1]].T.reshape(-1, 2)

    # Arrays to store object points and image points from all captured images.
    objpoints = []  # 3D points in real-world space
    imgpoints = []  # 2D points in the image plane
    images_captured = 0

    try:
        while True:
            frame = picam2.capture_array()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Display the live feed with capture count.
            display_frame = frame.copy()
            cv2.putText(display_frame, f"Images Captured: {images_captured}",
                        (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
            cv2.imshow('Distortion Calibration', display_frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord(' '):  # Space bar to capture image
                ret, corners = cv2.findChessboardCorners(gray, chessboard_corners, None)

                if ret:
                    # Save the raw frame before drawing on it.
                    img_filename = os.path.join(
                        config.DISTORTION_IMAGES_FOLDER,
                        f"calibration_img_{images_captured}.png"
                    )
                    cv2.imwrite(img_filename, frame)
                    images_captured += 1
                    print(f"SUCCESS: Chessboard found. Image {images_captured} saved.")

                    objpoints.append(objp)
                    # Refine corner locations for higher accuracy.
                    corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
                    imgpoints.append(corners2)
                else:
                    print("FAILURE: Chessboard not found. Try a different angle or lighting.")

            elif key == ord('c'):  # 'c' to calibrate
                if images_captured >= 15:
                    print("\nCalibrating camera... This may take a moment.")
                    ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
                        objpoints, imgpoints, gray.shape[::-1], None, None
                    )

                    if ret:
                        print("Calibration successful!")
                        calibration_data = {
                            'camera_matrix': mtx.tolist(),
                            'distortion_coefficients': dist.tolist()
                        }
                        # Save the data to the JSON file defined in config.
                        with open(config.DISTORTION_DATA_FILE, 'w') as f:
                            json.dump(calibration_data, f, indent=4)
                        print(f"Calibration data saved to '{config.DISTORTION_DATA_FILE}'")
                        break  # Exit after successful calibration.
                    else:
                        print("Calibration failed. Please try again with more diverse images.")
                else:
                    print(f"Calibration requires at least 15 images. You only have {images_captured}.")

            elif key == ord('q'):  # 'q' to quit
                print("Quitting calibration process.")
                break

    finally:
        # --- Cleanup ---
        print("Shutting down camera and closing windows.")
        picam2.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()