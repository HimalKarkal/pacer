import socket
import time

ARDUINO_IP = "10.33.110.199"
PORT = 8080
NUM_LEDS = 24

# DEMO SCALING
# ------------
# We're pretending the 24-LED ring is a 200m indoor track. At real running
# paces (a few km/h to low double digits), a lap of a 200m track takes tens
# of seconds to minutes - way longer than a few-second demo. Played back at
# literal real-time, the dot barely creeps (which is why it looked broken:
# you were seeing ~2 of the 3 trail LEDs sit almost still, not a moving
# blip). DEMO_TIME_SCALE fixes this by fast-forwarding wall-clock time for
# the position calculation only - think of it as watching a time-lapse of
# the runner. At 25x, the default demo (7.2 km/h uniform pace, 4s window)
# plays out as exactly one full lap of the ring. Turn this up for a faster
# whiz, down for a slower, more "real-time" crawl.
TRACK_LENGTH_M = 200.0
DEMO_TIME_SCALE = 25.0

# Scales every color sent to the strip. 1.0 = full brightness (whatever
# value each function passes in, e.g. green's 255), 0.0 = off. Applied once
# in send_frame() below, so it affects the countdown flashes and the trail
# uniformly - no need to touch color values in multiple places.
BRIGHTNESS = 0.05

_sock = None


def connect():
    """Opens (or re-opens) the single persistent connection to the Arduino."""
    global _sock
    if _sock is not None:
        try:
            _sock.close()
        except Exception:
            pass
    _sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _sock.settimeout(2.0)
    _sock.connect((ARDUINO_IP, PORT))
    _sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)


def send_frame(commands):
    """
    Sends a batch of (index, r, g, b) tuples in ONE write over the
    persistent connection. This is the key fix from earlier: previously
    every single command opened a fresh TCP connection, which couldn't
    keep up with the ~40ms frame rate and left the Arduino processing a
    backlog of stale connections. The sketch already reads 4-byte chunks
    in a loop, so multiple commands can safely ride in a single packet.
    """
    global _sock
    payload = bytearray()
    for index, r, g, b in commands:
        r = int(r * BRIGHTNESS)
        g = int(g * BRIGHTNESS)
        b = int(b * BRIGHTNESS)
        payload += bytes([int(index) % NUM_LEDS, r & 0xFF, g & 0xFF, b & 0xFF])
    try:
        _sock.sendall(payload)
    except (BrokenPipeError, ConnectionResetError, OSError):
        # Link dropped mid-show - reconnect once and retry this frame
        connect()
        _sock.sendall(payload)


def send_command(index, r, g, b):
    """Single-LED convenience wrapper, still batched under the hood."""
    send_frame([(index, r, g, b)])


def clear_all():
    send_frame([(i, 0, 0, 0) for i in range(NUM_LEDS)])


def render_trail(position):
    """
    Draws a solid, 3-LED-wide GREEN blip centered on `position`, all three
    dots at equal full brightness so all three are clearly visible.

    Wraparound is handled by `% NUM_LEDS`: as `position` sweeps past 23.x,
    `int(position + 1) % NUM_LEDS` rolls over from 23 to 0, so the blip
    flows straight from the last LED back to the first - the ring is
    treated as infinite/circular, no special-casing needed.
    """
    frame = [(i, 0, 0, 0) for i in range(NUM_LEDS)]
    for offset in (-1, 0, 1):
        idx = int(position + offset) % NUM_LEDS
        frame[idx] = (idx, 0, 255, 0)  # pure green, full brightness
    send_frame(frame)


def countdown_flash():
    print("Get ready... 3, 2, 1...")
    colors = [
        (255, 0, 0),  # 1: Red
        (0,0,0),      # 2. Blank
        (255,165, 0), # 3: Orange
        (0,0,0),      # 4. Blank
        (0, 255, 0)   # 5: Green (Go)
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
    time.sleep(0.2)
    run_uniform_pacing(target_speed_kmh=7.2, duration_sec=10.0)
    time.sleep(0.3)
 
    countdown_flash()
    time.sleep(0.2)
    run_acceleration(start_speed_kmh=0, target_speed_kmh=30, duration_sec=30.0)
    time.sleep(0.3)
 
    countdown_flash()
    time.sleep(0.2)
    run_deceleration(start_speed_kmh=12.6, target_speed_kmh=0.0, duration_sec=15.0)
 
    clear_all()
    _sock.close()
    print("Pacing sequence complete!")

if __name__ == "__main__":
    main()