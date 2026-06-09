# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "numpy>=2.4.6",
#     "wfdb>=4.3.1",
# ]
# ///
import numpy as np
import wfdb

record = wfdb.rdrecord("session1_participant13_gesture10_trial1")  # no extension

signal = record.p_signal  # already scaled to physical units
fs = record.fs

with open("out.txt", "w") as f:
    for i, val in enumerate(signal[:, 0]):
        t = i / fs
        f.write(f"{t:.6f} {val}\n")
