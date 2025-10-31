# ===========================
# streamlit_ui/panels/opc_panel.py
# ===========================

import streamlit as st
from ..state import SessionState

# Storage/OPC hooks (optional runtime availability)


def render(state: SessionState) -> None:
    st.header("OPC Data Acquisition")

    state.opc_endpoint = st.text_input("Endpoint URL", value=state.opc_endpoint, placeholder="opc.tcp://localhost:4840")

    col = st.columns(2)
    with col[0]:
        if st.button("Connect"):
            # Placeholder UI; backend integration can be wired to pid_tuner.opc
            state.opc_connected = True
    with col[1]:
        if st.button("Disconnect"):
            state.opc_connected = False

    st.info("This panel is a thin UI; wire to pid_tuner.opc.ua_client/da_client as needed.")
