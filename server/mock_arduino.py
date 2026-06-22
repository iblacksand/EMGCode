# mock_arduino.py

import math
import time

import requests

BASE_URL = "http://127.0.0.1:8000"

BATCH_SIZE = 250
SAMPLE_PERIOD_US = 1000


r = requests.post(f"{BASE_URL}/api/arduino/new_session")

r.raise_for_status()

session_id = r.json()["session"]

print("Session:", session_id)

sample_number = 0

while True:
    values = []

    start_micros = sample_number * SAMPLE_PERIOD_US

    for _ in range(BATCH_SIZE):
        value = int(512 + 400 * math.sin(sample_number * 0.05))

        values.append(value)
        sample_number += 1

    payload = {
        "session": session_id,
        "start_micros": start_micros,
        "sample_period_us": SAMPLE_PERIOD_US,
        "values": values,
    }

    r = requests.post(
        f"{BASE_URL}/api/arduino/batch",
        json=payload,
        timeout=10,
    )

    print(f"batch sent: " f"{len(values)} samples " f"status={r.status_code}")

    time.sleep(0.25)
