"""State management for the EMG sensor."""

from enum import Enum, auto

from pydantic import BaseModel


class EMGStage(Enum):
    NEEDS_CALIBRATION = auto()
    CALIBRATING = auto()
    CALIBRATED = auto()

    def __str__(self) -> str:
        match self:
            case EMGStage.NEEDS_CALIBRATION:
                return "needs_calibration"
            case EMGStage.CALIBRATING:
                return "calibrating"
            case EMGStage.CALIBRATED:
                return "calibrated"


class NumericRange:
    a: int | float
    b: int | float

    def __init__(self, a: int | float, b: int | float) -> None:
        if a > b:
            self.a = b
            self.b = a
        else:
            self.a = a
            self.b = b

    def in_range(self, x: int | float) -> bool:
        return x >= self.a and x <= self.b

    def clamp(self, x: int | float) -> int | float:
        return min(max(self.a, x), self.b)

    @staticmethod
    def from_tuple(x: tuple[float, float]) -> "NumericRange":
        (a, b) = x
        return NumericRange(a, b)


class EMGSettings(BaseModel):
    recovery_improvement: float = 0.2
    normal_peak: tuple[float, float] = (100, 300)


class EMGState:
    settings: EMGSettings
    stage: EMGStage

    def __init__(self, settings: EMGSettings | None = None) -> None:
        self.settings = settings if settings is not None else EMGSettings()
        self.stage = EMGStage.NEEDS_CALIBRATION

    def state_as_text(self) -> str:
        return str(self.stage)
