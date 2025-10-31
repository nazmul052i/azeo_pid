# ===========================
# streamlit_ui/components/tables.py
# ===========================

import pandas as pd
import streamlit as st


def dict_table(title: str, data: dict) -> None:
    st.subheader(title)
    df = pd.DataFrame(list(data.items()), columns=["Parameter", "Value"])
    st.dataframe(df, use_container_width=True)