# ===========================
# streamlit_ui/panels/process_panel.py
# ===========================

import streamlit as st
from ..state import SessionState
from ..components.forms import num


def render(state: SessionState) -> None:
    st.header("Process Model")
    colA, colB, colC, colD = st.columns(4)

    with colA:
        state.model_type = st.selectbox("Model", ("FOPDT", "SOPDT", "INTEGRATOR"), index=(0 if state.model_type == "FOPDT" else 1 if state.model_type == "SOPDT" else 2))
        state.K = num("Gain K", state.K)
        state.theta = num("Dead time θ", state.theta)

    with colB:
        state.tau = num("Time constant τ", state.tau)
        if state.model_type == "SOPDT":
            state.tau2 = num("Second τ2", state.tau2)
        if state.model_type == "INTEGRATOR":
            state.leak = num("Leak (1/s)", state.leak)

    with colC:
        state.sp = num("Setpoint SP", state.sp)
        state.u0 = num("Initial OP u0", state.u0)

    with colD:
        state.y0 = num("Initial PV y0", state.y0)
        state.dt = num("Δt (s)", state.dt, step=0.01, fmt="%.2f")
        state.horizon = num("Horizon (s)", state.horizon, step=1.0, fmt="%.0f")