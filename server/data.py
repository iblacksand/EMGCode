from typing import Annotated, Optional

from fastapi import Depends
from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, Session, SQLModel, create_engine


class ArduinoSession(SQLModel, table=True):
    session_id: str = Field(primary_key=True)


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
