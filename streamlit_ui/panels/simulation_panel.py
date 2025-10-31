import time
import streamlit as st
from ..state import SessionState
from ..components.charts import pv_sp_chart, op_chart
from ..compat import simulate_closed_loop, streaming_closed_loop

def render(state: SessionState) -> None:
    st.header("Simulation")

    col_top = st.columns([1, 1, 1, 2])
    with col_top[0]:
        state.use_realtime = st.toggle("Realtime mode", value=state.use_realtime)
    with col_top[1]:
        state.realtime_speed = st.slider("Speed ×", min_value=0.1, max_value=10.0, value=float(state.realtime_speed), step=0.1)
    with col_top[2]:
        run = st.button("Run", use_container_width=True)
    with col_top[3]:
        stop = st.button("Stop", use_container_width=True, key="stop_btn")

    if run and not state.use_realtime:
        # One-shot batch simulate
        t, y, sp, u = simulate_closed_loop(
            model_type=state.model_type,
            K=state.K, tau=state.tau, theta=state.theta, tau2=state.tau2, leak=state.leak,
            mode=state.mode, Kp=state.Kp, Ti=state.Ti, Td=state.Td,
            beta=state.beta, deriv_on=state.deriv_on, filt_N=state.filt_N,
            aw_track=state.aw_track, umin=state.umin, umax=state.umax,
            sp_value=state.sp, y0=state.y0, u0=state.u0,
            dt=state.dt, horizon=state.horizon,
        )
        st.plotly_chart(pv_sp_chart(t, y, sp), use_container_width=True)
        st.plotly_chart(op_chart(t, u), use_container_width=True)
        st.download_button("Download CSV", data=_to_csv(t, y, sp, u), file_name="simulation.csv", mime="text/csv")
        return

    if run and state.use_realtime:
        # Realtime streaming: update charts every ~1s
        placeholder_pv = st.empty()
        placeholder_op = st.empty()
        placeholder_status = st.empty()

        # Flag in session for Stop button
        st.session_state.setdefault("_sim_running", True)
        st.session_state["_sim_running"] = True

        gen = streaming_closed_loop(
            model_type=state.model_type,
            K=state.K, tau=state.tau, theta=state.theta, tau2=state.tau2, leak=state.leak,
            mode=state.mode, Kp=state.Kp, Ti=state.Ti, Td=state.Td,
            beta=state.beta, deriv_on=state.deriv_on, filt_N=state.filt_N,
            aw_track=state.aw_track, umin=state.umin, umax=state.umax,
            sp_value=state.sp, y0=state.y0, u0=state.u0,
            dt=state.dt, horizon=state.horizon,
            update_period=max(0.2, 1.0 / float(state.realtime_speed)),
        )

        for t, y, sp, u in gen:
            if not st.session_state.get("_sim_running", False):
                break
            placeholder_pv.plotly_chart(pv_sp_chart(t, y, sp), use_container_width=True)
            placeholder_op.plotly_chart(op_chart(t, u), use_container_width=True)
            placeholder_status.info(f"t = {t[-1]:.1f} s  •  points = {len(t)}")
            # Let Streamlit render this iteration
            time.sleep(0.01)

        # Final download after loop ends
        st.download_button("Download CSV", data=_to_csv(t, y, sp, u), file_name="simulation.csv", mime="text/csv")

    # Stop button handling (works whether in loop or not)
    if stop:
        st.session_state["_sim_running"] = False


def _to_csv(t, y, sp, u) -> str:
    import io, csv
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["t", "PV", "SP", "OP"])
    for i in range(len(t)):
        w.writerow([t[i], y[i], sp[i], u[i]])
    return buf.getvalue()
