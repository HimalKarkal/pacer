# Pacer: LED Strip Controller & Pacing Simulator

A high-performance pacing simulation system controlling a NeoPixel LED strip via WiFi using an Arduino Uno R4 / ESP32.

## Problem: Random Flashing of LED 0 (RESOLVED)

### Symptom
During acceleration, deceleration, and uniform pacing trials, LED 0 would randomly flash with various colors and intensities.

### Root Causes
1. **Framing Misalignment on Network Delays**: 
   Originally, the protocol sent individual 5-byte updates per LED: `[0xFF, index, r, g, b]` (amounting to 120 bytes for a full 24-LED frame). In standard WiFi networks (especially with TCP NODELAY enabled), packets could be fragmented or delayed.
   When the Arduino timed out waiting for the remaining bytes of a packet, those partially received bytes remained in the buffer. In subsequent loops, the outer loop skipped bytes until it found a `0xFF`. Since background/inactive LEDs were cleared to `(0, 0, 0)` on the Python side, a misaligned buffer read would often parse a `0` byte as the `index`, triggering a spurious/random write to LED 0.
2. **Integer Truncation on Negative Coordinates**:
   In `render_trail`, the index calculation was computed as `int(position + offset) % NUM_LEDS`.
   Because Python's `int()` truncates towards `0`, negative numbers close to zero (e.g. `position = 0.2` and `offset = -1` resulting in `-0.8`) were truncated to `0` rather than wrapping to `23`. This caused LED 0 to be active for a double-wide coordinate range compared to other LEDs, leading to asymmetry around the wrap-around boundary.

### Solution
1. **Full-Frame 73-Byte Protocol**:
   Instead of sending 24 separate 5-byte command packets, the system now constructs and sends a single, fixed-size 73-byte packet per frame:
   `[0xFF (SYNC_BYTE), r0, g0, b0, r1, g1, b1, ..., r23, g23, b23]`
   This reduces payload overhead by **39%** and guarantees that LED indexes are derived strictly from their positional sequence in the packet rather than parsed variable values.
2. **Sync Collision Avoidance**:
   We enforce that color values (after applying global `BRIGHTNESS`) never equal `0xFF` (by capping any `0xFF` byte to `0xFE`). This guarantees that `0xFF` in the data stream uniquely and exclusively identifies the start of a frame, enabling robust, self-healing framing.
3. **Symmetrical Wrapping with `math.floor`**:
   Updated the coordinate mapping to use `math.floor` (`int(math.floor(position + offset)) % NUM_LEDS`), ensuring clean, symmetrical wrapping at boundary edges.

---

## File Structure

- `main.py`: Python simulator script that manages pacing physics (acceleration, deceleration, uniform pacing) and transmits color frames over a TCP socket.
- `led_strip_controller/led_strip_controller.ino`: Arduino code managing the TCP server, receiving the 73-byte packages, and rendering them to the Adafruit NeoPixel strip.

---

## Protocol Specification

Each frame is transmitted as a single continuous TCP packet.

| Byte | Value | Description |
|---|---|---|
| 0 | `0xFF` | Frame Synchronization Byte |
| 1 | `0x00 - 0xFE` | LED 0 Red |
| 2 | `0x00 - 0xFE` | LED 0 Green |
| 3 | `0x00 - 0xFE` | LED 0 Blue |
| ... | ... | ... |
| 70 | `0x00 - 0xFE` | LED 23 Red |
| 71 | `0x00 - 0xFE` | LED 23 Green |
| 72 | `0x00 - 0xFE` | LED 23 Blue |

---

## Setup & Running

### Arduino Setup
1. Open `led_strip_controller/led_strip_controller.ino` in Arduino IDE.
2. Ensure you have the `WiFiS3` and `Adafruit_NeoPixel` libraries installed.
3. Update `ssid` and `password` variables to match your local WiFi network.
4. Upload the code to your Arduino.
5. Open the Serial Monitor at `115200` baud to find the printed Arduino IP Address.

### Python Setup
1. Update `ARDUINO_IP` in `main.py` with the IP address shown in the Serial Monitor.
2. Make sure you have python installed. Run the simulation script:
   ```bash
   python main.py
   ```
