from dataclasses import asdict, dataclass
from typing import Literal, Protocol

Ring = Literal['CENTER', 'INNER', 'MIDDLE', 'OUTER', 'UNKNOWN']


@dataclass(frozen=True)
class Classification:
    ring: Ring = 'UNKNOWN'
    confidence: float = 0.0


class HitClassifier(Protocol):
    def classify_hit(self, position: int | None, velocity: int) -> Classification: ...


@dataclass(frozen=True)
class HitEvent:
    sequence: int
    timestamp: str
    device: str
    channel: int
    note: int
    note_name: str
    articulation: str
    velocity: int
    position_cc16: int | None
    velocity_prefix_cc88: int | None
    estimated_ring: Ring = 'UNKNOWN'
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)
