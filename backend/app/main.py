import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.api.broker import EventBroker
from app.midi.engine import MidiEngine
from app.midi.interpreter import MidiInterpreter

ROOT = Path(__file__).resolve().parents[1]


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {'level': record.levelname, 'event': record.getMessage(),
                   'logger': record.name, 'data': getattr(record, 'data', {})}
        if record.exc_info:
            payload['exception'] = self.formatException(record.exc_info)
        return json.dumps(payload)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.getLogger('app').addHandler(handler)
logging.getLogger('app').setLevel(logging.DEBUG if os.getenv('MIDI_DEBUG') == '1' else logging.INFO)
logging.getLogger('app').propagate = False


def create_app(backend=None):
    mapping = json.loads((ROOT / 'app/midi/mapping.json').read_text())
    broker = EventBroker()
    engine = MidiEngine(MidiInterpreter(mapping), broker, backend)

    @asynccontextmanager
    async def lifespan(app):
        await engine.start()
        yield
        await engine.stop()

    app = FastAPI(title='TD-50X MIDI Interface', version='0.1.0', lifespan=lifespan)
    app.state.engine = engine

    @app.get('/api/status')
    async def status():
        return engine.status()

    @app.get('/api/midi/devices')
    async def devices():
        try:
            return {'devices': engine.devices()}
        except Exception as exc:
            raise HTTPException(503, detail=str(exc)) from exc

    @app.post('/api/midi/connect')
    async def connect(request: ConnectRequest):
        try:
            engine.connect(request.device)
        except Exception as exc:
            raise HTTPException(503, detail=str(exc)) from exc
        return engine.status()

    @app.websocket('/ws/events')
    async def events(websocket: WebSocket):
        # Local browser origins only. No remote service or CORS dependency.
        origin = websocket.headers.get('origin')
        if origin and origin not in {'http://localhost:5173', 'http://127.0.0.1:5173'}:
            await websocket.close(code=1008)
            return
        await websocket.accept()
        queue = broker.subscribe()
        try:
            await websocket.send_json({'type': 'snapshot', 'status': engine.status(), 'hits': list(engine.history)})

            async def send():
                while True:
                    await websocket.send_json(await queue.get())

            async def receive():
                while True:
                    await websocket.receive_text()

            tasks = [asyncio.create_task(send()), asyncio.create_task(receive())]
            try:
                done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    task.result()
            finally:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
        except (WebSocketDisconnect, RuntimeError, asyncio.CancelledError):
            pass
        finally:
            broker.unsubscribe(queue)

    return app


class ConnectRequest(BaseModel):
    device: str


app = create_app()
