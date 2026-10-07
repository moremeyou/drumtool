import asyncio


class EventBroker:
    """Event-loop-only fanout. Slow browsers lose oldest UI events, never block MIDI."""

    def __init__(self):
        self.clients: set[asyncio.Queue] = set()
        self.dropped = 0

    def subscribe(self):
        queue = asyncio.Queue(maxsize=256)
        self.clients.add(queue)
        return queue

    def unsubscribe(self, queue):
        self.clients.discard(queue)

    def publish(self, event):
        for queue in tuple(self.clients):
            if queue.full():
                queue.get_nowait()
                self.dropped += 1
            queue.put_nowait(event)
