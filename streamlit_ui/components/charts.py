# ===========================
# streamlit_ui/components/charts.py
# ===========================

from typing import Sequence
import plotly.graph_objects as go


def pv_sp_chart(t: Sequence[float], y: Sequence[float], sp: Sequence[float]) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(x=t, y=y, mode="lines", name="PV")
    fig.add_scatter(x=t, y=sp, mode="lines", name="SP")
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10))
    return fig


def op_chart(t: Sequence[float], u: Sequence[float]) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(x=t, y=u, mode="lines", name="OP")
    fig.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10))
    return fig