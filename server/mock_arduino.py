# mock_arduino.py

import math
import time

import requests

BASE_URL = "http://127.0.0.1:8000"

BATCH_SIZE = 100
SAMPLE_PERIOD_US = 1000

resp = requests.post(f"{BASE_URL}/api/arduino/new_session")

session_id = resp.json()["session"]

sample_index = 0

while True:
    values = []

    for _ in range(BATCH_SIZE):
        value = int(512 + 400 * math.sin(sample_index * 0.05))

        values.append(value)
        sample_index += 1

    payload = {
        "session": session_id,
        "start_micros": sample_index * SAMPLE_PERIOD_US,
        "sample_period_us": SAMPLE_PERIOD_US,
        "values": values,
    }

    r = requests.post(
        f"{BASE_URL}/api/arduino/batch",
        json=payload,
    )

    print(
        "Sent",
        len(values),
        "samples",
        r.status_code,
    )

    time.sleep(0.1)
