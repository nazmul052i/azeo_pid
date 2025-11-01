from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Literal


@dataclass(slots=True)
class FitResult:
    """
    Identification result returned by step-test fitting.

    model_type: "FOPDT" | "SOPDT" | "Integrating"
    params    : dictionary keyed by model type fields
    stats     : {"rss":..., "aic":..., "bic":..., "r2":...} etc.
    """
    model_type: Literal["FOPDT", "SOPDT", "Integrating"]
    params: Dict[str, float]
    stats: Dict[str, float]

    def to_dict(self) -> Dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict) -> "FitResult":
        return FitResult(
            model_type=d.get("model_type", "FOPDT"),
            params={k: float(v) for k, v in d.get("params", {}).items()},
            stats={k: float(v) for k, v in d.get("stats", {}).items()},
        )
