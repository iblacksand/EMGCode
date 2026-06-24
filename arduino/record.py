# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pyserial>=3.5",
# ]
# ///
import csv
from datetime import datetime

import serial

PORT = "/dev/tty.usbmodemACA7043BDEEC2"  # Replace with your Arduino port
BAUD = 115200

ser = serial.Serial(PORT, BAUD)

filename = f"a0_log_{datetime.now():%Y%m%d_%H%M%S}.csv"

with open(filename, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["datetime", "arduino_millis", "voltage"])

    while True:
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        if not line or line.startswith("millis"):
            continue

        try:
            millis, voltage = line.split(",")

            writer.writerow([datetime.now().isoformat(), millis, voltage])

            f.flush()

            print(millis, voltage)

        except ValueError:
            pass
