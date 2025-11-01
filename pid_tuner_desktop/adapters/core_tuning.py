from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Literal, Tuple


# ------------------------------
# Generic PID parameterization
# ------------------------------

@dataclass(slots=True)
class GenericPID:
    """
    Generic continuous-time parallel PID with setpoint weight and
    derivative filter:
        u = Kp [ β r - y ] + Kp/Ti ∫ (r - y) dt + Kp*Td/(α s + 1) d/dt(-y or e)

    Fields
      Kp   : proportional gain
      Ti   : integral time [s] (0 = off)
      Td   : derivative time [s] (0 = off)
      beta : setpoint weight on proportional path
      alpha: derivative filter factor (0<α≤1, higher = more filtering)
      mode : "P" | "PI" | "PID" (for UI logic)
      d_on : "PV" | "Error" (derivative on measurement or error)
    """
    Kp: float
    Ti: float
    Td: float
    beta: float = 1.0
    alpha: float = 0.125
    mode: Literal["P", "PI", "PID"] = "PID"
    d_on: Literal["PV", "Error"] = "PV"

    def clamp_nonneg(self):
        self.Kp = max(0.0, float(self.Kp))
        self.Ti = max(0.0, float(self.Ti))
        self.Td = max(0.0, float(self.Td))
        self.beta = float(min(max(self.beta, 0.0), 2.0))
        self.alpha = float(min(max(self.alpha, 1e-6), 1.0))
        if self.mode == "P":
            self.Ti = 0.0; self.Td = 0.0
        elif self.mode == "PI":
            self.Td = 0.0
        return self


# -------------------------------------------
# Emerson DeltaV: "Standard PID (PIDe)" form
# -------------------------------------------

@dataclass(slots=True)
class DeltaVStdPIDe:
    """
    Emerson DeltaV Standard PID (external-reset, PIDe) parameters.
    We normalize to the common set:
      Gain  : dimensionless
      Tr    : Reset time [s]  (0 disables integral)
      Td    : Derivative time [s] (0 disables derivative)
      alpha : Derivative filter factor (0<α≤1)
    """
    Gain: float
    Tr: float
    Td: float
    alpha: float = 0.125

    def as_dict(self) -> Dict[str, float]:
        return {"Gain": float(self.Gain), "Tr": float(self.Tr), "Td": float(self.Td), "alpha": float(self.alpha)}


def generic_to_deltav_std_pide(pid: GenericPID) -> DeltaVStdPIDe:
    """
    Map GenericPID → DeltaV Standard PIDe.
    Assumptions:
      - Reset time is seconds (DeltaV can show min; we stay in seconds for internal consistency).
      - Proportional band is not used; we keep numeric gain.
      - SP weight β is not represented in DeltaV standard block; keep it in UI but doesn't map.
    """
    pid = pid.clamp_nonneg()
    return DeltaVStdPIDe(Gain=pid.Kp, Tr=pid.Ti, Td=pid.Td, alpha=pid.alpha)


def deltav_std_pide_to_generic(block: DeltaVStdPIDe, beta: float = 1.0, d_on: str = "PV") -> GenericPID:
    """
    Map DeltaV Standard PIDe → GenericPID. Beta and derivative-on are UI concerns;
    we carry them through using defaults unless supplied.
    """
    mode: Literal["P", "PI", "PID"]
    if block.Tr <= 0.0 and block.Td <= 0.0:
        mode = "P"
    elif block.Td <= 0.0:
        mode = "PI"
    else:
        mode = "PID"
    return GenericPID(Kp=block.Gain, Ti=max(0.0, block.Tr), Td=max(0.0, block.Td),
                      beta=float(beta), alpha=float(block.alpha), mode=mode,
                      d_on="PV" if str(d_on).upper().startswith("PV") else "Error")


# -------------------------------------------
# Utility: vendor registry (future extension)
# -------------------------------------------

def to_vendor_form(vendor: str, pid: GenericPID) -> Dict[str, float]:
    """
    Convert a GenericPID to a vendor-specific dictionary. Supported:
      - "Emerson DeltaV PIDe"
    """
    vendor = vendor.strip().lower()
    if "deltav" in vendor:
        blk = generic_to_deltav_std_pide(pid)
        return blk.as_dict()
    # add more vendor mappings here as needed
    # default to generic
    return {
        "Kp": pid.Kp, "Ti": pid.Ti, "Td": pid.Td, "beta": pid.beta, "alpha": pid.alpha,
        "mode": pid.mode, "d_on": pid.d_on
    }


def from_vendor_form(vendor: str, data: Dict[str, float], *, beta: float = 1.0, d_on: str = "PV") -> GenericPID:
    """
    Convert vendor dictionary back to GenericPID.
    """
    vendor = vendor.strip().lower()
    if "deltav" in vendor:
        blk = DeltaVStdPIDe(
            Gain=float(data.get("Gain", data.get("Kp", 0.0))),
            Tr=float(data.get("Tr", data.get("Ti", 0.0))),
            Td=float(data.get("Td", 0.0)),
            alpha=float(data.get("alpha", 0.125)),
        )
        return deltav_std_pide_to_generic(blk, beta=beta, d_on=d_on)
    # fallback generic
    return GenericPID(
        Kp=float(data.get("Kp", 0.0)),
        Ti=float(data.get("Ti", 0.0)),
        Td=float(data.get("Td", 0.0)),
        beta=float(data.get("beta", beta)),
        alpha=float(data.get("alpha", 0.125)),
        mode=str(data.get("mode", "PID")),
        d_on="PV" if str(data.get("d_on", d_on)).upper().startswith("PV") else "Error",
    )
