# mock_arduino.py

import asyncio
import math
import random
import time

import requests
import websockets

BASE_URL = "https://emg-web-g8cpfhghhqbacce4.centralus-01.azurewebsites.net"
WS_URL = "wss://emg-web-g8cpfhghhqbacce4.centralus-01.azurewebsites.net/ws/send"

BATCH_SIZE = 250
SAMPLE_PERIOD_US = 1000
CALIBRATION_FLEXES = 3


def create_session():
    r = requests.get(f"{BASE_URL}/api/arduino/new_session")
    r.raise_for_status()
    session_id = r.json()["session"]
    print(f"Created session: {session_id}")
    return session_id


def calibrate(session_id):
    print("\n=== CALIBRATION MODE ===")
    print(f"Performing {CALIBRATION_FLEXES} calibration flexes...")

    calibration_peaks = []

    for i in range(CALIBRATION_FLEXES):
        print(f"\nCalibration flex {i + 1}/{CALIBRATION_FLEXES}")
        print("Flex now... ", end="", flush=True)

        time.sleep(1)

        # Simulate a flex with peak around 200-250
        peak = random.uniform(180, 260)
        calibration_peaks.append(peak)

        print(f"Peak detected: {peak:.2f}")
        time.sleep(1.5)

    # Send calibration data
    payload = {
        "session": session_id,
        "calibration_values": calibration_peaks,
    }

    r = requests.post(f"{BASE_URL}/api/arduino/calibrate", json=payload, timeout=10)
    r.raise_for_status()

    result = r.json()
    normal_peak = result["normal_peak"]

    print(f"\n✓ Calibration complete!")
    print(f"  Normal peak: {normal_peak:.2f}")
    print(f"  Calibration values: {[f'{v:.2f}' for v in calibration_peaks]}")

    return normal_peak


def send_batch(session_id, start_micros, values):
    payload = {
        "session": session_id,
        "start_micros": start_micros,
        "sample_period_us": SAMPLE_PERIOD_US,
        "values": values,
    }

    r = requests.post(f"{BASE_URL}/api/arduino/batch", json=payload, timeout=10)
    return r.status_code == 200


def send_flex_event(session_id, timestamp_micros, peak_value, quality):
    payload = {
        "session": session_id,
        "timestamp_micros": timestamp_micros,
        "peak_value": peak_value,
        "quality": quality,
    }

    r = requests.post(f"{BASE_URL}/api/arduino/flex_event", json=payload, timeout=10)
    return r.status_code == 200


def classify_flex(peak_value, normal_peak, good_multiplier=1.2, poor_multiplier=0.7):
    good_threshold = normal_peak * good_multiplier
    poor_threshold = normal_peak * poor_multiplier

    if peak_value >= good_threshold:
        return "good"
    elif peak_value < poor_threshold:
        return "poor"
    return "normal"


async def send_live_data(websocket, values):
    for value in values:
        try:
            await websocket.send(str(value))
            await asyncio.sleep(0.001)  # 1ms between samples
        except Exception as e:
            print(f"WebSocket send error: {e}")
            break


async def run_session():
    session_id = create_session()

    # Perform calibration
    normal_peak = calibrate(session_id)

    print("\n=== STARTING DATA COLLECTION ===")
    print("Sending batches and live data...")

    sample_number = 0
    flex_cycle = 0

    # Connect to WebSocket for live data
    async with websockets.connect(WS_URL) as websocket:
        print("Connected to WebSocket for live streaming")

        while True:
            values = []
            start_micros = sample_number * SAMPLE_PERIOD_US
            batch_max = 0
            peak_timestamp = 0

            # Generate a batch with occasional flexes
            for i in range(BATCH_SIZE):
                # Base noise around 50-100
                base = random.uniform(50, 100)

                # Add flex every ~3 seconds (750 samples @ 1ms)
                flex_cycle = (sample_number % 750) / 750.0

                if 0.1 < flex_cycle < 0.3:  # Flex period
                    # Generate a flex with varying intensity
                    flex_intensity = random.choice(
                        [
                            normal_peak * 0.6,  # Poor flex
                            normal_peak * 1.0,  # Normal flex
                            normal_peak * 1.3,  # Good flex
                        ]
                    )
                    flex_shape = math.sin((flex_cycle - 0.1) * math.pi / 0.2)
                    value = int(base + flex_intensity * flex_shape)
                else:
                    value = int(base)

                values.append(value)

                if value > batch_max:
                    batch_max = value
                    peak_timestamp = start_micros + (i * SAMPLE_PERIOD_US)

                sample_number += 1

            # Send batch to server
            send_batch(session_id, start_micros, values)

            # Detect and classify flex
            if batch_max > 150:  # Threshold for flex detection
                quality = classify_flex(batch_max, normal_peak)
                send_flex_event(session_id, peak_timestamp, batch_max, quality)

                quality_color = {"good": "🟢", "normal": "🟡", "poor": "🔴"}
                print(
                    f"{quality_color.get(quality, '⚪')} Flex: {batch_max:.0f} ({quality})"
                )

            # Send live data via WebSocket
            await send_live_data(websocket, values)

            # Small delay between batches
            await asyncio.sleep(0.1)


if __name__ == "__main__":
    try:
        asyncio.run(run_session())
    except KeyboardInterrupt:
        print("\n\nStopped by user")
