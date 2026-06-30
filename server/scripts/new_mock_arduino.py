import math
import random
import time

import requests

# --- Configuration ---
# Change this to http://localhost:8000 if running the server on the same machine
SERVER_URL = "http://localhost:8000"

BATCH_SIZE = 500
CALIBRATION_FLEXES = 3
NOISE_FLOOR = 50

# --- State Variables ---
session_id = ""
is_calibrated = False
accepted_calibrations = 0

normal_peak = 200
good_threshold = 400
poor_threshold = 100


def set_light_color(r, g, b):
    """Simulates the physical LED by printing the color to the console."""
    if r == 0 and g == 0 and b == 0:
        color = "OFF"
    elif r > 0 and g == 0 and b == 0:
        color = "RED"
    elif r == 0 and g > 0 and b == 0:
        color = "GREEN"
    elif r == 0 and g == 0 and b > 0:
        color = "BLUE"
    else:
        color = f"RGB({r},{g},{b})"

    print(f"[LED STATUS]: {color}")


def create_session():
    global session_id
    print("Creating session...")
    try:
        response = requests.post(f"{SERVER_URL}/api/arduino/new_session")
        if response.status_code == 200:
            data = response.json()
            session_id = data.get("session", "")
            print(f"Session ID: {session_id}")
            return True
        else:
            print(f"Session creation failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Connection error: {e}")
        return False


def get_settings():
    global normal_peak, good_threshold, poor_threshold
    print("Fetching settings...")
    try:
        response = requests.get(f"{SERVER_URL}/api/settings")
        if response.status_code == 200:
            data = response.json()
            normal_peak = data.get("normal_peak", 0)
            good_threshold = data.get("good_threshold", 0)
            poor_threshold = data.get("poor_threshold", 0)

            print("Settings loaded:")
            print(f"  Normal peak: {normal_peak}")
            print(f"  Good threshold: {good_threshold}")
            print(f"  Poor threshold: {poor_threshold}")
            return True
        else:
            print(f"Settings request failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Connection error: {e}")
        return False


# def generate_simulated_batch(is_flexing, is_strong):
#     """Generates a batch of 500 samples. If is_flexing is True, adds a simulated sine-wave peak."""
#     values = []
#     base_noise = lambda: random.randint(0, 15)

#     peak = 250 if not is_strong else 500

#     for i in range(BATCH_SIZE):
#         # A 500ms peak at 500Hz requires 250 samples.
#         # We start at index 125 and end at 375 (375 - 125 = 250 samples).
#         if is_flexing and 125 <= i <= 375:
#             # math.sin goes from 0 to 1 back to 0 as the input goes from 0 to pi.
#             # We scale the input to match the 250-sample window.
#             val = int(peak * math.sin(math.pi * (i - 125) / 250)) + base_noise()
#             values.append(val)
#         else:
#             values.append(base_noise())

#     return values


def generate_simulated_batch(is_flexing, is_strong):
    """Generates a batch of 500 samples. If is_flexing is True, adds a simulated square-wave peak."""
    values = []
    base_noise = lambda: random.randint(0, 15)

    # Adding a small fluctuation around the peak makes the square wave look like real sensor data
    flex_noise = lambda: random.randint(-15, 15)

    peak = 250 if not is_strong else 500

    for i in range(BATCH_SIZE):
        # A 500ms plateau at 500Hz requires 250 samples.
        if is_flexing and 125 <= i <= 375:
            # Instantly jump to the peak and hold it (plus minor noise)
            val = peak + flex_noise()
            values.append(val)
        else:
            # Resting state
            values.append(base_noise())

    return values


def send_batch(endpoint, values, start_micros, sample_period_us):
    set_light_color(0, 0, 255)  # Blue during WiFi TX

    payload = {
        "session": session_id,
        "start_micros": start_micros,
        "sample_period_us": sample_period_us,
        "values": values,
    }

    try:
        response = requests.post(f"{SERVER_URL}{endpoint}", json=payload)
        return response.status_code, response.text
    except requests.exceptions.RequestException as e:
        print(f"HTTP Post failed: {e}")
        return 500, ""


def setup():
    print("Simulating Arduino Setup...")
    set_light_color(255, 0, 0)  # Red while connecting (simulated)
    time.sleep(1)

    while not create_session():
        time.sleep(2)

    print(f"Ready. Entering calibration phase (Needs {CALIBRATION_FLEXES} flexes)...")


start = time.time()


def loop():
    global is_calibrated, accepted_calibrations, start

    # 1. Simulate data collection timing
    start_time_sec = time.time()
    start_micros = int(start_time_sec * 1_000_000)

    # Simulate a flex every few iterations to test logic automatically
    # (Random chance of 30% to flex on any given loop, but 100% if calibration)
    is_flexing = random.random() > 0.7 or not is_calibrated
    is_strong = (random.random() > 0.5) and is_calibrated
    values = generate_simulated_batch(is_flexing, is_strong)

    # Simulate the ~1 second it takes to collect 500 samples at 500Hz
    time.sleep(1.0)
    end_micros = int(time.time() * 1_000_000)
    sample_period_us = int((end_micros - start_micros) / BATCH_SIZE)

    # 2. Process LED feedback for max value in batch (simulating real-time loop)
    max_val = max(values)

    if not is_calibrated:
        print(f"\n[CALIBRATION] Batch collected. Max val: {max_val}. Sending...")
        status, text = send_batch(
            "/api/arduino/calibration_signal",
            values,
            0,
            sample_period_us,
        )

        if status == 200 and "true" in text.lower():
            print("Server ACCEPTED calibration flex!")
            set_light_color(0, 255, 0)  # Green for 1 sec on success
            time.sleep(1)
            accepted_calibrations += 1
        elif status == 200:
            print("Server REJECTED calibration flex (or no flex detected).")
            # Blink red
            for _ in range(3):
                set_light_color(255, 0, 0)
                time.sleep(0.2)
                set_light_color(0, 0, 0)
                time.sleep(0.2)

        if accepted_calibrations >= CALIBRATION_FLEXES:
            print("\nCalibration complete. Fetching final settings...")
            if get_settings():
                is_calibrated = True
                start = time.time()
                print("Entering Live Reading Phase...\n")

    else:
        # Live Phase
        print(f"[LIVE] Batch max: {max_val} | ", end="")

        # Evaluate simulated real-time LED status based on the peak in this batch
        if max_val >= good_threshold:
            print("Status: STRONG -> ", end="")
            set_light_color(0, 255, 0)
        elif max_val >= poor_threshold:
            print("Status: NORMAL -> ", end="")
            set_light_color(0, 0, 0)
        elif max_val > NOISE_FLOOR:
            print("Status: POOR/LOW -> ", end="")
            set_light_color(255, 0, 0)
        else:
            print("Status: RESTING -> ", end="")
            set_light_color(0, 0, 0)

        # Send live data
        start_micros = int((start_time_sec - start) * 1_000_000)
        status, _ = send_batch(
            "/api/arduino/batch", values, start_micros, sample_period_us
        )
        if status != 200:
            print(f"Upload failed with status {status}")


if __name__ == "__main__":
    setup()
    try:
        while True:
            loop()
    except KeyboardInterrupt:
        print("\nTest script stopped by user.")
