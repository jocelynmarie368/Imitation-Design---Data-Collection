import os

# Toggle RGB or Thermal capturing 
RGB_CAPTURE = True
THERMAL_CAPTURE = False

# Modify camera indexes if necessary
RGB_CAMERA_INDEX = 0
THERMAL_CAMERA_INDEX = 1

CAPTURE_EVERY_N_FRAMES = 30 # Captures an image every N frames
IMAGE_WIDTH = 720
IMAGE_HEIGHT = 720
IMAGE_EXTENSION = '.jpg'

ERASE_HISTORY = False # Set True to erase saved images from previous runs
DISPLAY_PREVIEW = True # Toggle to show the CV2 window

SCRIPT_FOLDER = os.path.dirname(os.path.abspath(__file__))
RGB_FOLDER = os.path.join(SCRIPT_FOLDER, 'rgb_imgs')
THERMAL_FOLDER = os.path.join(SCRIPT_FOLDER, 'thermal_imgs')

# CSV logging
CSV_CAPTURE = True
CSV_FOLDER = 'data'
CSV_FILENAME = 'labels.csv'

# IMU/GNSS source
IMU_INPUT_MODE = 'xsensdeviceapi'  # or 'serial_raw' if no ARM wheel exists for the Jetson

# Manual control source
STEERING_INPUT_MODE = 'joystick'   # or 'serial'
WHEEL_AXIS = 0                     # ** Confirm first
THROTTLE_AXIS = 1                  # ** Confirm first
MAX_ANGULAR_RATE = 2.0             # rad/s
MAX_LINEAR_SPEED = 1.53            # m/s

# Only needed if STEERING_INPUT_MODE = 'serial'
CONTROL_SERIAL_PORT = '/dev/ttyACM0'
CONTROL_SERIAL_BAUD = 115200
