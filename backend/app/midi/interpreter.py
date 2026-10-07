import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import mido

from app.models.hit import Classification, HitClassifier, HitEvent

log = logging.getLogger(__name__)


@dataclass
class ChannelState:
    position: tuple[int, float] | None = None
    prefix: tuple[int, float] | None = None


class MidiInterpreter:
    """Called serially by the engine; controller freshness uses monotonic receipt time."""

    def __init__(self, mapping: dict, classifier: HitClassifier | None = None):
        self.mapping = mapping
        self.classifier = classifier
        self.window = mapping['correlation_window_ms'] / 1000
        self.states: dict[int, ChannelState] = {}
        self.sequence = 0

    def reset(self):
        self.states.clear()

    def process(self, message: mido.Message, *, device: str, now: float,
                timestamp: str | None = None) -> HitEvent | None:
        log.debug('raw_midi', extra={'data': {'message': message.dict(), 'device': device}})
        if not hasattr(message, 'channel'):
            return None
        state = self.states.setdefault(message.channel, ChannelState())
        if message.type == 'control_change':
            if message.control == 16:
                state.position = (message.value, now)
            elif message.control == 88:
                state.prefix = (message.value, now)
            if message.control in (16, 88):
                log.debug('controller_received', extra={'data': {
                    'channel': message.channel + 1, 'controller': message.control, 'value': message.value}})
            return None
        if message.type != 'note_on' or message.velocity == 0:
            return None

        def fresh(value):
            return value[0] if value is not None and 0 <= now - value[1] <= self.window else None

        position, prefix = fresh(state.position), fresh(state.prefix)
        # Each positive Note On consumes the preceding channel-local controller pair,
        # even for an unmapped note. Note Off/zero-velocity Note On never creates a hit.
        state.position = state.prefix = None
        channel = message.channel + 1
        articulation = (self.mapping['articulations'].get(str(message.note), 'unknown')
                        if channel == self.mapping['channel'] else 'unknown')
        result = (self.classifier.classify_hit(position, message.velocity)
                  if self.classifier and articulation == 'head' else Classification())
        self.sequence += 1
        pitch = ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')[message.note % 12]
        octave = message.note // 12 + self.mapping.get('note_name_octave_offset', -2)
        event = HitEvent(self.sequence, timestamp or datetime.now(timezone.utc).isoformat(),
                         device, channel, message.note, f'{pitch}{octave}', articulation,
                         message.velocity, position, prefix, result.ring, result.confidence)
        log.debug('classifier_result', extra={'data': {'ring': result.ring, 'confidence': result.confidence}})
        log.debug('hit_generated', extra={'data': event.to_dict()})
        return event
