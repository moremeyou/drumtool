"""Small, replaceable nearest-neighbour classifier; no position threshold bands."""
from collections import Counter
from math import hypot, isfinite

from app.models.hit import Classification

RINGS = {'CENTER', 'INNER', 'MIDDLE', 'OUTER'}


def midi_value(value):
    return type(value) is int and 0 <= value <= 127


class KNNClassifier:
    def __init__(self, calibration: dict):
        samples = calibration.get('samples', [])
        k = calibration.get('k', 5)
        if not samples or type(k) is not int or not 1 <= k <= len(samples):
            raise ValueError('Calibration requires samples and an integer k within sample count.')
        self.k = k
        weights = calibration.get('feature_weights', {'position_cc16': 1, 'velocity': 1})
        if not isinstance(weights, dict) or set(weights) != {'position_cc16', 'velocity'}:
            raise ValueError('Feature weights require position_cc16 and velocity.')
        if any(type(value) not in (int, float) or not isfinite(value) or value < 0
               for value in weights.values()) or not any(weights.values()):
            raise ValueError('Feature weights must be finite, nonnegative, and not all zero.')
        self.position_weight = weights['position_cc16']
        self.velocity_weight = weights['velocity']
        self.samples = []
        for sample in samples:
            ring = sample.get('ring')
            position, velocity = sample.get('position_cc16'), sample.get('velocity')
            if ring not in RINGS or not midi_value(position) or not midi_value(velocity):
                raise ValueError('Calibration samples require a known ring and MIDI values from 0 to 127.')
            self.samples.append((position / 127, velocity / 127, ring))

    def classify_hit(self, position: int | None, velocity: int) -> Classification:
        if not midi_value(position) or not midi_value(velocity):
            return Classification()
        neighbours = sorted(
            (hypot(self.position_weight * (position / 127 - x),
                   self.velocity_weight * (velocity / 127 - y)), ring)
            for x, y, ring in self.samples
        )[:self.k]
        votes = Counter(ring for _, ring in neighbours)
        # Vote ties prefer the label with the smallest total neighbour distance;
        # exact distance ties use the label for deterministic, order-independent output.
        winner = min(votes, key=lambda ring: (
            -votes[ring], sum(distance for distance, label in neighbours if label == ring), ring))
        mean_distance = sum(distance for distance, _ in neighbours) / self.k
        confidence = (votes[winner] / self.k) / (1 + mean_distance)
        return Classification(winner, round(confidence, 4))
