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
VIDEO_RESOLUTION = (640, 480)
SPI_CHANNELS = [0, 1]  # MCP3208 channels for 2 potentiometers
SERVO_PINS = [18, 19]  # GPIO pins for 2 servos
FILTER_SIZE = 10  # Moving average filter size
MAX_CAMERA_RETRIES = 3  # Camera recovery attempts
TARGET_FPS = 30  # Frame capture rate
# ==================================================


class DataCollector:
    def __init__(self):
        self.running = False
        self.lock = Lock()
        self._create_directories()

        # Initialize hardware components
        self.camera = self._init_camera()
        self.spi = self._init_spi()
        self.pi = self._init_pigpio()
        self.csv_file, self.csv_writer = self._init_csv()

        # Data buffers
        self.adc_history = {ch: [] for ch in SPI_CHANNELS}
        self.last_frame_time = time.time()

    def _create_directories(self):
        """Create required dataset directories"""
        os.makedirs(os.path.join(DATA_DIR, "videos"), exist_ok=True)
        print(f"Dataset directories created at: {os.path.abspath(DATA_DIR)}")

    def _init_camera(self):
        """Initialize Raspberry Pi camera with retries"""
        for attempt in range(MAX_CAMERA_RETRIES):
            try:
                camera = Picamera2()
                config = camera.create_still_configuration(
                    main={"size": VIDEO_RESOLUTION}, buffer_count=2, display="main"
                )
                camera.configure(config)
                camera.start()
                time.sleep(2)  # Camera warm-up
                return camera
            except Exception as e:
                print(f"Camera init attempt {attempt + 1} failed: {str(e)}")
                if attempt == MAX_CAMERA_RETRIES - 1:
                    raise RuntimeError("Camera initialization failed after retries")

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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = os.path.join(DATA_DIR, f"data_{timestamp}.csv")
        file = open(csv_path, "w", newline="")
        writer = csv.writer(file)
        writer.writerow(["timestamp", "angle1", "angle2", "video_frame"])
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
        """Read and process angles from both potentiometers"""
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

    def _capture_frame(self, timestamp):
        """Capture and save video frame with error recovery"""
        try:
            frame = self.camera.capture_array()
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            filename = os.path.join(DATA_DIR, "videos", f"{timestamp}.jpg")
            cv2.imwrite(filename, frame)
            return filename
        except Exception as e:
            print(f"Frame capture error: {str(e)}")
            # Attempt camera restart
            self.camera.stop()
            self.camera.start()
            time.sleep(1)
            return None

    def run(self):
        """Main data collection loop"""
        self.running = True
        print("Starting data collection... (Press Ctrl+C to stop)")

        try:
            while self.running:
                start_time = time.time()
                timestamp = datetime.now().isoformat()

                # Capture sensor data
                angles = self._get_angles()
                frame_path = self._capture_frame(timestamp)

                if angles and frame_path:
                    # Write to CSV
                    self.csv_writer.writerow(
                        [timestamp, angles[0], angles[1], os.path.basename(frame_path)]
                    )

                    # Update servo positions
                    for pin, angle in zip(SERVO_PINS, angles):
                        pulse_width = int(500 + (angle / 180) * 2000)
                        self.pi.set_servo_pulsewidth(pin, pulse_width)

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

        if hasattr(self, "camera") and self.camera.started:
            self.camera.stop()
            self.camera.close()

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
        print("- Camera cable connection")
        print("- 'sudo pigpiod' is running")
        print("- SPI is enabled in raspi-config")
        exit(1)
