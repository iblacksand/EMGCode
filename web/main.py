from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

app = FastAPI()
receivers: set[WebSocket] = set()


@app.get("/api/hello")
def hello():
    return {"message": "Hello from FastAPI"}


@app.get("/api/arduino/{value}")
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
            await ws.receive_text()  # keep connection alive
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


app.mount("/", StaticFiles(directory="build", html=True), name="static")
