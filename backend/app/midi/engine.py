import asyncio
import logging
import queue
import threading
import time
from collections import deque
from contextlib import suppress

import mido

from app.api.broker import EventBroker
from app.midi.interpreter import MidiInterpreter

log = logging.getLogger(__name__)


class MidiEngine:
    def __init__(self, interpreter: MidiInterpreter, broker: EventBroker, backend=None):
        self.interpreter = interpreter
        self.broker = broker
        self.backend = backend or mido.Backend('mido.backends.rtmidi')
        self.port = None
        self.device = None
        self.error = None
        self.pending = queue.Queue(maxsize=2048)
        self.history = deque(maxlen=50)
        self.lock = threading.Lock()
        self.generation = 0
        self.hits = 0
        self.dropped = 0
        self.tasks = []

    def devices(self):
        return self.backend.get_input_names()

    def status(self):
        return {'connected': self.port is not None, 'device': self.device,
                'error': self.error, 'hits_received': self.hits,
                'capture_queue_dropped': self.dropped, 'browser_events_dropped': self.broker.dropped}

    def announce(self):
        self.broker.publish({'type': 'status', 'status': self.status()})

    def disconnect(self, reason=None):
        with self.lock:
            self.generation += 1
            self.interpreter.reset()
            old_port, self.port = self.port, None
        # Closing may wait for the native callback: never hold its lock here.
        if old_port is not None:
            with suppress(Exception):
                old_port.close()
        self.error = reason
        log.info('midi_disconnected', extra={'data': {'device': self.device, 'reason': reason}})
        self.announce()

    def connect(self, name):
        if name not in self.devices():
            raise ValueError('MIDI input is unavailable. Refresh the device list and reconnect.')
        self.disconnect()
        self.device = name
        generation = self.generation

        def callback(message):
            received = time.monotonic()
            with self.lock:
                if generation != self.generation:
                    return
                try:
                    hit = self.interpreter.process(message, device=name, now=received)
                    if hit is None:
                        return
                    self.hits += 1
                    try:
                        self.pending.put_nowait(hit)
                    except queue.Full:
                        with suppress(queue.Empty):
                            self.pending.get_nowait()
                        self.dropped += 1
                        self.pending.put_nowait(hit)
                except Exception:
                    log.exception('midi_callback_failed')
        try:
            self.port = self.backend.open_input(name, callback=callback)
            self.error = None
            log.info('midi_connected', extra={'data': {'device': name}})
        except Exception as exc:
            self.disconnect(str(exc))
            raise
        finally:
            self.announce()

    async def start(self):
        try:
            devices = self.devices()
            preferred = next((name for name in devices if 'TD-50X' in name.upper()), None)
            if preferred:
                self.connect(preferred)
        except Exception as exc:
            self.error = str(exc)
            log.warning('midi_startup_unavailable', extra={'data': {'error': self.error}})
        self.tasks = [asyncio.create_task(self._drain()), asyncio.create_task(self._monitor())]

    async def stop(self):
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.disconnect()

    async def _drain(self):
        while True:
            for _ in range(256):
                try:
                    hit = self.pending.get_nowait()
                except queue.Empty:
                    break
                event = hit.to_dict()
                self.history.appendleft(event)
                self.broker.publish({'type': 'hit', 'hit': event})
            await asyncio.sleep(0.005)

    async def _monitor(self):
        while True:
            await asyncio.sleep(1)
            if self.port is not None:
                try:
                    if self.port.closed or self.device not in self.devices():
                        self.disconnect('MIDI device disconnected. Refresh sources and reconnect.')
                except Exception as exc:
                    self.disconnect(str(exc))
            self.announce()
