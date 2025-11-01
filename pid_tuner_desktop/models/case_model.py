from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Tuple


@dataclass(slots=True)
class CaseModel:
    """
    A tuning 'case' — row-oriented data mirroring the AptiTune-like grid.

    Fields:
      name         : display name of the case
      optimize_map : which parameters are optimized {"Gain":bool,"Ti":bool,"Td":bool}
      bounds       : parameter bounds {"Gain":(lo,hi),"Ti":(lo,hi),"Td":(lo,hi)}
      existing     : existing controller values {"Gain":..., "Ti":..., "Td":...}
      initial      : starting point for optimizer {"Gain":..., "Ti":..., "Td":...}
      final        : tuned result {"Gain":..., "Ti":..., "Td":...}
    """
    name: str = "tuning case"
    optimize_map: Dict[str, bool] = None
    bounds: Dict[str, Tuple[float, float]] = None
    existing: Dict[str, float] = None
    initial: Dict[str, float] = None
    final: Dict[str, float] = None

    def __post_init__(self):
        def _ensure_map(d, default):
            return d if isinstance(d, dict) else dict(default)

        self.optimize_map = _ensure_map(
            self.optimize_map, {"Gain": True, "Ti": True, "Td": True}
        )
        self.bounds = _ensure_map(
            self.bounds, {"Gain": (1e-4, 1e2), "Ti": (0.0, 1e4), "Td": (0.0, 1e4)}
        )
        self.existing = _ensure_map(
            self.existing, {"Gain": 1.0, "Ti": 0.0, "Td": 0.0}
        )
        self.initial = _ensure_map(
            self.initial, {"Gain": 0.3, "Ti": 20.0, "Td": 0.0}
        )
        self.final = _ensure_map(
            self.final, {"Gain": 0.3, "Ti": 20.0, "Td": 0.0}
        )

    def to_dict(self) -> Dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict) -> "CaseModel":
        return CaseModel(
            name=d.get("name", "tuning case"),
            optimize_map=d.get("optimize_map"),
            bounds=d.get("bounds"),
            existing=d.get("existing"),
            initial=d.get("initial"),
            final=d.get("final"),
        )
