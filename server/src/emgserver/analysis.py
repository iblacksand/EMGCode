"""Analysis related functions.

1. Bad signal recognition
    - Not enough variability?

"""

# from collections import
from collections import Counter

from emgserver.data import FlexEvent

MIN_HEIGHT = 100
MIN_GAP_MS = 30
MIN_PEAK_DURATION_MS = 400  # 250 ms
MIN_PEAK_PERCENTAGE = 0.85


def classify_value(value: float, bad: float, normal: float, high: float) -> str:
    if value >= high:
        return "good"
    elif value >= normal:
        return "normal"
    elif value >= bad:
        return "poor"
    return "none"


def classify_peaks(
    data: list[tuple[int, float]],
    ranges: tuple[float, float, float],
    session: str,
    batch_id: int,
) -> list[FlexEvent]:
    """
    Parameters
    ----------
    data
        List of (timestamp_micros, value)
    ranges
        (bad_threshold, normal_threshold, good_threshold)
    """

    bad, normal, high = ranges

    flexes: list[FlexEvent] = []

    current_peak: list[tuple[int, float]] = []
    inside_peak = False
    below_start = None

    def finalize_peak(peak: list[tuple[int, float]]) -> None:
        if not peak:
            return

        # Duration
        duration_ms = (peak[-1][0] - peak[0][0]) / 1000.0

        if duration_ms < MIN_PEAK_DURATION_MS:
            return

        counts = Counter()
        peak_max = float("-inf")
        peak_time = peak[0][0]

        for timestamp, value in peak:
            category = classify_value(value, bad, normal, high)

            if category != "none":
                counts[category] += 1

            if value > peak_max:
                peak_max = value
                peak_time = timestamp

        if not counts:
            return

        quality, count = counts.most_common(1)[0]

        total = sum(counts.values())

        if count / total < MIN_PEAK_PERCENTAGE:
            return

        flexes.append(
            FlexEvent(
                session_id=session,
                timestamp_micros=peak_time,
                peak_value=peak_max,
                quality=quality,
                batch_id=batch_id,
            )
        )

    for timestamp, value in data:
        if value >= MIN_HEIGHT:
            if not inside_peak:
                inside_peak = True
                current_peak = []

            current_peak.append((timestamp, value))
            below_start = None

        elif inside_peak:
            current_peak.append((timestamp, value))

            if below_start is None:
                below_start = timestamp

            elif (timestamp - below_start) / 1000.0 >= MIN_GAP_MS:
                while current_peak and current_peak[-1][1] < MIN_HEIGHT:
                    current_peak.pop()

                finalize_peak(current_peak)

                current_peak = []
                inside_peak = False
                below_start = None

    # Handle peak reaching end of recording
    if inside_peak:
        while current_peak and current_peak[-1][1] < MIN_HEIGHT:
            current_peak.pop()

        finalize_peak(current_peak)

    return flexes
