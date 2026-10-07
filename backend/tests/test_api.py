import mido
from fastapi.testclient import TestClient

from app.main import create_app


class FakePort:
    closed = False

    def close(self):
        self.closed = True


class FakeBackend:
    def __init__(self):
        self.names = ['TD-50X']
        self.callback = None

    def get_input_names(self):
        return self.names

    def open_input(self, name, callback):
        self.callback = callback
        return FakePort()


def test_raw_websocket_and_browser_independent_capture():
    backend = FakeBackend()
    app = create_app(backend)
    with TestClient(app) as client:
        assert client.get('/api/status').json()['connected']
        assert client.get('/api/midi/devices').json()['devices'] == ['TD-50X']
        # The real production callback path captures with no browser connected.
        backend.callback(mido.Message('control_change', channel=9, control=16, value=85))
        backend.callback(mido.Message('control_change', channel=9, control=88, value=64))
        backend.callback(mido.Message('note_on', channel=9, note=38, velocity=67))
        with client.websocket_connect('/ws/events') as ws:
            snapshot = ws.receive_json()
            hits = snapshot['hits']
            while not hits:
                event = ws.receive_json()
                if event['type'] == 'hit':
                    hits = [event['hit']]
            assert hits[0]['position_cc16'] == 85
            assert hits[0]['velocity_prefix_cc88'] == 64
            assert hits[0]['velocity'] == 67
        assert client.get('/api/status').json()['hits_received'] == 1


def test_disconnect_and_reconnect():
    backend = FakeBackend()
    app = create_app(backend)
    with TestClient(app) as client:
        old_callback = backend.callback
        backend.names = []
        with client.websocket_connect('/ws/events') as ws:
            ws.receive_json()
            while True:
                event = ws.receive_json()
                if event['type'] == 'status' and not event['status']['connected']:
                    break
        assert not client.get('/api/status').json()['connected']
        assert client.post('/api/midi/connect', json={'device': 'TD-50X'}).status_code == 503
        backend.names = ['TD-50X']
        assert client.post('/api/midi/connect', json={'device': 'TD-50X'}).json()['connected']
        old_callback(mido.Message('note_on', note=38, velocity=90))
        assert client.get('/api/status').json()['hits_received'] == 0
