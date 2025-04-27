import spidev
import pigpio
import time

# Initialize SPI for MCP3208
spi = spidev.SpiDev()
spi.open(0, 0)  # (bus, CE)
spi.max_speed_hz = 1000000  # 1 MHz

# Initialize pigpio for servo control
pi = pigpio.pi()
if not pi.connected:
    print("ERROR: Run 'sudo pigpiod' first.")
    exit()

# Servo GPIO Pins
SERVO_PIN_1 = 18  # GPIO18 for Servo 1
SERVO_PIN_2 = 19  # GPIO19 for Servo 2

# Filter parameters for both channels
FILTER_SIZE = 10
adc_history_1 = []
adc_history_2 = []


def read_adc(channel):
    adc = spi.xfer2([6 | (channel >> 2), (channel & 3) << 6, 0])
    return ((adc[1] & 0x0F) << 8) + adc[2]


def moving_average(new_value, history):
    history.append(new_value)
    if len(history) > FILTER_SIZE:
        history.pop(0)
    return sum(history) / len(history)


try:
    while True:
        # Read and filter ADC values
        raw_adc1 = read_adc(0)  # Potentiometer 1 on CH0
        filtered_adc1 = moving_average(raw_adc1, adc_history_1)
        inverted_adc1 = 4095 - filtered_adc1  # Reverse direction

        raw_adc2 = read_adc(1)  # Potentiometer 2 on CH1
        filtered_adc2 = moving_average(raw_adc2, adc_history_2)
        inverted_adc2 = 4095 - filtered_adc2  # Reverse direction

        # Calculate angles (0-180Â°)
        angle1 = round((inverted_adc1 / 4095) * 180.0, 1)
        angle2 = round((inverted_adc2 / 4095) * 180.0, 1)

        # Calculate pulse widths (500-2500 Âµs)
        pulse_width1 = int(500 + (inverted_adc1 / 4095) * 2000)
        pulse_width2 = int(500 + (inverted_adc2 / 4095) * 2000)

        # Update servos
        pi.set_servo_pulsewidth(SERVO_PIN_1, pulse_width1)
        pi.set_servo_pulsewidth(SERVO_PIN_2, pulse_width2)

        # Print angles
        print(f"Servo 1: {angle1}Â° | Servo 2: {angle2}Â°   ", end="\r", flush=True)
        time.sleep(0.02)

except KeyboardInterrupt:
    pi.set_servo_pulsewidth(SERVO_PIN_1, 0)
    pi.set_servo_pulsewidth(SERVO_PIN_2, 0)
    spi.close()
    pi.stop()
    print("\nServos stopped. Exiting.")
