# ===========================
# streamlit_ui/panels/controller_panel.py
# ===========================

import streamlit as st
from ..state import SessionState
from ..components import forms


def render(state: SessionState) -> None:
    st.header("Controller")
    colA, colB, colC, colD = st.columns(4)

    with colA:
        state.mode = st.selectbox("Mode", ("P", "PI", "PID"), index=(0 if state.mode == "P" else 1 if state.mode == "PI" else 2))
        state.Kp = forms.num("Kp", state.Kp)

    with colB:
        state.Ti = forms.num("Ti (s)", state.Ti)
        state.Td = forms.num("Td (s)", state.Td)

    with colC:
        state.beta = forms.num("Setpoint weight β", state.beta)
        state.deriv_on = st.selectbox("Derivative on", ("PV", "ERROR"), index=(0 if state.deriv_on == "PV" else 1))

    with colD:
        state.filt_N = forms.num("Deriv filter N", state.filt_N)
        state.aw_track = st.checkbox("Anti-windup (tracking)", value=state.aw_track)
        state.umin = forms.num("u min", state.umin)
        state.umax = forms.num("u max", state.umax)