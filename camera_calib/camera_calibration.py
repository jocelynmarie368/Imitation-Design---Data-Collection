import cv2
import numpy as np
import glob
import os

# Checkerboard Configs (Modify accordingly)
DIMENSION = (6, 9)
SIZE = 0.03

criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

objpoints = [] # 3D point in real world space
imgpoints = [] # 2D points in image plane

# Keep calibration files together inside the camera_calib folder.
camera_calib_folder = os.path.dirname(os.path.abspath(__file__))
checkerboard_folder = os.path.join(camera_calib_folder, 'checkerboard_imgs')

imgs = glob.glob(os.path.join(checkerboard_folder, '*.jpg'))
imgs += glob.glob(os.path.join(checkerboard_folder, '*.png'))

if not imgs:
    print("No calibration images found.")
    print(f"Add checkerboard images to '{checkerboard_folder}' and run this script again.")
    raise SystemExit

# Create the 3D coordinates for the checkerboard corners
objp = np.zeros((DIMENSION[0] * DIMENSION[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:DIMENSION[0], 0:DIMENSION[1]].T.reshape(-1, 2)
objp *= SIZE

image_size = None

for filename in imgs:
    image = cv2.imread(filename)
    if image is None:
        print(f"Could not read: {filename}")
        continue

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    found, corners = cv2.findChessboardCorners(gray, DIMENSION, None)

    if found:
        corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

        # Preview the detected corners before using them for calibration
        preview = image.copy()
        cv2.drawChessboardCorners(preview, DIMENSION, corners, found)
        cv2.imshow('Detected Checkerboard Corners', preview)
        key = cv2.waitKey(500) & 0xFF
        if key == ord('q'): # Press 'q' to exit
            cv2.destroyAllWindows()
            raise SystemExit

        objpoints.append(objp)
        imgpoints.append(corners)
        image_size = gray.shape[::-1]
        print(f"Checkerboard found: {filename}")
    else:
        print(f"Checkerboard not found: {filename}")

cv2.destroyAllWindows()

if len(objpoints) < 1:
    print("No checkerboards were detected")
    raise SystemExit

# Calculate the camera matrix and distortion coefficients.
success, camera_matrix, distortion, _, _ = cv2.calibrateCamera(
    objpoints, imgpoints, image_size, None, None
)

if success:
    calibration_file = os.path.join(camera_calib_folder, 'camera_calibration.npz')
    np.savez(
        calibration_file,
        camera_matrix=camera_matrix,
        distortion=distortion,
    )
    print("Calibration finished")
    print(f"Saved calibration data to {calibration_file}")
else:
    print("Calibration failed")
