from datetime import datetime
from typing import Annotated, Optional

from fastapi import Depends
from sqlalchemy.types import JSON
from sqlmodel import TIMESTAMP, Column, Field, Session, SQLModel, create_engine, text


class ArduinoSession(SQLModel, table=True):
    session_id: str = Field(primary_key=True)
    created_datetime: Optional[datetime] = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )


class MeasurementBatch(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    session_id: str = Field(index=True)

    start_micros: int
    sample_period_us: int

    values: list[int] = Field(sa_column=Column(JSON))


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
