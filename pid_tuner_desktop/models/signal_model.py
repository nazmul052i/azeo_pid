from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass(slots=True)
class SignalModel:
    """
    Describes a plant/sim signal and its display limits.
    """
    name: str
    kind: str  # "SP" | "PV" | "OP" | "DV" | "MV" etc.
    unit: Optional[str] = None
    minimum: float = 0.0
    maximum: float = 100.0
    description: str = ""

    def clamp(self, value: float) -> float:
        return max(self.minimum, min(self.maximum, float(value)))

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "SignalModel":
        return SignalModel(
            name=d.get("name", ""),
            kind=d.get("kind", "PV"),
            unit=d.get("unit"),
            minimum=float(d.get("minimum", 0.0)),
            maximum=float(d.get("maximum", 100.0)),
            description=d.get("description", ""),
        )
