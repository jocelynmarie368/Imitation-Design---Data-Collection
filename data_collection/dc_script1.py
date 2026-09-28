import os
import csv
import time
import threading
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


# ---------------------------------------------------------------------------
# Sensor logging
# ---------------------------------------------------------------------------

_sensor_lock = threading.Lock()
_stop_event = threading.Event()

imu_gnss_state = {
    'accel_x': 0.0, 'accel_y': 0.0, 'accel_z': 0.0,
    'gyro_x': 0.0, 'gyro_y': 0.0, 'gyro_z': 0.0,
    'lat': 0.0, 'lon': 0.0, 'alt': 0.0,
}

control_state = {
    'linear_speed': 0.0,   # m/s, forward positive
    'angular': 0.0,        # rad/s, turn rate
}


def read_imu_gnss():
    '''Background thread: polls the Xsens MTi-680G and updates imu_gnss_state'''
    if config.IMU_INPUT_MODE == 'xsensdeviceapi':
        _read_imu_gnss_xda()
    elif config.IMU_INPUT_MODE == 'serial_raw':
        _read_imu_gnss_serial()
    else:
        raise ValueError(f'Unknown IMU_INPUT_MODE: {config.IMU_INPUT_MODE}')


def _read_imu_gnss_xda():
    '''
    Uses Xsens' official xsensdeviceapi (XDA) Python bindings, bundled with
    the MT Software Suite. Requires a wheel built for your platform - check
    for an aarch64/Jetson build before relying on this path.
    '''
    try:
        import xsensdeviceapi as xda
    except ImportError:
        print('[imu] xsensdeviceapi not importable on this platform. '
              'Check for an ARM64 wheel in your MT SDK install, or switch '
              "IMU_INPUT_MODE to 'serial_raw' in config.py.")
        return

    class Callback(xda.XsCallback):
        def __init__(self):
            xda.XsCallback.__init__(self)

        def onLiveDataAvailable(self, dev, packet):
            if packet is None:
                return
            with _sensor_lock:
                if packet.containsCalibratedData():
                    acc = packet.calibratedAcceleration()
                    gyr = packet.calibratedGyroscopeData()
                    imu_gnss_state['accel_x'], imu_gnss_state['accel_y'], imu_gnss_state['accel_z'] = acc[0], acc[1], acc[2]
                    imu_gnss_state['gyro_x'], imu_gnss_state['gyro_y'], imu_gnss_state['gyro_z'] = gyr[0], gyr[1], gyr[2]
                if packet.containsLatitudeLongitude():
                    ll = packet.latitudeLongitude()
                    imu_gnss_state['lat'], imu_gnss_state['lon'] = ll[0], ll[1]
                if packet.containsAltitude():
                    imu_gnss_state['alt'] = packet.altitude()

    control = xda.XsControl.construct()
    port_info_array = xda.XsScanner.scanPorts()
    mt_port = next((p for p in port_info_array if p.deviceId().isMti()), None)
    if mt_port is None:
        print('[imu] No Xsens MTi device found.')
        return

    control.openPort(mt_port.portName(), mt_port.baudrate())
    device = control.device(mt_port.deviceId())
    callback = Callback()
    device.addCallbackHandler(callback)
    device.gotoConfig()
    device.gotoMeasurement()
    print('[imu] Xsens MTi-680G streaming started.')

    while not _stop_event.is_set():
        time.sleep(0.01)

    device.gotoConfig()
    control.closePort(mt_port.portName())


def _read_imu_gnss_serial():
    '''
    Fallback: read the MTi's raw serial output directly with pyserial.
    Parsing the MTData2 binary protocol from scratch is nontrivial - adapt
    an existing open-source parser (e.g. mtdevice.py from the
    ethzasl_xsens_driver project) and have its callback update
    imu_gnss_state instead of publishing to ROS.
    '''
    raise NotImplementedError(
        'Plug in a raw serial MTData2 parser here if xsensdeviceapi is not '
        "available for this platform's architecture."
    )


def read_manual_controls():
    '''Background thread: polls the simchair/wheel and updates control_state'''
    if config.STEERING_INPUT_MODE == 'joystick':
        _read_manual_controls_joystick()
    elif config.STEERING_INPUT_MODE == 'serial':
        _read_manual_controls_serial()
    else:
        raise ValueError(f'Unknown STEERING_INPUT_MODE: {config.STEERING_INPUT_MODE}')


def _read_manual_controls_joystick():
    '''
    Reads the wheel/pedal rig via pygame's joystick module. Axis indices
    are device-specific - print raw axis values once to confirm the mapping
    before trusting config.WHEEL_AXIS / config.THROTTLE_AXIS.

    This vehicle is differential/tracked-drive, so the wheel axis maps to
    angular turn rate and the throttle/brake axis maps to linear speed -
    there is no separate "steering angle" being logged.
    '''
    import pygame
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print('[manual] No joystick/wheel detected.')
        return

    joy = pygame.joystick.Joystick(0)
    joy.init()
    print(f'[manual] Reading input from: {joy.get_name()}')

    while not _stop_event.is_set():
        pygame.event.pump()
        with _sensor_lock:
            control_state['angular'] = joy.get_axis(config.WHEEL_AXIS) * config.MAX_ANGULAR_RATE
            control_state['linear_speed'] = -joy.get_axis(config.THROTTLE_AXIS) * config.MAX_LINEAR_SPEED
        time.sleep(0.02)  # ~50 Hz poll rate


def _read_manual_controls_serial():
    '''
    Alternative: if linear/angular values arrive over USB serial from a
    microcontroller instead of a joystick, read that here.
    Expected line format: "linear_speed,angular" e.g. "0.80,0.12"
    '''
    import serial
    port = serial.Serial(config.CONTROL_SERIAL_PORT, config.CONTROL_SERIAL_BAUD, timeout=0.1)
    while not _stop_event.is_set():
        line = port.readline().decode(errors='ignore').strip()
        if not line:
            continue
        try:
            linear_speed, angular = (float(x) for x in line.split(','))
        except ValueError:
            continue
        with _sensor_lock:
            control_state['linear_speed'], control_state['angular'] = linear_speed, angular


def start_sensor_threads():
    '''Starts the IMU/GNSS and manual control background threads'''
    threads = (
        threading.Thread(target=read_imu_gnss, daemon=True),
        threading.Thread(target=read_manual_controls, daemon=True),
    )
    for thread in threads:
        thread.start()
    return threads


def stop_sensor_threads(threads):
    '''Signals background sensor threads to stop and waits for them to exit'''
    _stop_event.set()
    for thread in threads:
        thread.join(timeout=1.0)


def open_csv_writer(folder):
    '''Opens labels.csv for this run and writes the header row'''
    os.makedirs(folder, exist_ok=True)
    csv_path = os.path.join(folder, config.CSV_FILENAME)
    csv_file = open(csv_path, 'w', newline='')
    writer = csv.writer(csv_file)
    writer.writerow([
        'frame_count', 'time',
        'linear_speed', 'angular',
        'accel_x', 'accel_y', 'accel_z',
        'gyro_x', 'gyro_y', 'gyro_z',
        'lat', 'lon', 'alt',
    ])
    return csv_file, writer


def write_csv_row(writer, frame_count):
    '''Writes one CSV row using the latest sensor state at this instant'''
    with _sensor_lock:
        writer.writerow([
            frame_count, time.time(),
            control_state['linear_speed'], control_state['angular'],
            imu_gnss_state['accel_x'], imu_gnss_state['accel_y'], imu_gnss_state['accel_z'],
            imu_gnss_state['gyro_x'], imu_gnss_state['gyro_y'], imu_gnss_state['gyro_z'],
            imu_gnss_state['lat'], imu_gnss_state['lon'], imu_gnss_state['alt'],
        ])


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

    sensor_threads = start_sensor_threads() if config.CSV_CAPTURE else ()
    csv_file, csv_writer = open_csv_writer(config.CSV_FOLDER) if config.CSV_CAPTURE else (None, None)

    print(f'Capturing one image every {config.CAPTURE_EVERY_N_FRAMES} frames')
    print("Press 'q' to stop capturing.")

    frame_number = 0
    capture_count = 0

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
            should_capture = frame_number % config.CAPTURE_EVERY_N_FRAMES == 0

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
            if should_capture:
                capture_count += 1
                for name, frame in frames.items():
                    stream = streams[name]

                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                    filename = (
                        f"{name}_{stream['image_number']:06d}_{timestamp}{config.IMAGE_EXTENSION}"
                    )
                    filepath = os.path.join(stream['folder'], filename)

                    if cv2.imwrite(filepath, frame):
                        print(f'Saved: {filename}')
                        stream['image_number'] += 1

                if config.CSV_CAPTURE:
                    write_csv_row(csv_writer, capture_count)
                    csv_file.flush()

            if config.DISPLAY_PREVIEW and cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        for stream in streams.values():
            stream['camera'].release()
        cv2.destroyAllWindows()
        if config.CSV_CAPTURE:
            stop_sensor_threads(sensor_threads)
            csv_file.close()


if __name__ == '__main__':
    main()
