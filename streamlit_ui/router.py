# ===========================
# streamlit_ui/router.py
# ===========================

from enum import Enum, auto
import streamlit as st


class Page(Enum):
    PROCESS = auto()
    CONTROLLER = auto()
    SIMULATION = auto()
    STEP_ID = auto()
    OPC = auto()


def route_sidebar() -> Page:
    with st.sidebar:
        st.title("PID Tuner")
        choice = st.radio(
            "Navigation",
            (
                "Process",
                "Controller",
                "Simulation",
                "Step-Test ID",
                "OPC Data",
            ),
            index=2,
        )
    return {
        "Process": Page.PROCESS,
        "Controller": Page.CONTROLLER,
        "Simulation": Page.SIMULATION,
        "Step-Test ID": Page.STEP_ID,
        "OPC Data": Page.OPC,
    }[choice]