import logging
import uuid

from fastapi import (
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlmodel import select

from data import (
    ArduinoSession,
    MeasurementBatch,
    SessionDep,
    create_db_and_tables,
)

MAX_BATCH_SIZE = 50_000

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ArduinoBatchRequest(BaseModel):
    session: str
    start_micros: int
    sample_period_us: int
    values: list[int]


app = FastAPI()

receivers: set[WebSocket] = set()


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/api/hello")
def hello():
    return {"message": "Hello from FastAPI"}


@app.post("/api/arduino/new_session")
def new_session(
    session: SessionDep,
) -> dict[str, str]:
    session_id = str(uuid.uuid4())

    db_session = ArduinoSession(session_id=session_id)

    session.add(db_session)
    session.commit()

    logger.info(
        "Created session %s",
        session_id,
    )

    return {
        "session": session_id,
    }


@app.post("/api/arduino/batch")
def arduino_batch(
    req: ArduinoBatchRequest,
    session: SessionDep,
):
    if len(req.values) == 0:
        raise HTTPException(
            status_code=400,
            detail="Empty batch",
        )

    if len(req.values) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Batch too large",
        )

    arduino_session = session.exec(
        select(ArduinoSession).where(ArduinoSession.session_id == req.session)
    ).first()

    if arduino_session is None:
        raise HTTPException(
            status_code=404,
            detail="Unknown session",
        )

    batch = MeasurementBatch(
        session_id=req.session,
        start_micros=req.start_micros,
        sample_period_us=req.sample_period_us,
        values=req.values,
    )

    session.add(batch)
    session.commit()
    session.refresh(batch)

    logger.info(
        "Session=%s Batch=%s Samples=%d StartMicros=%d",
        req.session,
        batch.id,
        len(req.values),
        req.start_micros,
    )

    return {
        "success": True,
        "batch_id": batch.id,
        "samples": len(req.values),
    }


@app.get("/api/arduino/session/{session_id}")
def session_summary(
    session_id: str,
    session: SessionDep,
):
    arduino_session = session.exec(
        select(ArduinoSession).where(ArduinoSession.session_id == session_id)
    ).first()

    if arduino_session is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )

    batches = session.exec(
        select(MeasurementBatch).where(MeasurementBatch.session_id == session_id)
    ).all()

    total_samples = sum(len(batch.values) for batch in batches)

    return {
        "session": session_id,
        "batch_count": len(batches),
        "sample_count": total_samples,
    }


@app.get("/api/list_sessions")
def list_sessions(session: SessionDep):
    all_sessions = session.exec(select(ArduinoSession)).all()
    if all_sessions is None:
        raise HTTPException(
            status_code=404,
            detail="No sessions not found",
        )
    return [s.model_dump(mode="json") for s in all_sessions]


@app.get("/api/list_batches")
def list_batches(session: SessionDep):
    all_sessions = session.exec(select(MeasurementBatch)).all()
    if all_sessions is None:
        raise HTTPException(
            status_code=404,
            detail="No sessions not found",
        )
    return [s.model_dump(mode="json") for s in all_sessions]


@app.get("/api/arduino/session/{session_id}/data")
def session_data(
    session_id: str,
    session: SessionDep,
):
    arduino_session = session.exec(
        select(ArduinoSession).where(ArduinoSession.session_id == session_id)
    ).first()

    if arduino_session is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )

    batches = session.exec(
        select(MeasurementBatch).where(MeasurementBatch.session_id == session_id)
    ).all()

    return [
        {
            "batch_id": batch.id,
            "start_micros": batch.start_micros,
            "sample_period_us": batch.sample_period_us,
            "values": batch.values,
        }
        for batch in batches
    ]


@app.get("/api/arduino/single/{value}")
async def arduino_value(value: int):
    dead = []

    for receiver in receivers:
        try:
            await receiver.send_text(str(value))
        except Exception:
            dead.append(receiver)

    for receiver in dead:
        receivers.discard(receiver)

    return {"sent_to": len(receivers)}


@app.websocket("/ws/receive")
async def receive_channel(ws: WebSocket):
    await ws.accept()
    receivers.add(ws)

    logger.info(
        "Receiver connected. Total receivers=%d",
        len(receivers),
    )

    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        receivers.discard(ws)

        logger.info(
            "Receiver disconnected. Total receivers=%d",
            len(receivers),
        )


@app.websocket("/ws/send")
async def send_channel(ws: WebSocket):
    await ws.accept()

    logger.info("Sender connected")

    try:
        while True:
            value = await ws.receive_text()

            dead = []

            for receiver in receivers:
                try:
                    await receiver.send_text(value)
                except Exception:
                    dead.append(receiver)

            for receiver in dead:
                receivers.discard(receiver)

    except WebSocketDisconnect:
        logger.info("Sender disconnected")


app.mount(
    "/",
    StaticFiles(
        directory="build",
        html=True,
    ),
    name="static",
)
