

### **Circuit Diagram**  
<!-- ![Circuit Diagram](https://via.placeholder.com/600x400?text=MCP3208+%7C+Raspberry+Pi+4+%7C+Potentiometers+%26+Servos)  
*(Replace with actual diagram or use tools like Fritzing to create one.)* -->

#### **Components**:
1. **Raspberry Pi 4** (with GPIO pins).
2. **MCP3208 ADC** (12-bit, 8-channel).
3. **2x B500k Potentiometers**.
4. **2x Servo Motors** (e.g., SG90).
5. **0.1µF Capacitors** (for noise reduction).
6. **Breadboard & Jumper Wires**.
7. **Separate 5V Power Supply** (for servos).

---

### **Hardware Connections**  
| **Component**      | **Raspberry Pi 4 / MCP3208 Connection**        |
|---------------------|------------------------------------------------|
| **MCP3208 VDD**     | 3.3V (Pi Pin 1)                                |
| **MCP3208 VREF**    | 3.3V (Pi Pin 1)                                |
| **MCP3208 AGND**    | GND (Pi Pin 6)                                 |
| **MCP3208 DGND**    | GND (Pi Pin 6)                                 |
| **MCP3208 CLK**     | GPIO11/SCLK (Pi Pin 23)                        |
| **MCP3208 DIN**     | GPIO10/MOSI (Pi Pin 19)                        |
| **MCP3208 DOUT**    | GPIO9/MISO (Pi Pin 21)                         |
| **MCP3208 CS**      | GPIO8/CE0 (Pi Pin 24)                          |
| **Pot 1 (CH0)**     | Wiper → MCP3208 CH0, Ends → 3.3V & GND         |
| **Pot 2 (CH1)**     | Wiper → MCP3208 CH1, Ends → 3.3V & GND         |
| **Servo 1 Signal**  | GPIO18 (Pi Pin 12)                             |
| **Servo 2 Signal**  | GPIO19 (Pi Pin 35)                             |
| **Servo Power**     | 5V External Supply → Servo VCC, GND → Pi GND   |

---

### **Key Design Notes**  
1. **Noise Reduction**:
   - Add **0.1µF capacitors** between each potentiometer’s wiper and GND.
   - Use short wires for analog signals (potentiometer to MCP3208).

2. **Power Isolation**:
   - Servos draw high current: Use a **separate 5V supply** (not the Pi’s 5V pin).
   - Common ground between Pi, MCP3208, and servos.

3. **ADC Calibration**:
   - The MCP3208’s 12-bit resolution gives `0–4095` values for `0–3.3V`.

---

### **Software Documentation**  
#### **Dependencies**  
Install required libraries:  
```bash
sudo apt-get update
sudo apt-get install pigpio python3-pigpio python3-spidev
```

#### **Code Workflow**  
1. **SPI Initialization**:  
   - Configure the MCP3208 ADC at 1 MHz speed.  
   ```python
   spi = spidev.SpiDev()
   spi.open(0, 0)  # Bus 0, CE0
   spi.max_speed_hz = 1000000
   ```

2. **Servo Control**:  
   - Use `pigpio` library for hardware PWM (GPIO18/19).  
   ```python
   pi = pigpio.pi()
   pi.set_servo_pulsewidth(SERVO_PIN_1, pulse_width1)
   ```

3. **ADC Reading & Filtering**:  
   - Read ADC values from CH0 and CH1.  
   - Apply a **moving average filter** to reduce noise.  
   ```python
   def moving_average(new_value, history):
       history.append(new_value)
       if len(history) > FILTER_SIZE:
           history.pop(0)
       return sum(history) / len(history)
   ```

4. **Angle Mapping**:  
   - Convert ADC values to angles (`0–180°` for servos).  
   ```python
   angle1 = (inverted_adc1 / 4095) * 180.0
   ```

5. **Direction Fix**:  
   - Invert ADC values if servos rotate backward.  
   ```python
   inverted_adc1 = 4095 - filtered_adc1
   ```

---

### **Troubleshooting**  
| **Issue**               | **Solution**                                   |
|-------------------------|------------------------------------------------|
| Servo jitters/shakes    | Increase `FILTER_SIZE` or add capacitors.      |
| Angle flickers          | Check potentiometer wiring and grounding.      |
| Servo doesn’t move      | Verify PWM pins (GPIO18/19) and 5V power.      |
| `pigpio` connection error | Run `sudo pigpiod` to start the daemon.      |

---

### **Testing Procedure**  
1. **Potentiometer Calibration**:  
   - Rotate pots fully CCW → Servos should be at `0°`.  
   - Rotate pots fully CW → Servos should reach `180°`.  

2. **Noise Check**:  
   - Monitor printed angles for stability.  

---

### **Final Notes**  
- Use **hardware PWM pins (GPIO12/18/19)** for jitter-free servo control.  
- Adjust `FILTER_SIZE` in code for smoother motion.  
- Always disconnect power before modifying circuits.  

