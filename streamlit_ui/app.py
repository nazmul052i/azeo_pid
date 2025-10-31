# ===========================
# streamlit_ui/app.py
# ===========================

import streamlit as st
from .router import Page, route_sidebar
from .panels import process_panel, controller_panel, simulation_panel, stepid_panel, opc_panel
from .state import get_state, init_defaults
from .styles import inject_css


def main() -> None:
    st.set_page_config(page_title="PID Tuner & Loop Analyzer", layout="wide")
    inject_css()

    state = get_state()
    init_defaults(state)

    page = route_sidebar()

    if page == Page.PROCESS:
        process_panel.render(state)
    elif page == Page.CONTROLLER:
        controller_panel.render(state)
    elif page == Page.SIMULATION:
        simulation_panel.render(state)
    elif page == Page.STEP_ID:
        stepid_panel.render(state)
    elif page == Page.OPC:
        opc_panel.render(state)
    else:
        st.error("Unknown page")
