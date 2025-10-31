# ===========================
# streamlit_ui/styles.py
# ===========================

import streamlit as st


_DEF_CSS = """
/* tighten paddings */
.block-container { padding-top: 1rem; padding-bottom: 1rem; }
/* small code blocks */
code, pre { font-size: 12px; }
"""


def inject_css():
    st.markdown(f"<style>{_DEF_CSS}</style>", unsafe_allow_html=True)