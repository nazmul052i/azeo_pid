# ===========================
# streamlit_ui/state.py
# ===========================

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import streamlit as st


@dataclass
class SessionState:
    # Process params (FOPDT/SOPDT/Integrator)
    model_type: str = "FOPDT"  # FOPDT | SOPDT | INTEGRATOR
    K: float = 1.0
    tau: float = 10.0
    theta: float = 2.0
    tau2: float = 0.0  # SOPDT second time constant
    leak: float = 0.0  # Integrator leak term

    # PID params & options
    mode: str = "PID"          # P | PI | PID
    Kp: float = 1.0
    Ti: float = 10.0
    Td: float = 0.0
    beta: float = 1.0           # setpoint weight
    deriv_on: str = "PV"        # PV | ERROR
    filt_N: float = 10.0        # derivative filter factor (T_d/N)
    aw_track: bool = True
    umin: float = 0.0
    umax: float = 100.0

    # Simulation
    sp: float = 1.0
    u0: float = 0.0
    y0: float = 0.0
    dt: float = 0.1
    horizon: float = 200.0
    realtime_speed: float = 1.0
    use_realtime: bool = False
    
    # Continuous simulation state
    simulation_running: bool = False
    simulation_time: float = 0.0
    simulation_data: Dict[str, List[float]] = field(default_factory=lambda: {"t": [], "y": [], "sp": [], "u": []})
    last_update: float = 0.0

    # Data for Step-ID / Tuning
    uploaded_csv_bytes: Optional[bytes] = None
    last_fit: Optional[Dict[str, Any]] = None
    calculated_tuning: Optional[Dict[str, float]] = None

    # OPC
    opc_endpoint: str = ""
    opc_connected: bool = False


_STATE_KEY = "__pid_tuner_state__"


def get_state() -> SessionState:
    if _STATE_KEY not in st.session_state:
        st.session_state[_STATE_KEY] = SessionState()
    return st.session_state[_STATE_KEY]


def init_defaults(state: SessionState) -> None:
    # Could load persisted prefs here
    pass