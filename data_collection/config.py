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
