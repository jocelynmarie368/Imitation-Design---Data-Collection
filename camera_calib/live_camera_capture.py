# This script collects checkerboard images directly from the live RGB camera.
# Press Space to save a valid checkerboard view for camera calibration.

import os
import cv2
import numpy as np


CAMERA_INDEX = 0
DIMENSION = (6, 9)
SIZE = 0.03
IMAGE_WIDTH = 720
IMAGE_HEIGHT = 720
MINIMUM_IMAGES = 10

SCRIPT_FOLDER = os.path.dirname(os.path.abspath(__file__))
IMAGE_FOLDER = os.path.join(SCRIPT_FOLDER, 'checkerboard_imgs')
CALIBRATION_FILE = os.path.join(SCRIPT_FOLDER, 'camera_calibration.npz')

criteria = (
    cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
    30,
    0.001,
)

objp = np.zeros((DIMENSION[0] * DIMENSION[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:DIMENSION[0], 0:DIMENSION[1]].T.reshape(-1, 2)
objp *= SIZE

objpoints = []
imgpoints = []


def calibrate_camera(image_size):
    if len(objpoints) < MINIMUM_IMAGES:
        print(f'Collect at least {MINIMUM_IMAGES} images first.')
        return

    success, camera_matrix, distortion, _, _ = cv2.calibrateCamera(
        objpoints,
        imgpoints,
        image_size,
        None,
        None,
    )

    if success:
        np.savez(
            CALIBRATION_FILE,
            camera_matrix=camera_matrix,
            distortion=distortion,
        )
        print(f'Calibration saved to {CALIBRATION_FILE}')
    else:
        print('Calibration failed.')


def main():
    os.makedirs(IMAGE_FOLDER, exist_ok=True)

    camera = cv2.VideoCapture(CAMERA_INDEX)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, IMAGE_WIDTH)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, IMAGE_HEIGHT)

    if not camera.isOpened():
        raise RuntimeError(f'Camera index {CAMERA_INDEX} could not be opened.')

    print("Press Space to collect a checkerboard image.")
    print("Press 'c' to calibrate or 'q' to quit.")

    image_size = None

    try:
        while True:
            success, frame = camera.read()
            if not success:
                print("Couldn't read a frame from the camera.")
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            found, corners = cv2.findChessboardCorners(gray, DIMENSION, None)
            preview = frame.copy()

            if found:
                corners = cv2.cornerSubPix(
                    gray,
                    corners,
                    (11, 11),
                    (-1, -1),
                    criteria,
                )
                cv2.drawChessboardCorners(preview, DIMENSION, corners, found)

            cv2.putText(
                preview,
                f'Collected: {len(objpoints)}',
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )
            cv2.imshow('Live Camera Calibration', preview)

            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                break

            if key == ord(' ') and found:
                objpoints.append(objp.copy())
                imgpoints.append(corners)
                image_size = gray.shape[::-1]
                filename = os.path.join(
                    IMAGE_FOLDER,
                    f'calibration_{len(objpoints):03d}.jpg',
                )
                cv2.imwrite(filename, frame)
                print(f'Collected image {len(objpoints)}')

            if key == ord('c') and image_size is not None:
                calibrate_camera(image_size)
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
