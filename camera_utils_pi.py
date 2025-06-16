# camera_utils.py
# UPDATED FOR RASPBERRY PI CAMERA MODULE (using picamera2)
 
import time
from picamera2 import Picamera2
import cv2  # OpenCV is still needed for color space conversion
 
class Camera:
    """
    A wrapper class for the Raspberry Pi Camera (picamera2 library).
    This class provides an OpenCV-compatible interface for grabbing frames.
    """
    def __init__(self, resolution=(640, 480)):
        """
        Initializes the Raspberry Pi Camera using the picamera2 library.
        """
        self.picam2 = Picamera2()
        
        # Configure the camera for video capture.
        # The 'main' stream is what we use for capturing numpy arrays.
        # We request an RGB format, as it's common for processing.
        config = self.picam2.create_video_configuration(
            main={"size": resolution, "format": "RGB888"}
        )
        self.picam2.configure(config)
        
        # Start the camera stream.
        self.picam2.start()
        
        # The camera needs a moment to warm up and adjust settings like auto-exposure.
        time.sleep(1.0)
        print("PiCamera initialized and running.")
 
    def get_frame(self):
        """
        Captures a single frame from the camera stream.
 
        Returns:
            A tuple (True, frame) where `frame` is a NumPy array in BGR format,
            to maintain compatibility with the rest of the OpenCV-based application.
        """
        # capture_array() returns a NumPy array representing the image.
        rgb_frame = self.picam2.capture_array()
        
        # OpenCV works with BGR format by default for functions like imwrite and imshow.
        # We must convert the RGB frame captured by picamera2 to BGR.
        bgr_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
        
# Return True to mimic the 'ret' value from OpenCV's VideoCapture.read()
        return True, bgr_frame
 
    def release(self):
        """
        Stops the camera stream and releases the resources.
        """
        self.picam2.stop()
        print("PiCamera released.")