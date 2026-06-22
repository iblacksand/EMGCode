from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from data import create_db_and_tables
import uuid


class ArduinoBatchRequest(BaseModel):
    session: str
    start_micros: int
    sample_period_us: int
    values: list[int]


app = FastAPI()
receivers: set[WebSocket] = set()


@app.on("startup")
def on_startup():
    create_db_and_tables()


@app.get("/api/hello")
def hello():
    return {"message": "Hello from FastAPI"}


@app.post("/api/arduino/batch")
def arduino_batch(req: ArduinoBatchRequest) -> None:
    pass


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
def new_session():
    return {"session": str(uuid.uuid4())}


app.mount("/", StaticFiles(directory="build", html=True), name="static")
