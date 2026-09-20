import os
import cv2
from datetime import datetime

import config


def erase_previous_images(folder):
    '''Erases saved images from previous runs'''
    for filename in os.listdir(folder):
        filepath = os.path.join(folder, filename)
        if os.path.isfile(filepath) and filename.lower().endswith(
            ('.jpg', '.jpeg', '.png')
        ):
            os.remove(filepath)


def open_camera(camera_index):
    '''Verifies Camera settings'''
    try:
        camera = cv2.VideoCapture(camera_index)
    except cv2.error as error:
        raise RuntimeError(
            f'Camera index {camera_index} could not be opened'
        ) from error

    if not camera.isOpened():
        camera.release()
        raise RuntimeError(f'Camera index {camera_index} was not found')

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, config.IMAGE_WIDTH)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, config.IMAGE_HEIGHT)
    return camera


def main():
    if not config.RGB_CAPTURE and not config.THERMAL_CAPTURE:
        print('Enable RGB_CAPTURE or THERMAL_CAPTURE in config.py')
        return

    if config.CAPTURE_EVERY_N_FRAMES < 1:
        print('CAPTURE_EVERY_N_FRAMES must be at least 1.')
        return

    print(f"*** RGB capture {'enabled' if config.RGB_CAPTURE else 'disabled'}")
    print(f"*** Thermal capture {'enabled' if config.THERMAL_CAPTURE else 'disabled'}\n")

    streams = {}

    camera_settings = (
        ('rgb', config.RGB_CAPTURE, config.RGB_CAMERA_INDEX, config.RGB_FOLDER, 'RGB Camera'),
        ('thermal', config.THERMAL_CAPTURE, config.THERMAL_CAMERA_INDEX, config.THERMAL_FOLDER, 'Thermal Camera'),
    )

    for name, enabled, camera_index, folder, window in camera_settings:
        if not enabled:
            continue

        os.makedirs(folder, exist_ok=True)
        if config.ERASE_HISTORY:
            erase_previous_images(folder)

        try:
            camera = open_camera(camera_index)
        except RuntimeError as error:
            for stream in streams.values():
                stream['camera'].release()
            raise RuntimeError(
                f'{name.capitalize()} capture could not start: {error}'
            ) from error

        streams[name] = {
            'camera': camera,
            'folder': folder,
            'image_number': 1,
            'window': window,
        }

    if not streams:
        return

    print(f'Capturing one image every {config.CAPTURE_EVERY_N_FRAMES} frames')
    print("Press 'q' to stop capturing.")

    frame_number = 0

    try:
        while streams:
            frames = {}
            for name in list(streams):
                success, frame = streams[name]['camera'].read()
                if not success:
                    print(f"Error: Couldn't read a frame from the {name} camera")
                    streams[name]['camera'].release()
                    del streams[name]
                    continue
                frames[name] = frame

            if not streams:
                break

            frame_number += 1

            if config.DISPLAY_PREVIEW:
                if 'rgb' in frames and 'thermal' in frames: # Stack 2 views into one windowed frame
                    rgb_frame = frames['rgb']
                    thermal_frame = frames['thermal']

                    if len(thermal_frame.shape) == 2:
                        thermal_frame = cv2.cvtColor(
                            thermal_frame, cv2.COLOR_GRAY2BGR
                        )

                    thermal_frame = cv2.resize(
                        thermal_frame,
                        (rgb_frame.shape[1], rgb_frame.shape[0]),
                    )
                    stacked_view = cv2.hconcat([rgb_frame, thermal_frame])
                    cv2.imshow('RGB + Thermal', stacked_view)
                else: # One windowed frame only
                    for name, frame in frames.items():
                        cv2.imshow(streams[name]['window'], frame)

            # -- Saving images --
            for name, frame in frames.items():
                stream = streams[name]

                if frame_number % config.CAPTURE_EVERY_N_FRAMES != 0:
                    continue

                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                filename = (
                    f"{name}_{stream['image_number']:06d}_{timestamp}{config.IMAGE_EXTENSION}"
                )
                filepath = os.path.join(stream['folder'], filename)

                if cv2.imwrite(filepath, frame):
                    print(f'Saved: {filename}')
                    stream['image_number'] += 1

            if config.DISPLAY_PREVIEW and cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        for stream in streams.values():
            stream['camera'].release()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
