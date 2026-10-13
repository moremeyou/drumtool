import json
from pathlib import Path

import mido
import pytest

from app.classifier.knn import KNNClassifier
from app.midi.interpreter import MidiInterpreter

ROOT = Path(__file__).parents[1]


@pytest.fixture
def classifier():
    return KNNClassifier(json.loads((ROOT / 'calibration/pd140ds_default.json').read_text()))


def test_center_and_outer_anchors(classifier):
    assert classifier.classify_hit(0, 63).ring == 'CENTER'
    assert classifier.classify_hit(127, 44).ring == 'OUTER'


@pytest.mark.parametrize('position,velocity', [(None, 60), (-1, 60), (128, 60), (0, 128), (True, 60)])
def test_missing_or_invalid_features_are_unknown(classifier, position, velocity):
    result = classifier.classify_hit(position, velocity)
    assert result.ring == 'UNKNOWN'
    assert result.confidence == 0


def test_overlapping_labels_have_reduced_confidence():
    samples = [
        {'ring': ring, 'position_cc16': 60, 'velocity': 50}
        for ring in ['INNER', 'INNER', 'INNER', 'MIDDLE', 'MIDDLE']
    ]
    result = KNNClassifier({'k': 5, 'samples': samples}).classify_hit(60, 50)
    assert result.ring == 'INNER'
    assert result.confidence == pytest.approx(.6)


def test_velocity_can_change_label_at_same_position():
    classifier = KNNClassifier({'k': 1, 'samples': [
        {'ring': 'INNER', 'position_cc16': 50, 'velocity': 30},
        {'ring': 'MIDDLE', 'position_cc16': 50, 'velocity': 90},
    ]})
    assert classifier.classify_hit(50, 30).ring == 'INNER'
    assert classifier.classify_hit(50, 90).ring == 'MIDDLE'


def test_zero_velocity_weight_keeps_location_and_confidence_stable_across_strengths():
    classifier = KNNClassifier({'k': 1, 'feature_weights': {'position_cc16': 1, 'velocity': 0},
        'samples': [
            {'ring': 'INNER', 'position_cc16': 40, 'velocity': 110},
            {'ring': 'MIDDLE', 'position_cc16': 100, 'velocity': 20},
        ]})
    for position, expected in [(42, 'INNER'), (98, 'MIDDLE')]:
        results = [classifier.classify_hit(position, velocity) for velocity in range(1, 128)]
        assert all(result == results[0] for result in results)
        assert results[0].ring == expected


def test_default_profile_center_does_not_depend_on_strength(classifier):
    results = [classifier.classify_hit(0, velocity) for velocity in range(1, 128)]
    assert all(result == results[0] for result in results)
    assert results[0].ring == 'CENTER'


@pytest.mark.parametrize('weights', [None, {}, {'position_cc16': 1},
    {'position_cc16': 0, 'velocity': 0}, {'position_cc16': 1, 'velocity': -1},
    {'position_cc16': 1, 'velocity': float('nan')},
    {'position_cc16': float('inf'), 'velocity': 0},
    {'position_cc16': True, 'velocity': 0}, {'position_cc16': 1, 'velocity': '0'}])
def test_invalid_feature_weights_fail_clearly(weights):
    with pytest.raises(ValueError):
        KNNClassifier({'k': 1, 'feature_weights': weights, 'samples': [
            {'ring': 'CENTER', 'position_cc16': 0, 'velocity': 60}]})


def test_distance_reduces_confidence_without_threshold_bands():
    classifier = KNNClassifier({'k': 1, 'samples': [
        {'ring': 'INNER', 'position_cc16': 50, 'velocity': 50},
    ]})
    close = classifier.classify_hit(50, 50)
    far = classifier.classify_hit(127, 127)
    assert close.ring == far.ring == 'INNER'
    assert 0 < far.confidence < close.confidence <= 1


def test_vote_ties_use_distance():
    classifier = KNNClassifier({'k': 3, 'samples': [
        {'ring': 'CENTER', 'position_cc16': 0, 'velocity': 50},
        {'ring': 'INNER', 'position_cc16': 49, 'velocity': 50},
        {'ring': 'MIDDLE', 'position_cc16': 60, 'velocity': 50},
    ]})
    assert classifier.classify_hit(50, 50).ring == 'INNER'


def test_invalid_calibration_fails_clearly():
    with pytest.raises(ValueError):
        KNNClassifier({'samples': []})
    with pytest.raises(ValueError):
        KNNClassifier({'k': 1, 'samples': [{'ring': 'UNKNOWN', 'position_cc16': 10, 'velocity': 60}]})


def test_only_mapped_heads_are_classified_and_raw_values_survive(classifier):
    mapping = json.loads((ROOT / 'app/midi/mapping.json').read_text())
    interpreter = MidiInterpreter(mapping, classifier)
    for pitch, channel, expected in [(38, 9, 'CENTER'), (40, 9, 'UNKNOWN'), (36, 9, 'UNKNOWN'), (38, 8, 'UNKNOWN')]:
        interpreter.process(mido.Message('control_change', channel=channel, control=16, value=0), device='TD-50X', now=1)
        event = interpreter.process(mido.Message('note_on', channel=channel, note=pitch, velocity=63), device='TD-50X', now=1.001)
        assert event.estimated_ring == expected
        assert event.position_cc16 == 0 and event.velocity == 63
    event = interpreter.process(mido.Message('note_on', channel=9, note=38, velocity=63), device='TD-50X', now=2)
    assert event.estimated_ring == 'UNKNOWN'
