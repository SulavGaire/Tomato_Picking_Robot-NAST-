# Robotic Arm Control System Documentation  
**Project Overview**: A robotic arm control system using imitation learning, featuring 3 servo motors (joint control) + 1 stepper motor (base rotation), with dual-camera data collection and real-time visualization.  

---

## **1. Hardware Components**  
| Component              | Model/Specs                          |  
|------------------------|--------------------------------------|  
| Single-Board Computer  | Raspberry Pi 4B                     |  
| Servo Motors (x3)      | Standard 180° PWM Servos            |  
| Stepper Motor          | 28BYJ-48 (with L298N driver)        |  
| Potentiometers (x4)    | B500k (for servos + base)           |  
| ADC Chip               | MCP3208 (12-bit, SPI)               |  
| Cameras                | Raspberry Pi Camera (Picam) + USB Webcam |  
| Motor Driver           | L298N Dual H-Bridge                 |  

---

## **2. Circuit Diagram & Connections**  
### **2.1 L298N Stepper Motor Connections**  
| L298N Pin | Raspberry Pi GPIO | Wire Color (Typical) |  
|-----------|-------------------|----------------------|  
| IN1       | GPIO17            | Blue                 |  
| IN2       | GPIO27            | Pink                 |  
| IN3       | GPIO22            | Yellow               |  
| IN4       | GPIO23            | Orange               |  
| ENA       | GPIO24            | -                    |  
| ENB       | GPIO25            | -                    |  
| +12V      | 12V PSU           | Red                  |  
| GND       | Pi GND            | Black                |  

**Notes**:  
- Use a **separate 12V power supply** for the L298N motor power.  
- Connect Pi and L298N **GND** together.  

---

### **2.2 Potentiometer Connections (MCP3208 ADC)**  
| MCP3208 Pin | Raspberry Pi Connection | Potentiometer Wiring |  
|-------------|-------------------------|----------------------|  
| CH0-CH2     | Servo Pots (Joints)     | Middle Pin → ADC CHx |  
| CH3         | Base Pot                | Middle Pin → ADC CH3 |  
| VDD         | 3.3V                    | -                    |  
| VREF        | 3.3V                    | -                    |  
| AGND/DGND   | GND                     | -                    |  
| CLK         | GPIO11 (SPI SCLK)       | -                    |  
| DOUT        | GPIO9 (SPI MISO)        | -                    |  
| DIN         | GPIO10 (SPI MOSI)       | -                    |  
| CS/SHDN     | GPIO8 (SPI CE0)         | -                    |  

---

### **2.3 Servo Connections**  
| Servo | Raspberry Pi GPIO |  
|-------|-------------------|  
| 1     | GPIO18            |  
| 2     | GPIO19            |  
| 3     | GPIO20            |  

---

### **2.4 Camera Connections**  
- **Pi Camera**: Connected via Raspberry Pi CSI port.  
- **USB Webcam**: Connected to USB port (device index `1`).  

---

## **3. Software Setup**  
### **3.1 Raspberry Pi Configuration**  
1. Enable interfaces:  
   ```bash
   sudo raspi-config
   ```  
   - Enable **SPI**, **I2C**, and **Camera**.  

2. Install dependencies:  
   ```bash
   sudo apt install pigpio python3-opencv
   sudo systemctl enable pigpiod
   sudo systemctl start pigpiod
   pip install spidev picamera2 dash plotly pandas
   ```

---

### **3.2 Directory Structure**  
```bash
project/  
├── dataset/  
│   └── episode-YYYYMMDD-HHMMSS/  
│       ├── picam_frames/  
│       ├── webcam_frames/  
│       └── data.csv  
├── episodeDataCollect.py  
└── VisualizeEpisode.py  
```

---

## **4. Code Overview**  
### **4.1 `episodeDataCollect.py`**  
**Key Functions**:  
1. **Hardware Initialization**:  
   - Sets up SPI for ADC, GPIO for servos/stepper, and cameras.  
   - Starts background thread for stepper control.  

2. **Data Collection Loop**:  
   - Reads potentiometer values (ADC) at 30 FPS.  
   - Controls servos via PWM and stepper via L298N.  
   - Captures frames from both cameras.  
   - Logs data to `data.csv`.  

3. **Stepper Control**:  
   - Uses a **half-step sequence** (8 steps per cycle) for smooth motion.  
   - Threaded worker updates motor position based on potentiometer input.  

**Run the Collector**:  
```bash
python3 episodeDataCollect.py
```

---

### **4.2 `VisualizeEpisode.py`**  
**Features**:  
- Interactive Dash web dashboard.  
- Real-time angle plots for all joints + base.  
- Hover-to-preview camera frames.  
- Multi-episode comparison.  

**Launch Visualization**:  
```bash
python3 VisualizeEpisode.py
```  
Access at: `http://<pi-ip>:8050`  

---

## **5. Calibration**  
1. **Servo Calibration**:  
   - Rotate pots fully CW/CCW to verify 0°–180° movement.  

2. **Stepper Calibration**:  
   - Adjust `STEPS_PER_REV` in code (default = 2048 for 28BYJ-48 with half-stepping).  
   - Rotate the base pot to verify full 360° rotation.  

3. **Camera Alignment**:  
   - Ensure PiCam focuses on the gripper, and webcam captures the entire arm.  

---

## **6. Troubleshooting**  
| Issue                  | Solution                          |  
|------------------------|-----------------------------------|  
| Stepper not moving     | Check ENA/ENB pins (must be HIGH) |  
| SPI ADC errors         | Verify `spidev` installation      |  
| Webcam not detected    | Confirm device index (try `0` or `1`) |  
| Servo jitter           | Add capacitors to servo power lines |  
| Latency in visualization | Reduce `TARGET_FPS` or image resolution |  

---

## **7. Safety & Optimization**  
- Use a **separate power supply** for motors to avoid Raspberry Pi voltage drops.  
- Attach heatsinks to the L298N driver.  
- Secure wiring to prevent loose connections.  
- Adjust `FILTER_SIZE` in code to tune potentiometer noise filtering.  

---