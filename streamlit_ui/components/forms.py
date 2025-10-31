# ===========================
# streamlit_ui/components/forms.py
# ===========================

import streamlit as st


def num(label: str, value: float, step: float = 0.1, fmt: str = "%.3f") -> float:
    return st.number_input(label, value=float(value), step=step, format=fmt)