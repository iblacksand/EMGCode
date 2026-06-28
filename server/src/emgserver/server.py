import logging
import uuid
from typing import Optional

import uvicorn
from fastapi import (
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlmodel import select

from .data import (
    ArduinoSession,
    FlexEvent,
    MeasurementBatch,
    SessionDep,
    create_db_and_tables,
)
from .state import EMGState

MAX_BATCH_SIZE = 50_000

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

emg_state = EMGState()


class UpdateSettingsRequest(BaseModel):
    normal_peak_min: Optional[float] = Field(None)
    normal_peak_max: Optional[float] = Field(None)
    recovery_improvement: Optional[float] = Field(None)


class ArduinoBatchRequest(BaseModel):
    session: str
    start_micros: int
    sample_period_us: int
    values: list[int]


class CalibrationRequest(BaseModel):
    session: str
    calibration_values: list[float]


class FlexEventRequest(BaseModel):
    session: str
    timestamp_micros: int
    peak_value: float
    quality: str
    batch_id: Optional[int] = None


class SettingsResponse(BaseModel):
    normal_peak_min: float
    normal_peak_max: float
    good_threshold_multiplier: float
    poor_threshold_multiplier: float


app = FastAPI()

receivers: set[WebSocket] = set()


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/api/hello")
def hello():
    return {"message": "Hello from FastAPI"}


@app.get("/api/arduino/new_session")
def new_session(
    session: SessionDep,
) -> dict[str, str]:
    session_id = str(uuid.uuid4())

    db_session = ArduinoSession(session_id=session_id, created_datetime=None)

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
        "session_id": session_id,
        "created_datetime": arduino_session.created_datetime.isoformat()
        if arduino_session.created_datetime
        else None,
        "batch_count": len(batches),
        "sample_count": total_samples,
        "batches": [
            {
                "id": b.id,
                "start_micros": b.start_micros,
                "sample_period_us": b.sample_period_us,
                "sample_count": len(b.values),
            }
            for b in batches
        ],
    }


@app.get("/api/list_sessions")
def list_sessions(session: SessionDep):
    all_sessions = session.exec(select(ArduinoSession)).all()
    if not all_sessions:
        return []
    result = []
    for s in all_sessions:
        batches = session.exec(
            select(MeasurementBatch).where(MeasurementBatch.session_id == s.session_id)
        ).all()
        total_samples = sum(len(b.values) for b in batches)
        result.append(
            {
                "session_id": s.session_id,
                "created_datetime": s.created_datetime.isoformat()
                if s.created_datetime
                else None,
                "batch_count": len(batches),
                "sample_count": total_samples,
                "calibrated": s.calibrated,
                "calibration_normal_peak": s.calibration_normal_peak,
                "good_flex_count": s.good_flex_count,
                "normal_flex_count": s.normal_flex_count,
                "poor_flex_count": s.poor_flex_count,
            }
        )
    return result


@app.post("/api/arduino/calibrate")
def calibrate_session(req: CalibrationRequest, session: SessionDep):
    arduino_session = session.exec(
        select(ArduinoSession).where(ArduinoSession.session_id == req.session)
    ).first()

    if arduino_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if len(req.calibration_values) < 3:
        raise HTTPException(
            status_code=400, detail="Need at least 3 calibration flexes"
        )

    avg_peak = sum(req.calibration_values) / len(req.calibration_values)

    arduino_session.calibrated = True
    arduino_session.calibration_normal_peak = avg_peak

    session.add(arduino_session)
    session.commit()
    session.refresh(arduino_session)

    logger.info("Calibrated session %s with normal peak %.2f", req.session, avg_peak)

    return {
        "success": True,
        "normal_peak": avg_peak,
        "calibration_values": req.calibration_values,
    }


@app.post("/api/arduino/flex_event")
def record_flex_event(req: FlexEventRequest, session: SessionDep):
    arduino_session = session.exec(
        select(ArduinoSession).where(ArduinoSession.session_id == req.session)
    ).first()

    if arduino_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    flex_event = FlexEvent(
        session_id=req.session,
        timestamp_micros=req.timestamp_micros,
        peak_value=req.peak_value,
        quality=req.quality,
        batch_id=req.batch_id,
    )

    if req.quality == "good":
        arduino_session.good_flex_count += 1
    elif req.quality == "normal":
        arduino_session.normal_flex_count += 1
    elif req.quality == "poor":
        arduino_session.poor_flex_count += 1

    session.add(flex_event)
    session.add(arduino_session)
    session.commit()

    return {"success": True, "flex_id": flex_event.id}


@app.get("/api/arduino/session/{session_id}/flexes")
def get_session_flexes(session_id: str, session: SessionDep):
    flex_events = session.exec(
        select(FlexEvent).where(FlexEvent.session_id == session_id)
    ).all()

    return [
        {
            "id": f.id,
            "timestamp_micros": f.timestamp_micros,
            "peak_value": f.peak_value,
            "quality": f.quality,
            "batch_id": f.batch_id,
        }
        for f in flex_events
    ]


@app.get("/api/settings")
def get_settings():
    normal_min, normal_max = emg_state.settings.normal_peak
    return {
        "normal_peak_min": normal_min,
        "normal_peak_max": normal_max,
        "good_threshold_multiplier": 1.0 + emg_state.settings.recovery_improvement,
        "poor_threshold_multiplier": 0.7,
    }


@app.get("/api/current_session")
def get_current_session(session: SessionDep):
    latest_session = session.exec(
        select(ArduinoSession).order_by(ArduinoSession.created_datetime.desc())
    ).first()
    
    if latest_session is None:
        return None
    
    return {
        "session_id": latest_session.session_id,
        "calibrated": latest_session.calibrated,
        "calibration_normal_peak": latest_session.calibration_normal_peak,
        "good_flex_count": latest_session.good_flex_count,
        "normal_flex_count": latest_session.normal_flex_count,
        "poor_flex_count": latest_session.poor_flex_count,
    }


@app.get("/api/list_batches")
def list_batches(session: SessionDep):
    all_sessions = session.exec(select(MeasurementBatch)).all()
    if all_sessions is None:
        raise HTTPException(
            status_code=404,
            detail="No sessions not found",
        )
    return [s.model_dump(mode="json") for s in all_sessions]


@app.get("/api/arduino/get_recovery_percent")
async def get_recovery_percent() -> float:
    return emg_state.settings.recovery_improvement


@app.post("/api/update_settings")
async def update_settings(req: UpdateSettingsRequest) -> bool:
    (cur_min, cur_max) = emg_state.settings.normal_peak
    if req.normal_peak_min is not None:
        cur_min = req.normal_peak_min
    if req.normal_peak_max is not None:
        cur_max = req.normal_peak_max
    emg_state.settings.normal_peak = (cur_min, cur_max)
    if req.recovery_improvement is not None:
        emg_state.settings.recovery_improvement = req.recovery_improvement
    return True


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


def start():
    uvicorn.run("emgserver.server:app", host="0.0.0.0", port=8000, reload=True)
