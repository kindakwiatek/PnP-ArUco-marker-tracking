# server/distortion_calibration.py
#
# This command-line script performs camera intrinsic calibration.
# It is designed to be executed on a Raspberry Pi, typically triggered
# remotely via SSH from the main controller notebook. It can capture
# individual chessboard images or run the full calibration process.

import cv2
import numpy as np
import os
import json
from picamera2 import Picamera2
import time
import argparse
import sys

# Add the project root to the Python path to allow importing 'config'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config


def initialize_camera():
    """Initializes and configures the Picamera2 instance."""
    print("Initializing Picamera2...")
    picam2 = Picamera2()
    # Use a still configuration for higher quality captures
    camera_cfg = picam2.create_still_configuration(
        main={"size": (config.FRAME_WIDTH, config.FRAME_HEIGHT)},
        lores={"size": (config.FRAME_WIDTH, config.FRAME_HEIGHT)},
        display="lores"
    )
    picam2.configure(camera_cfg)
    picam2.start()
    # Allow time for the camera sensor to adjust to lighting conditions
    print("Camera started. Allowing 3 seconds for sensor to settle...")
    time.sleep(3.0)
    return picam2


def capture_and_save_image(picam2, hostname):
    """
    Captures a single frame, searches for a chessboard pattern,
    and saves the image if the pattern is found.
    """
    # Create the output directory if it does not exist
    output_dir = os.path.join(os.path.dirname(__file__), '..', config.DISTORTION_IMAGES_FOLDER)
    os.makedirs(output_dir, exist_ok=True)

    print("Capturing frame...")
    frame = picam2.capture_array("main")
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    print(f"Searching for {config.CHESSBOARD_DIMENSIONS} chessboard pattern...")
    ret, corners = cv2.findChessboardCorners(gray, config.CHESSBOARD_DIMENSIONS, None)

    if ret:
        # Find the next available image number to avoid overwriting
        i = 0
        while True:
            img_filename = os.path.join(output_dir, f"calibration_{hostname}_{i}.png")
            if not os.path.exists(img_filename):
                break
            i += 1
        
        cv2.imwrite(img_filename, frame)
        print(f"SUCCESS: Chessboard found. Image saved to '{img_filename}'")
        return True
    else:
        print("FAILURE: Chessboard not found. Try a different angle or lighting.")
        return False


def run_calibration_process():
    """
    Finds all captured calibration images, calculates the camera matrix
    and distortion coefficients, and saves them to a JSON file.
    """
    image_dir = os.path.join(os.path.dirname(__file__), '..', config.DISTORTION_IMAGES_FOLDER)

    if not os.path.isdir(image_dir):
        print(f"Error: Image directory '{image_dir}' not found. Capture images first.")
        return False

    # Termination criteria for the corner sub-pixel algorithm
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

    # Prepare object points, like (0,0,0), (1,0,0), ..., based on chessboard dimensions
    objp = np.zeros((config.CHESSBOARD_DIMENSIONS[0] * config.CHESSBOARD_DIMENSIONS[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:config.CHESSBOARD_DIMENSIONS[0], 0:config.CHESSBOARD_DIMENSIONS[1]].T.reshape(-1, 2)

    objpoints = []  # 3D points in real-world space
    imgpoints = []  # 2D points in the image plane
    
    images = [f for f in os.listdir(image_dir) if f.startswith('calibration_') and f.endswith('.png')]
    
    if len(images) < 15:
        print(f"Error: Calibration requires at least 15 images. Found only {len(images)}.")
        return False

    print(f"Processing {len(images)} images for calibration...")
    for fname in images:
        img = cv2.imread(os.path.join(image_dir, fname))
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ret, corners = cv2.findChessboardCorners(gray, config.CHESSBOARD_DIMENSIONS, None)
        if ret:
            objpoints.append(objp)
            # Refine corner locations for higher accuracy
            corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            imgpoints.append(corners2)

    if not objpoints:
        print("Error: Could not find chessboard in any of the processed images.")
        return False

    print("Calibrating camera... This may take a moment.")
    ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
        objpoints, imgpoints, gray.shape[::-1], None, None
    )

    if ret:
        print("Calibration successful!")
        calibration_data = {
            'camera_matrix': mtx.tolist(),
            'distortion_coefficients': dist.tolist()
        }
        # Save the data to the JSON file in the project root on the Pi
        save_path = os.path.join(os.path.dirname(__file__), '..', config.DISTORTION_DATA_FILE)
        with open(save_path, 'w') as f:
            json.dump(calibration_data, f, indent=4)
        print(f"Calibration data saved to '{save_path}'")
        return True
    else:
        print("Error: Calibration failed.")
        return False


def main():
    """Parses command-line arguments and executes the requested action."""
    parser = argparse.ArgumentParser(
        description="Headless camera distortion calibration script for Raspberry Pi."
    )
    parser.add_argument(
        "--capture",
        action="store_true",
        help="Capture a single image if a chessboard is found."
    )
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="Run calibration using all existing images in the calibration folder."
    )
    parser.add_argument(
        "--host",
        type=str,
        default="unknown-pi",
        help="Hostname of the Pi, used for naming captured images to prevent collisions."
    )
    args = parser.parse_args()

    if not args.capture and not args.calibrate:
        parser.print_help()
        sys.exit(1)

    if args.capture:
        picam2 = None
        try:
            picam2 = initialize_camera()
            if not capture_and_save_image(picam2, args.host):
                sys.exit(1)  # Exit with error code if capture fails
        finally:
            if picam2:
                picam2.stop()
                print("Camera stopped.")
    
    if args.calibrate:
        if not run_calibration_process():
            sys.exit(1)  # Exit with error code if calibration fails


if __name__ == "__main__":
    main()
