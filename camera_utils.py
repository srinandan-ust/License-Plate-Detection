# raspberry_pi_code/camera_utils.py
import cv2
import time

class Camera:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None
        self.connect()

    def connect(self):
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            print(f"Error: Could not open camera with index {self.camera_index}.")
            self.cap = None # Ensure cap is None if connection failed
        else:
            print(f"Camera {self.camera_index} opened successfully.")
            # Optional: Set camera properties
            # self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            # self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    def get_frame(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                return frame
        # Attempt to reconnect if frame grab fails or cap is not initialized
        print("Warning: Could not get frame. Attempting to reconnect camera...")
        self.release()
        time.sleep(1) # Wait a bit before reconnecting
        self.connect()
        if self.cap and self.cap.isOpened(): # Try one more time after reconnect
             ret, frame = self.cap.read()
             if ret:
                 return frame
        return None


    def release(self):
        if self.cap:
            self.cap.release()
            print("Camera released.")
        self.cap = None

if __name__ == '__main__':
    # Test camera_utils
    cam = Camera(0) # Use config.CAMERA_INDEX in main script
    if cam.cap: # Check if camera was successfully opened
        for i in range(5):
            frame = cam.get_frame()
            if frame is not None:
                cv2.imshow("Test Frame", frame)
                print(f"Frame {i+1} captured.")
                if cv2.waitKey(1000) & 0xFF == ord('q'):
                    break
            else:
                print(f"Failed to capture frame {i+1}.")
                break
        cam.release()
        cv2.destroyAllWindows()
    else:
        print("Camera test failed: Could not initialize camera.")