from datetime import datetime
from typing import Annotated, Optional

from fastapi import Depends
from sqlalchemy.types import JSON
from sqlmodel import (
    TIMESTAMP,
    Column,
    Field,
    Relationship,
    Session,
    SQLModel,
    create_engine,
    text,
)


class ArduinoSession(SQLModel, table=True):
    session_id: str = Field(primary_key=True)
    created_datetime: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )

    calibrated: bool = Field(default=False)
    calibration_peaks: list[float] = Field(default=[], sa_column=Column(JSON))
    calibration_normal_peak: Optional[float] = Field(default=None)
    good_flex_count: int = Field(default=0)
    normal_flex_count: int = Field(default=0)
    poor_flex_count: int = Field(default=0)

    measurement_batches: list["MeasurementBatch"] = Relationship(
        back_populates="arduino_session"
    )
    flex_events: list["FlexEvent"] = Relationship(back_populates="arduino_session")


class MeasurementBatch(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str | None = Field(
        default=None, foreign_key="arduinosession.session_id"
    )

    arduino_session: list[ArduinoSession] = Relationship(
        back_populates="measurement_batches"
    )

    start_micros: int
    sample_period_us: int

    values: list[int] = Field(sa_column=Column(JSON))


class FlexEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str | None = Field(
        default=None, foreign_key="arduinosession.session_id"
    )

    arduino_session: list[ArduinoSession] = Relationship(back_populates="flex_events")

    timestamp_micros: int
    peak_value: float
    quality: str  # "good", "normal", "poor"
    batch_id: Optional[int] = Field(default=None, foreign_key="measurementbatch.id")


sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}

engine = create_engine(
    sqlite_url,
    connect_args=connect_args,
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[
    Session,
    Depends(get_session),
]
