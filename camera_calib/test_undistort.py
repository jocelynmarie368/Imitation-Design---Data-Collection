# This script tests the saved camera calibration on every checkerboard image
# It saves each original and undistorted image together for easy comparison

import glob
import os

import cv2
import numpy as np


SCRIPT_FOLDER = os.path.dirname(os.path.abspath(__file__))
CALIBRATION_FILE = os.path.join(SCRIPT_FOLDER, 'camera_calibration.npz')
IMAGE_FOLDER = os.path.join(SCRIPT_FOLDER, 'checkerboard_imgs')
OUTPUT_FOLDER = os.path.join(SCRIPT_FOLDER, 'undistorted_test')
SHOW_PREVIEW = True


def find_images():
    image_patterns = ('*.jpg', '*.jpeg', '*.png')
    images = []

    for pattern in image_patterns:
        images.extend(glob.glob(os.path.join(IMAGE_FOLDER, pattern)))

    return images


def main():
    if not os.path.exists(CALIBRATION_FILE):
        print(f'Calibration file not found: {CALIBRATION_FILE}')
        return

    images = find_images()
    if not images:
        print(f'No images found in {IMAGE_FOLDER}')
        return

    calibration = np.load(CALIBRATION_FILE)
    camera_matrix = calibration['camera_matrix']
    distortion = calibration['distortion']

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    for image_path in images:
        image = cv2.imread(image_path)
        if image is None:
            print(f'Could not read image: {image_path}')
            continue

        height, width = image.shape[:2]
        new_matrix, _ = cv2.getOptimalNewCameraMatrix(
            camera_matrix,
            distortion,
            (width, height),
            1,
            (width, height),
        )
        undistorted = cv2.undistort(
            image,
            camera_matrix,
            distortion,
            None,
            new_matrix,
        )

        comparison = cv2.hconcat([image, undistorted])
        output_path = os.path.join(
            OUTPUT_FOLDER,
            f'comparison_{os.path.basename(image_path)}',
        )
        cv2.imwrite(output_path, comparison)
        print(f'Saved: {output_path}')

        if SHOW_PREVIEW:
            cv2.imshow('Original | Undistorted', comparison)
            if cv2.waitKey(300) & 0xFF == ord('q'):
                break

    if SHOW_PREVIEW:
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
