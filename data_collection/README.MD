# Image Data Collection
The script will run image data capturing for the vehicle

# Overview
In `config.py`, toggle `RGB_CAPTURE` and `THERMAL_CAPTURE` depending on which camera to capture, or can do both at the same time

- RGB images will be stored in `/rgb_imgs` directory
- Thermal images will be stored in `/thermal_imgs` directory
- By default, images will be captured every **30** frames (Can be modified)
- Naming format for images: [rgb|thermal]\_{image_count}\_{timestamp}.jpg

# How to Run the Script
To run the script:
`python dc_script.py`