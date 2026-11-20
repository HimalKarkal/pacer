import serial
import time
import math

SERIAL_PORT = "COM3"       # <-- update to match your Arduino's port (Windows: COMx, Linux/Mac: /dev/ttyACM0 etc.)
BAUD_RATE = 115200
NUM_LEDS = 24

TRACK_LENGTH_M = 200.0
DEMO_TIME_SCALE = 25.0
BRIGHTNESS = 0.05

_ser = None


def connect():
    global _ser
    if _ser is not None:
        try:
            _ser.close()
        except Exception:
            pass
    _ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2.0)
    # Opening the port resets the R4 (like an Uno). Give it time to
    # finish setup() before we start sending frames.
    time.sleep(2.0)


def send_frame(commands):
    global _ser
    # Build a full frame of colors for all LEDs
    frame_colors = [[0, 0, 0] for _ in range(NUM_LEDS)]
    for index, r, g, b in commands:
        idx = int(index) % NUM_LEDS
        frame_colors[idx] = [
            int(r * BRIGHTNESS) & 0xFF,
            int(g * BRIGHTNESS) & 0xFF,
            int(b * BRIGHTNESS) & 0xFF
        ]

    # Payload format: [SYNC_BYTE (0xFF), r0, g0, b0, r1, g1, b1, ..., checksum]
    payload = bytearray([0xFF])
    color_bytes = bytearray()
    for r, g, b in frame_colors:
        # Avoid sending 0xFF in color bytes to prevent sync byte collision
        if r == 0xFF: r = 0xFE
        if g == 0xFF: g = 0xFE
        if b == 0xFF: b = 0xFE
        color_bytes.append(r)
        color_bytes.append(g)
        color_bytes.append(b)

    checksum = 0
    for byte in color_bytes:
        checksum ^= byte

    payload.extend(color_bytes)
    payload.append(checksum)

    try:
        _ser.write(payload)
    except (serial.SerialException, OSError):
        connect()
        _ser.write(payload)


def send_command(index, r, g, b):
    send_frame([(index, r, g, b)])


def clear_all():
    send_frame([(i, 0, 0, 0) for i in range(NUM_LEDS)])


def render_trail(position):
    frame = [(i, 0, 0, 0) for i in range(NUM_LEDS)]
    for offset in (-1, 0, 1):
        idx = int(math.floor(position + offset)) % NUM_LEDS
        frame[idx] = (idx, 0, 255, 0)
    send_frame(frame)


def countdown_flash():
    print("Get ready... 3, 2, 1...")
    colors = [
        (255, 0, 0),
        (0, 0, 0),
        (255, 165, 0),
        (0, 0, 0),
        (0, 255, 0),
    ]
    for color in colors:
        send_frame([(i, *color) for i in range(NUM_LEDS)])
        time.sleep(1)
        clear_all()
        time.sleep(0.1)


def run_uniform_pacing(target_speed_kmh, duration_sec):
    print(f"--- Uniform Pacing: {target_speed_kmh} km/h for {duration_sec}s ---")
    target_speed_m_s = target_speed_kmh / 3.6
    meters_per_led = TRACK_LENGTH_M / NUM_LEDS
    leds_per_second = target_speed_m_s / meters_per_led

    start_time = time.time()
    while (time.time() - start_time) < duration_sec:
        real_elapsed = time.time() - start_time
        sim_elapsed = real_elapsed * DEMO_TIME_SCALE
        current_position = (leds_per_second * sim_elapsed) % NUM_LEDS
        render_trail(current_position)
        time.sleep(0.04)


def run_acceleration(start_speed_kmh, target_speed_kmh, duration_sec):
    print(f"--- Acceleration: {start_speed_kmh} km/h -> {target_speed_kmh} km/h over {duration_sec}s ---")
    start_speed = start_speed_kmh / 3.6
    target_speed = target_speed_kmh / 3.6
    meters_per_led = TRACK_LENGTH_M / NUM_LEDS

    start_time = time.time()
    current_position = 0.0

    while (time.time() - start_time) < duration_sec:
        t = time.time() - start_time
        fraction = min(t / duration_sec, 1.0)

        current_speed = start_speed + (target_speed - start_speed) * fraction
        leds_per_sec = current_speed / meters_per_led
        current_position = (current_position + leds_per_sec * 0.04 * DEMO_TIME_SCALE) % NUM_LEDS

        render_trail(current_position)
        time.sleep(0.04)


def run_deceleration(start_speed_kmh, target_speed_kmh, duration_sec):
    print(f"--- Deceleration: {start_speed_kmh} km/h -> {target_speed_kmh} km/h over {duration_sec}s ---")
    start_speed = start_speed_kmh / 3.6
    target_speed = target_speed_kmh / 3.6
    meters_per_led = TRACK_LENGTH_M / NUM_LEDS

    start_time = time.time()
    current_position = 0.0

    while (time.time() - start_time) < duration_sec:
        t = time.time() - start_time
        fraction = min(t / duration_sec, 1.0)

        current_speed = start_speed - (start_speed - target_speed) * fraction
        if current_speed < 0:
            current_speed = 0

        leds_per_sec = current_speed / meters_per_led
        current_position = (current_position + leds_per_sec * 0.04 * DEMO_TIME_SCALE) % NUM_LEDS

        render_trail(current_position)
        time.sleep(0.04)


def main():
    connect()
    clear_all()
    time.sleep(0.2)

    countdown_flash()
    run_acceleration(0, 30, 15)
    clear_all()
    _ser.close()


if __name__ == "__main__":
    main()