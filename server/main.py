from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlmodel import select
from data import ArduinoSession, SessionDep, create_db_and_tables, get_session
import uuid


class ArduinoBatchRequest(BaseModel):
    session: str
    start_micros: int
    sample_period_us: int
    values: list[int]


app = FastAPI()
receivers: set[WebSocket] = set()
current_session = None


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/api/hello")
def hello():
    return {"message": "Hello from FastAPI"}


@app.post("/api/arduino/batch")
def arduino_batch(req: ArduinoBatchRequest, session: SessionDep) -> None:
    global current_session
    arduino_session = None
    if current_session == req.session:
        arduino_session = session.exec(
            select(ArduinoSession).where(ArduinoSession.session_id == req.session)
        ).first()
    if arduino_session is None:
        current_session = req.session
        arduino_session = ArduinoSession(session_id=req.session, measurements=[])
    arduino_session.measurements.extend(req.values)
    session.add(arduino_session)
    session.commit()


@app.get("/api/arduino/single/{value}")
async def arduino_value(value: int) -> None:
    try:
        dead = []
        for receiver in receivers:
            try:
                await receiver.send_text(str(value))
            except Exception:
                dead.append(receiver)

        for receiver in dead:
            receivers.discard(receiver)
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/receive")
async def receive_channel(ws: WebSocket):
    await ws.accept()
    receivers.add(ws)

    try:
        while True:
            _ = await ws.receive_text()  # keep connection alive
    except WebSocketDisconnect:
        receivers.discard(ws)


@app.websocket("/ws/send")
async def send_channel(ws: WebSocket):
    await ws.accept()

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
        pass


@app.post("/api/arduino/new_session")
def new_session() -> dict[str, str]:
    global current_session
    current_session = str(uuid.uuid4())
    return {"session": current_session}


app.mount("/", StaticFiles(directory="build", html=True), name="static")
