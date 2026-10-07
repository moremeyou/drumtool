import json
from pathlib import Path

import mido
import pytest

from app.midi.interpreter import MidiInterpreter


@pytest.fixture
def interpreter():
    mapping = json.loads((Path(__file__).parents[1] / 'app/midi/mapping.json').read_text())
    return MidiInterpreter(mapping)


def cc(interpreter, control, value, now=1, channel=9):
    return interpreter.process(mido.Message('control_change', channel=channel, control=control, value=value), device='TD-50X', now=now)


def note(interpreter, velocity=67, now=1.002, channel=9, pitch=38):
    return interpreter.process(mido.Message('note_on', channel=channel, note=pitch, velocity=velocity), device='TD-50X', now=now)


def test_normal_head(interpreter):
    cc(interpreter, 16, 85)
    cc(interpreter, 88, 64)
    hit = note(interpreter)
    assert (hit.position_cc16, hit.velocity_prefix_cc88, hit.velocity) == (85, 64, 67)
    assert (hit.note, hit.note_name, hit.channel, hit.articulation) == (38, 'D1', 10, 'head')


def test_missing_controller(interpreter):
    hit = note(interpreter)
    assert hit.position_cc16 is None
    assert hit.estimated_ring == 'UNKNOWN'


def test_rapid_hits_consume_each_pair(interpreter):
    for index in range(1000):
        now = 1 + index * .005
        cc(interpreter, 16, index % 128, now)
        cc(interpreter, 88, (index + 1) % 128, now)
        hit = note(interpreter, now=now + .001)
        assert (hit.position_cc16, hit.velocity_prefix_cc88) == (index % 128, (index + 1) % 128)
    assert note(interpreter, now=6.01).position_cc16 is None


def test_stale_controllers(interpreter):
    cc(interpreter, 16, 85)
    cc(interpreter, 88, 64)
    hit = note(interpreter, now=1.1)
    assert hit.position_cc16 is None and hit.velocity_prefix_cc88 is None


def test_channels_are_isolated(interpreter):
    cc(interpreter, 16, 85, channel=8)
    assert note(interpreter).position_cc16 is None
    assert note(interpreter, channel=8).position_cc16 == 85


def test_non_snare_and_note_off(interpreter):
    assert note(interpreter, pitch=36).articulation == 'unknown'
    assert note(interpreter, velocity=0) is None
    assert interpreter.process(mido.Message('note_off', note=38), device='TD-50X', now=2) is None


def test_freshness_is_independent_and_zero_preserved(interpreter):
    cc(interpreter, 16, 0, now=1)
    cc(interpreter, 88, 0, now=1.05)
    hit = note(interpreter, now=1.051)
    assert hit.position_cc16 is None and hit.velocity_prefix_cc88 == 0


def test_unmapped_note_consumes_controllers(interpreter):
    cc(interpreter, 16, 85)
    assert note(interpreter, pitch=36).position_cc16 == 85
    assert note(interpreter).position_cc16 is None
