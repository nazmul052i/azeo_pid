# ===========================
# streamlit_ui/panels/stepid_panel.py
# ===========================

import io
import streamlit as st
import numpy as np
from ..state import SessionState
from ..components.tables import dict_table

# Go through compat shim so we don't depend on exact backend names.
from ..tune_compat import (
    identify_model,
    tuning_simc,
    tuning_lambda,
    tuning_zn_reaction,
)


def render(state: SessionState) -> None:
    st.header("Step-Test Identification & Tuning")

    uploaded = st.file_uploader("Upload step-test CSV (t, SP, PV[, OP])", type=["csv"]) 
    if uploaded is not None:
        state.uploaded_csv_bytes = uploaded.getvalue()

    if state.uploaded_csv_bytes:
        import pandas as pd
        df = pd.read_csv(io.BytesIO(state.uploaded_csv_bytes))
        df.columns = [c.strip().lower() for c in df.columns]

        # Flexible column handling
        # Accept t/time, sp/setpoint, pv/processvalue, op/output if provided
        colmap = {
            "t": next((c for c in df.columns if c in ("t","time","sec","seconds")), None),
            "sp": next((c for c in df.columns if c in ("sp","setpoint")), None),
            "pv": next((c for c in df.columns if c in ("pv","processvalue","mv","y")), None),
        }
        if not all(colmap.values()):
            missing = [k for k,v in colmap.items() if v is None]
            st.error(f"Missing required columns: {', '.join(missing)} (case-insensitive)")
            return

        t = df[colmap["t"]].to_numpy()
        sp = df[colmap["sp"]].to_numpy()
        pv = df[colmap["pv"]].to_numpy()

        st.line_chart({"PV": pv, "SP": sp})

        with st.expander("Fit model"):
            mtype = st.selectbox("Model type to fit", ("FOPDT", "SOPDT", "INTEGRATOR"))
            if st.button("Identify"):
                fit = identify_model(mtype=mtype, t=t, sp=sp, pv=pv)
                if fit is None:
                    st.error("Identification failed (or backend function not found).")
                else:
                    state.last_fit = fit

        if state.last_fit:
            dict_table("Identified model", state.last_fit)

            with st.expander("Compute tuning (SIMC / Lambda / ZN)", expanded=True):
                rule = st.selectbox("Rule", ("SIMC", "Lambda/IMC", "Ziegler–Nichols (reaction curve)"))
                if st.button("Calculate tuning"):
                    if rule == "SIMC":
                        Kp, Ti, Td = tuning_simc(state.last_fit)
                    elif rule == "Lambda/IMC":
                        Kp, Ti, Td = tuning_lambda(state.last_fit)
                    else:
                        Kp, Ti, Td = tuning_zn_reaction(state.last_fit)

                    st.success(f"Kp={Kp:.3f}, Ti={Ti:.3f}, Td={Td:.3f}")
                    if st.button("Apply to controller"):
                        state.Kp, state.Ti, state.Td = float(Kp), float(Ti), float(Td)