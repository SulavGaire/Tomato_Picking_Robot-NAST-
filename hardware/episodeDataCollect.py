import spidev
import pigpio
from picamera2 import Picamera2
import cv2
import csv
import time
import os
import numpy as np
from datetime import datetime
from threading import Lock

# ================= Configuration =================
DATA_DIR = "dataset"
EPISODE_FORMAT = "episode-%Y%m%d-%H%M%S"  # Folder name format
VIDEO_RESOLUTION = (640, 480)
SPI_CHANNELS = [0, 1, 2]  # MCP3208 channels for 3 potentiometers
SERVO_PINS = [18, 19, 20]  # GPIO pins for 3 servos
WEBCAM_INDEX = 1  # USB webcam device index
FILTER_SIZE = 10  # Moving average filter size
MAX_CAMERA_RETRIES = 3  # Camera recovery attempts
TARGET_FPS = 30  # Frame capture rate
# ==================================================


class DataCollector:
    def __init__(self):
        self.running = False
        self.lock = Lock()
        self.episode_dir = self._create_episode_dir()

        # Initialize hardware components
        self.picam = self._init_picam()
        self.webcam = self._init_webcam()
        self.spi = self._init_spi()
        self.pi = self._init_pigpio()
        self.csv_file, self.csv_writer = self._init_csv()

        # Data buffers
        self.adc_history = {ch: [] for ch in SPI_CHANNELS}
        self.last_frame_time = time.time()

    def _create_episode_dir(self):
        """Create episode directory with timestamp"""
        timestamp = datetime.now().strftime(EPISODE_FORMAT)
        episode_path = os.path.join(DATA_DIR, timestamp)

        os.makedirs(os.path.join(episode_path, "picam_frames"), exist_ok=True)
        os.makedirs(os.path.join(episode_path, "webcam_frames"), exist_ok=True)
        print(f"Episode directory created at: {os.path.abspath(episode_path)}")
        return episode_path

    def _init_picam(self):
        """Initialize Raspberry Pi camera with retries"""
        for attempt in range(MAX_CAMERA_RETRIES):
            try:
                camera = Picamera2()
                config = camera.create_video_configuration(
                    main={"size": VIDEO_RESOLUTION}, buffer_count=2, display="main"
                )
                camera.configure(config)
                camera.start()
                time.sleep(2)  # Camera warm-up
                return camera
            except Exception as e:
                print(f"PiCam init attempt {attempt + 1} failed: {str(e)}")
                if attempt == MAX_CAMERA_RETRIES - 1:
                    raise RuntimeError("PiCam initialization failed after retries")

    def _init_webcam(self):
        """Initialize USB webcam"""
        for attempt in range(MAX_CAMERA_RETRIES):
            try:
                webcam = cv2.VideoCapture(WEBCAM_INDEX)
                webcam.set(cv2.CAP_PROP_FRAME_WIDTH, VIDEO_RESOLUTION[0])
                webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, VIDEO_RESOLUTION[1])
                if not webcam.isOpened():
                    raise RuntimeError("Webcam not opened")
                return webcam
            except Exception as e:
                print(f"Webcam init attempt {attempt + 1} failed: {str(e)}")
                if attempt == MAX_CAMERA_RETRIES - 1:
                    raise RuntimeError("Webcam initialization failed after retries")

    def _init_spi(self):
        """Initialize MCP3208 SPI connection"""
        spi = spidev.SpiDev()
        try:
            spi.open(0, 0)
            spi.max_speed_hz = 1000000
            return spi
        except Exception as e:
            raise RuntimeError(f"SPI initialization failed: {str(e)}")

    def _init_pigpio(self):
        """Initialize pigpio for servo control"""
        pi = pigpio.pi()
        if not pi.connected:
            raise RuntimeError("pigpio daemon not running")
        return pi

    def _init_csv(self):
        """Initialize CSV data logger"""
        csv_path = os.path.join(self.episode_dir, "data.csv")
        file = open(csv_path, "w", newline="")
        writer = csv.writer(file)
        writer.writerow(
            ["timestamp", "angle1", "angle2", "angle3", "picam_frame", "webcam_frame"]
        )
        return file, writer

    def _read_adc(self, channel):
        """Read ADC value from specified channel"""
        try:
            adc = self.spi.xfer2([6 | (channel >> 2), (channel & 3) << 6, 0])
            return ((adc[1] & 0x0F) << 8) + adc[2]
        except Exception as e:
            print(f"ADC read error: {str(e)}")
            return None

    def _moving_average(self, new_value, channel):
        """Apply moving average filter to ADC values"""
        with self.lock:
            history = self.adc_history[channel]
            history.append(new_value)
            if len(history) > FILTER_SIZE:
                history.pop(0)
            return sum(history) / len(history)

    def _get_angles(self):
        """Read and process angles from all potentiometers"""
        angles = []
        for ch in SPI_CHANNELS:
            raw = self._read_adc(ch)
            if raw is None:
                return None

            # Invert and filter ADC value
            inverted = 4095 - raw
            filtered = self._moving_average(inverted, ch)
            angle = round((filtered / 4095) * 180.0, 2)
            angles.append(angle)
        return angles

    def _capture_frames(self, timestamp):
        """Capture frames from both cameras"""
        frame_data = {
            "picam": None,
            "webcam": None,
            "picam_frame": None,
            "webcam_frame": None,
        }

        try:
            # Capture PiCam frame
            picam_frame = self.picam.capture_array()
            picam_frame = cv2.cvtColor(picam_frame, cv2.COLOR_RGB2BGR)
            picam_filename = os.path.join(
                self.episode_dir, "picam_frames", f"{timestamp}.jpg"
            )
            cv2.imwrite(picam_filename, picam_frame)
            frame_data["picam"] = picam_filename
            frame_data["picam_frame"] = picam_frame
        except Exception as e:
            print(f"PiCam capture error: {str(e)}")
            self.picam.stop()
            self.picam.start()
            time.sleep(1)

        try:
            # Capture Webcam frame
            ret, webcam_frame = self.webcam.read()
            if ret:
                webcam_filename = os.path.join(
                    self.episode_dir, "webcam_frames", f"{timestamp}.jpg"
                )
                cv2.imwrite(webcam_filename, webcam_frame)
                frame_data["webcam"] = webcam_filename
                frame_data["webcam_frame"] = webcam_frame
        except Exception as e:
            print(f"Webcam capture error: {str(e)}")
            self.webcam.release()
            self.webcam = self._init_webcam()

        return frame_data

    def run(self):
        """Main data collection loop"""
        self.running = True
        print("Starting data collection... (Press 'Q' to stop)")
        cv2.namedWindow("PiCam View", cv2.WINDOW_NORMAL)
        cv2.namedWindow("WebCam View", cv2.WINDOW_NORMAL)

        try:
            while self.running:
                start_time = time.time()
                timestamp = datetime.now().isoformat()

                # Capture sensor data
                angles = self._get_angles()
                frame_data = self._capture_frames(timestamp)

                # Process and record data if all components available
                if angles and frame_data["picam"] and frame_data["webcam"]:
                    # Write to CSV
                    self.csv_writer.writerow(
                        [
                            timestamp,
                            angles[0],
                            angles[1],
                            angles[2],
                            os.path.basename(frame_data["picam"]),
                            os.path.basename(frame_data["webcam"]),
                        ]
                    )

                    # Update servo positions
                    for pin, angle in zip(SERVO_PINS, angles):
                        pulse_width = int(500 + (angle / 180) * 2000)
                        self.pi.set_servo_pulsewidth(pin, pulse_width)

                # Display real-time video feeds
                if frame_data["picam_frame"] is not None:
                    cv2.imshow("PiCam View", frame_data["picam_frame"])
                if frame_data["webcam_frame"] is not None:
                    cv2.imshow("WebCam View", frame_data["webcam_frame"])

                # Check for exit command
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    self.running = False

                # Maintain frame rate
                elapsed = time.time() - start_time
                sleep_time = max(0, (1 / TARGET_FPS) - elapsed)
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            self.running = False
        finally:
            self._cleanup()

    def _cleanup(self):
        """Release all resources safely"""
        print("\nCleaning up resources...")
        cv2.destroyAllWindows()

        if hasattr(self, "picam") and self.picam.started:
            self.picam.stop()
            self.picam.close()

        if hasattr(self, "webcam") and self.webcam.isOpened():
            self.webcam.release()

        if hasattr(self, "spi"):
            self.spi.close()

        if hasattr(self, "csv_file"):
            self.csv_file.close()

        if hasattr(self, "pi"):
            for pin in SERVO_PINS:
                self.pi.set_servo_pulsewidth(pin, 0)
            self.pi.stop()

        print("Data collection stopped successfully")


if __name__ == "__main__":
    try:
        collector = DataCollector()
        collector.run()
    except Exception as e:
        print(f"\nFatal error: {str(e)}")
        print("Check:")
        print("- Camera connections (both PiCam and USB webcam)")
        print("- 'sudo pigpiod' is running")
        print("- SPI is enabled in raspi-config")
        print("- Webcam permissions and correct device index")
        exit(1)
