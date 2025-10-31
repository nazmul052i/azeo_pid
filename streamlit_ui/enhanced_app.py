# ===========================
# Enhanced PID Tuner App - INCA-style UI
# ===========================

import sys
from pathlib import Path

# Add project path to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# Import existing modules - adjust paths as needed
try:
    from streamlit_ui.state import SessionState, get_state, init_defaults
    from streamlit_ui.styles import inject_css
except ImportError:
    # Try alternative import if running from different location
    from state import SessionState, get_state, init_defaults
    from styles import inject_css

st.set_page_config(
    page_title="PID Tuner & Loop Analyzer",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_css()

# Custom CSS for INCA-style interface
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0 0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff;
        border-top: 3px solid #ff4b4b;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 5px;
        border-left: 4px solid #ff4b4b;
        margin: 10px 0;
    }
    .section-header {
        background-color: #e8eaed;
        padding: 10px;
        border-radius: 5px;
        font-weight: bold;
        margin: 15px 0 10px 0;
    }
</style>
""", unsafe_allow_html=True)

def main():
    state = get_state()
    init_defaults(state)
    
    # Sidebar - Project Overview
    with st.sidebar:
        st.title("🎛️ PID Tuner")
        st.markdown("---")
        
        # Project name
        project_name = st.text_input("Project Name", value="PID Tuning Project", key="project_name")
        
        st.markdown("---")
        st.subheader("📊 Quick Stats")
        
        # Display current controller settings
        st.markdown(f"""
        <div class="metric-card">
            <strong>Controller Mode:</strong> {state.mode}<br>
            <strong>Kp:</strong> {state.Kp:.3f}<br>
            <strong>Ti:</strong> {state.Ti:.3f} s<br>
            <strong>Td:</strong> {state.Td:.3f} s
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader("🔧 Actions")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Import", use_container_width=True):
                st.info("Import functionality")
        with col2:
            if st.button("💾 Export", use_container_width=True):
                st.info("Export functionality")
        
        if st.button("🔄 Reset All", use_container_width=True, type="secondary"):
            st.rerun()
    
    # Main content area with tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Acquisition",
        "🔍 Identification", 
        "🎛️ Controller",
        "🧪 Simulation",
        "📡 OPC Data"
    ])
    
    # Tab 1: Data Acquisition
    with tab1:
        render_acquisition_tab(state)
    
    # Tab 2: Identification
    with tab2:
        render_identification_tab(state)
    
    # Tab 3: Controller Configuration
    with tab3:
        render_controller_tab(state)
    
    # Tab 4: Simulation
    with tab4:
        render_simulation_tab(state)
    
    # Tab 5: OPC Data
    with tab5:
        render_opc_tab(state)

def render_acquisition_tab(state):
    st.header("Data Acquisition")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown('<div class="section-header">Signal Configuration</div>', unsafe_allow_html=True)
        
        # Signal table similar to INCA
        signal_data = {
            "Type": ["OP", "PV", "SP"],
            "Name": ["Controller Output", "Process Variable", "Setpoint"],
            "Min": [state.umin, 0, 0],
            "Max": [state.umax, 100, 100],
            "Unit": ["%", state.model_type, state.model_type],
            "Description": ["Control signal", "Measured value", "Target value"]
        }
        
        df_signals = pd.DataFrame(signal_data)
        st.dataframe(df_signals, use_container_width=True, hide_index=True)
        
        st.markdown('<div class="section-header">Sampling Configuration</div>', unsafe_allow_html=True)
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            sampling_interval = st.number_input("Sampling Interval (s)", 
                                               value=state.dt, 
                                               min_value=0.01,
                                               step=0.01)
        with col_b:
            duration = st.number_input("Duration (s)", 
                                      value=state.horizon,
                                      min_value=10.0,
                                      step=10.0)
        with col_c:
            st.metric("Expected Samples", int(duration / sampling_interval))
    
    with col2:
        st.markdown('<div class="section-header">Data Import</div>', unsafe_allow_html=True)
        
        # File upload
        uploaded_file = st.file_uploader(
            "Upload CSV Data",
            type=["csv"],
            help="CSV file should contain columns: t, SP, PV, OP"
        )
        
        if uploaded_file:
            state.uploaded_csv_bytes = uploaded_file.getvalue()
            st.success("✅ File uploaded successfully!")
            
            # Show preview
            import io
            df = pd.read_csv(io.BytesIO(state.uploaded_csv_bytes))
            st.write("Preview:")
            st.dataframe(df.head(), use_container_width=True)
        
        st.markdown('<div class="section-header">Quick Actions</div>', unsafe_allow_html=True)
        
        if st.button("▶️ Start Recording", use_container_width=True, type="primary"):
            st.info("Recording started...")
        
        if st.button("⏸️ Stop Recording", use_container_width=True):
            st.info("Recording stopped")
        
        if st.button("🗑️ Clear Data", use_container_width=True):
            state.uploaded_csv_bytes = None
            st.rerun()

def render_identification_tab(state):
    st.header("Model Identification & Tuning")
    
    # Process Model Selection
    st.markdown('<div class="section-header">Process Model</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        model_type = st.selectbox(
            "Model Type",
            ["FOPDT", "SOPDT", "INTEGRATOR"],
            index=["FOPDT", "SOPDT", "INTEGRATOR"].index(state.model_type)
        )
        state.model_type = model_type
    
    with col2:
        if state.uploaded_csv_bytes:
            if st.button("🔍 Identify Model", use_container_width=True, type="primary"):
                identify_model_from_data(state)
    
    with col3:
        if state.last_fit:
            if st.button("📋 Apply to Process", use_container_width=True):
                apply_identified_model(state)
    
    # Display identified model
    if state.last_fit:
        st.markdown('<div class="section-header">Identified Model Parameters</div>', unsafe_allow_html=True)
        
        cols = st.columns(len(state.last_fit))
        for i, (key, value) in enumerate(state.last_fit.items()):
            with cols[i]:
                st.metric(key.upper(), f"{value:.4f}")
        
        # Tuning Rules
        st.markdown('<div class="section-header">Tuning Rules</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            tuning_method = st.selectbox(
                "Select Tuning Method",
                ["SIMC", "Lambda/IMC", "Ziegler-Nichols (Reaction Curve)"]
            )
            
            if st.button("⚙️ Calculate Tuning", use_container_width=True, type="primary"):
                calculate_tuning(state, tuning_method)
        
        with col2:
            if hasattr(state, 'calculated_tuning'):
                st.info("**Calculated Parameters:**")
                tuning = state.calculated_tuning
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("Kp", f"{tuning['Kp']:.4f}")
                with col_b:
                    st.metric("Ti", f"{tuning['Ti']:.4f}")
                with col_c:
                    st.metric("Td", f"{tuning['Td']:.4f}")
                
                if st.button("✅ Apply to Controller", use_container_width=True):
                    state.Kp = tuning['Kp']
                    state.Ti = tuning['Ti']
                    state.Td = tuning['Td']
                    st.success("Tuning parameters applied!")
                    st.rerun()

def render_controller_tab(state):
    st.header("Controller Configuration")
    
    # Controller structure diagram
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown('<div class="section-header">Controller Type</div>', unsafe_allow_html=True)
        
        state.mode = st.radio(
            "Mode",
            ["P", "PI", "PID"],
            index=["P", "PI", "PID"].index(state.mode),
            horizontal=True
        )
        
        st.markdown('<div class="section-header">Tuning Parameters</div>', unsafe_allow_html=True)
        
        state.Kp = st.number_input("Proportional Gain (Kp)", 
                                   value=float(state.Kp), 
                                   step=0.1, 
                                   format="%.3f")
        
        if state.mode in ["PI", "PID"]:
            state.Ti = st.number_input("Integral Time (Ti) [s]", 
                                      value=float(state.Ti), 
                                      step=0.1, 
                                      format="%.3f")
        
        if state.mode == "PID":
            state.Td = st.number_input("Derivative Time (Td) [s]", 
                                      value=float(state.Td), 
                                      step=0.1, 
                                      format="%.3f")
            
            state.filt_N = st.number_input("Derivative Filter (N)", 
                                          value=float(state.filt_N), 
                                          step=1.0, 
                                          format="%.1f")
    
    with col2:
        st.markdown('<div class="section-header">Advanced Options</div>', unsafe_allow_html=True)
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            state.beta = st.number_input("Setpoint Weight (β)", 
                                        value=float(state.beta), 
                                        step=0.1, 
                                        format="%.2f")
            
            state.deriv_on = st.selectbox("Derivative On", 
                                         ["PV", "ERROR"],
                                         index=0 if state.deriv_on == "PV" else 1)
        
        with col_b:
            state.aw_track = st.checkbox("Anti-windup (Tracking)", value=state.aw_track)
            
            st.write("**Output Limits:**")
            state.umin = st.number_input("Min", value=float(state.umin), format="%.1f")
            state.umax = st.number_input("Max", value=float(state.umax), format="%.1f")
        
        # Visual representation of controller structure
        st.markdown('<div class="section-header">Controller Structure</div>', unsafe_allow_html=True)
        
        create_controller_diagram(state)

def render_simulation_tab(state):
    st.header("Process Simulation")
    
    # Process parameters
    st.markdown('<div class="section-header">Process Parameters</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        state.K = st.number_input("Gain (K)", value=float(state.K), step=0.1, format="%.3f")
        state.tau = st.number_input("Time Constant (τ)", value=float(state.tau), step=1.0, format="%.1f")
    
    with col2:
        state.theta = st.number_input("Dead Time (θ)", value=float(state.theta), step=0.1, format="%.2f")
        if state.model_type == "SOPDT":
            state.tau2 = st.number_input("Second τ₂", value=float(state.tau2), step=0.1, format="%.2f")
    
    with col3:
        state.sp = st.number_input("Setpoint (SP)", value=float(state.sp), step=0.1, format="%.2f")
        state.y0 = st.number_input("Initial PV", value=float(state.y0), step=0.1, format="%.2f")
    
    with col4:
        state.u0 = st.number_input("Initial OP", value=float(state.u0), step=0.1, format="%.2f")
        state.dt = st.number_input("Δt (s)", value=float(state.dt), step=0.01, format="%.2f")
    
    # Simulation controls
    st.markdown('<div class="section-header">Simulation Controls</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        state.horizon = st.number_input("Horizon (s)", value=float(state.horizon), step=10.0, format="%.0f")
    
    with col2:
        state.use_realtime = st.toggle("Continuous Mode", value=state.use_realtime, 
                                       help="Run simulation continuously in real-time")
    
    with col3:
        if state.use_realtime:
            state.realtime_speed = st.slider("Speed ×", 0.1, 10.0, float(state.realtime_speed), 0.1)
    
    with col4:
        col_a, col_b = st.columns(2)
        with col_a:
            start_sim = st.button("▶️ Start", use_container_width=True, type="primary")
        with col_b:
            stop_sim = st.button("⏹️ Stop", use_container_width=True)
    
    # Handle start/stop
    if start_sim:
        state.simulation_running = True
        state.simulation_time = 0
        state.simulation_data = {"t": [], "y": [], "sp": [], "u": []}
    
    if stop_sim:
        state.simulation_running = False
    
    # Run continuous simulation
    if state.use_realtime and hasattr(state, 'simulation_running') and state.simulation_running:
        run_continuous_simulation(state)
    elif not state.use_realtime:
        # One-shot simulation mode
        if start_sim:
            with st.spinner("Running simulation..."):
                run_pid_simulation(state)

def render_opc_tab(state):
    st.header("OPC Data Acquisition")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown('<div class="section-header">OPC UA/DA Configuration</div>', unsafe_allow_html=True)
        
        state.opc_endpoint = st.text_input(
            "Endpoint URL",
            value=state.opc_endpoint,
            placeholder="opc.tcp://localhost:4840"
        )
        
        # Connection status
        if state.opc_connected:
            st.success("✅ Connected to OPC Server")
        else:
            st.warning("⚠️ Not Connected")
    
    with col2:
        st.markdown('<div class="section-header">Connection</div>', unsafe_allow_html=True)
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔌 Connect", use_container_width=True, type="primary"):
                state.opc_connected = True
                st.rerun()
        
        with col_b:
            if st.button("🔌 Disconnect", use_container_width=True):
                state.opc_connected = False
                st.rerun()
    
    if state.opc_connected:
        st.markdown('<div class="section-header">Available Tags</div>', unsafe_allow_html=True)
        
        # Mock OPC tags
        tags_data = {
            "Tag": ["Process.PV", "Process.SP", "Controller.OP"],
            "Value": [45.2, 50.0, 62.3],
            "Quality": ["Good", "Good", "Good"],
            "Timestamp": ["2025-10-31 10:15:30"] * 3
        }
        
        df_tags = pd.DataFrame(tags_data)
        st.dataframe(df_tags, use_container_width=True, hide_index=True)

# Helper functions
def identify_model_from_data(state):
    """Identify process model from uploaded data"""
    import io
    
    try:
        from pid_tuner.identify.stepfit import fit_fopdt
        from pid_tuner.identify.sopdtfit import fit_sopdt
        from pid_tuner.identify.intfit import fit_integrator
    except ImportError:
        try:
            from identify.stepfit import fit_fopdt
            from identify.sopdtfit import fit_sopdt
            from identify.intfit import fit_integrator
        except ImportError:
            st.error("Could not import identification modules. Please check your pid_tuner library installation.")
            return
    
    df = pd.read_csv(io.BytesIO(state.uploaded_csv_bytes))
    cols = [c.lower() for c in df.columns]
    df.columns = cols
    
    t = df["t"].to_numpy()
    sp = df["sp"].to_numpy()
    pv = df["pv"].to_numpy()
    
    if state.model_type == "FOPDT":
        K, tau, theta = fit_fopdt(t, sp, pv)
        state.last_fit = {"type": "FOPDT", "K": K, "tau": tau, "theta": theta}
    elif state.model_type == "SOPDT":
        K, tau1, tau2, theta = fit_sopdt(t, sp, pv)
        state.last_fit = {"type": "SOPDT", "K": K, "tau": tau1, "tau2": tau2, "theta": theta}
    else:
        K, leak = fit_integrator(t, sp, pv)
        state.last_fit = {"type": "INTEGRATOR", "K": K, "leak": leak}
    
    st.success("✅ Model identified successfully!")

def apply_identified_model(state):
    """Apply identified model parameters to process"""
    if state.last_fit:
        state.K = state.last_fit.get("K", state.K)
        state.tau = state.last_fit.get("tau", state.tau)
        state.theta = state.last_fit.get("theta", state.theta)
        if "tau2" in state.last_fit:
            state.tau2 = state.last_fit["tau2"]
        st.success("Model parameters applied!")

def calculate_tuning(state, method):
    """Calculate tuning parameters using selected method"""
    try:
        from pid_tuner.tuning.methods import simc_from_model, lambda_from_model, zn_reaction_curve
    except ImportError:
        try:
            from tuning.methods import simc_from_model, lambda_from_model, zn_reaction_curve
        except ImportError:
            st.error("Could not import tuning methods. Please check your pid_tuner library installation.")
            return
    
    if method == "SIMC":
        Kp, Ti, Td = simc_from_model(state.last_fit)
    elif method == "Lambda/IMC":
        Kp, Ti, Td = lambda_from_model(state.last_fit)
    else:
        Kp, Ti, Td = zn_reaction_curve(state.last_fit)
    
    state.calculated_tuning = {"Kp": Kp, "Ti": Ti, "Td": Td}

def create_controller_diagram(state):
    """Create a visual diagram of the controller structure"""
    diagram_html = f"""
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; text-align: center;">
        <h4>PID Controller: {state.mode}</h4>
        <div style="margin: 20px 0;">
            <span style="font-size: 24px;">u(t) = </span>
            <span style="color: #ff4b4b; font-size: 24px; font-weight: bold;">
                Kp·e(t)
            </span>
    """
    
    if state.mode in ["PI", "PID"]:
        diagram_html += """
            <span style="font-size: 24px;"> + </span>
            <span style="color: #4b7bff; font-size: 24px; font-weight: bold;">
                (Kp/Ti)·∫e(t)dt
            </span>
        """
    
    if state.mode == "PID":
        diagram_html += """
            <span style="font-size: 24px;"> + </span>
            <span style="color: #4bff7b; font-size: 24px; font-weight: bold;">
                Kp·Td·de(t)/dt
            </span>
        """
    
    diagram_html += """
        </div>
        <div style="margin-top: 15px; font-size: 14px; color: #666;">
            e(t) = SP - PV (error signal)
        </div>
    </div>
    """
    
    st.markdown(diagram_html, unsafe_allow_html=True)

def run_continuous_simulation(state):
    """Run continuous real-time simulation with live updates"""
    import time
    
    try:
        from streamlit_ui.compat import simulate_closed_loop
    except ImportError:
        try:
            from compat import simulate_closed_loop
        except ImportError:
            st.error("Could not import simulation module. Please check your compat.py file.")
            return
    
    # Create placeholders
    plot_placeholder = st.empty()
    metrics_placeholder = st.empty()
    
    # Status indicator
    status_col1, status_col2 = st.columns([3, 1])
    with status_col1:
        progress_text = st.empty()
    with status_col2:
        if st.button("⏹️ Force Stop", key="force_stop"):
            state.simulation_running = False
            st.rerun()
    
    # Initialize if first run
    if not hasattr(state, 'last_update'):
        state.last_update = time.time()
    
    # Check if we should continue
    if state.simulation_time >= state.horizon:
        state.simulation_running = False
        st.success("✅ Simulation completed!")
        
        # Show final results
        if state.simulation_data["t"]:
            display_final_results(state.simulation_data, state)
        return
    
    # Run simulation chunk
    current_time = time.time()
    real_elapsed = current_time - state.last_update
    sim_elapsed = real_elapsed * state.realtime_speed
    
    # Limit simulation chunk size
    chunk_duration = min(sim_elapsed, 1.0, state.horizon - state.simulation_time)
    
    if chunk_duration > 0.01:  # Only simulate if enough time has passed
        try:
            # Get initial conditions
            y_init = state.y0 if state.simulation_time == 0 else state.simulation_data["y"][-1]
            u_init = state.u0 if state.simulation_time == 0 else state.simulation_data["u"][-1]
            
            # Run simulation chunk
            t, y, sp, u = simulate_closed_loop(
                model_type=state.model_type,
                K=state.K,
                tau=state.tau,
                theta=state.theta,
                tau2=state.tau2,
                leak=state.leak,
                mode=state.mode,
                Kp=state.Kp,
                Ti=state.Ti,
                Td=state.Td,
                beta=state.beta,
                deriv_on=state.deriv_on,
                filt_N=state.filt_N,
                aw_track=state.aw_track,
                umin=state.umin,
                umax=state.umax,
                sp_value=state.sp,
                y0=y_init,
                u0=u_init,
                dt=state.dt,
                horizon=chunk_duration,
            )
            
            # Append data
            t_offset = state.simulation_time
            for i in range(len(t)):
                state.simulation_data["t"].append(t_offset + t[i])
                state.simulation_data["y"].append(y[i])
                state.simulation_data["sp"].append(sp[i])
                state.simulation_data["u"].append(u[i])
            
            state.simulation_time += chunk_duration
            state.last_update = current_time
            
        except Exception as e:
            st.error(f"Simulation error: {str(e)}")
            state.simulation_running = False
            return
    
    # Update display
    if state.simulation_data["t"]:
        # Update plot
        with plot_placeholder.container():
            fig = create_live_plot(state.simulation_data, state)
            st.plotly_chart(fig, use_container_width=True)
        
        # Update metrics
        with metrics_placeholder.container():
            col1, col2, col3, col4 = st.columns(4)
            
            if len(state.simulation_data["t"]) > 1:
                error = np.array(state.simulation_data["y"]) - np.array(state.simulation_data["sp"])
                t_array = np.array(state.simulation_data["t"])
                iae = np.trapz(np.abs(error), t_array)
                ise = np.trapz(error**2, t_array)
                
                col1.metric("Elapsed Time", f"{state.simulation_time:.1f} / {state.horizon:.1f} s")
                col2.metric("IAE", f"{iae:.2f}")
                col3.metric("ISE", f"{ise:.2f}")
                col4.metric("Current PV", f"{state.simulation_data['y'][-1]:.2f}")
        
        # Update progress
        with progress_text:
            progress = (state.simulation_time / state.horizon) * 100
            st.markdown(
                f'<div class="status-connected"></div> **Simulation Running** - {progress:.0f}% complete',
                unsafe_allow_html=True
            )
    
    # Auto-refresh for continuous simulation
    time.sleep(0.1 / state.realtime_speed)  # Small delay based on speed
    st.rerun()

def create_live_plot(data, state):
    """Create live updating plot"""
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("Process Variable vs Setpoint", "Controller Output"),
        vertical_spacing=0.12,
        row_heights=[0.6, 0.4]
    )
    
    # PV and SP
    fig.add_trace(
        go.Scatter(x=data["t"], y=data["y"], name="PV", 
                  line=dict(color="#ff4b4b", width=2),
                  mode='lines'),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=data["t"], y=data["sp"], name="SP", 
                  line=dict(color="#4b7bff", width=2, dash="dash"),
                  mode='lines'),
        row=1, col=1
    )
    
    # Controller output
    fig.add_trace(
        go.Scatter(x=data["t"], y=data["u"], name="OP", 
                  line=dict(color="#4bff7b", width=2),
                  mode='lines'),
        row=2, col=1
    )
    
    # Add output limits
    if data["u"]:
        fig.add_hline(y=state.umax, line_dash="dot", line_color="red", 
                     annotation_text="Max", row=2, col=1)
        fig.add_hline(y=state.umin, line_dash="dot", line_color="red", 
                     annotation_text="Min", row=2, col=1)
    
    fig.update_xaxes(title_text="Time (s)", row=2, col=1)
    fig.update_yaxes(title_text="PV / SP", row=1, col=1)
    fig.update_yaxes(title_text="OP (%)", row=2, col=1)
    
    fig.update_layout(height=600, showlegend=True, hovermode='x unified')
    
    return fig

def display_final_results(data, state):
    """Display final simulation results and metrics"""
    st.markdown('<div class="section-header">Final Results</div>', unsafe_allow_html=True)
    
    # Create final plot
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("Process Variable vs Setpoint", "Controller Output"),
        vertical_spacing=0.12,
        row_heights=[0.6, 0.4]
    )
    
    # PV and SP
    fig.add_trace(
        go.Scatter(x=data["t"], y=data["y"], name="PV", line=dict(color="#ff4b4b", width=2)),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=data["t"], y=data["sp"], name="SP", line=dict(color="#4b7bff", width=2, dash="dash")),
        row=1, col=1
    )
    
    # Controller output
    fig.add_trace(
        go.Scatter(x=data["t"], y=data["u"], name="OP", line=dict(color="#4bff7b", width=2)),
        row=2, col=1
    )
    
    # Add output limits
    fig.add_hline(y=state.umax, line_dash="dot", line_color="red", 
                 annotation_text="Max", row=2, col=1)
    fig.add_hline(y=state.umin, line_dash="dot", line_color="red", 
                 annotation_text="Min", row=2, col=1)
    
    fig.update_xaxes(title_text="Time (s)", row=2, col=1)
    fig.update_yaxes(title_text="PV / SP", row=1, col=1)
    fig.update_yaxes(title_text="OP (%)", row=2, col=1)
    
    fig.update_layout(height=700, showlegend=True, hovermode='x unified')
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Performance metrics
    st.markdown('<div class="section-header">Performance Metrics</div>', unsafe_allow_html=True)
    
    # Calculate metrics
    t = np.array(data["t"])
    y = np.array(data["y"])
    sp = np.array(data["sp"])
    
    error = y - sp
    iae = np.trapz(np.abs(error), t)
    ise = np.trapz(error**2, t)
    settling_time = calculate_settling_time(t, y, sp[-1])
    overshoot = calculate_overshoot(y, sp[-1])
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("IAE", f"{iae:.2f}")
    col2.metric("ISE", f"{ise:.2f}")
    col3.metric("Settling Time", f"{settling_time:.2f} s")
    col4.metric("Overshoot", f"{overshoot:.1f}%")
    
    # Download button
    csv_data = create_csv_export(t, y, sp, data["u"])
    st.download_button(
        "📥 Download Results (CSV)",
        data=csv_data,
        file_name="simulation_results.csv",
        mime="text/csv",
        use_container_width=True
    )

def run_pid_simulation(state):
    """Run closed-loop simulation and display results"""
    try:
        from streamlit_ui.compat import simulate_closed_loop
    except ImportError:
        try:
            from compat import simulate_closed_loop
        except ImportError:
            st.error("Could not import simulation module. Please check your compat.py file.")
            return
    
    try:
        t, y, sp, u = simulate_closed_loop(
            model_type=state.model_type,
            K=state.K,
            tau=state.tau,
            theta=state.theta,
            tau2=state.tau2,
            leak=state.leak,
            mode=state.mode,
            Kp=state.Kp,
            Ti=state.Ti,
            Td=state.Td,
            beta=state.beta,
            deriv_on=state.deriv_on,
            filt_N=state.filt_N,
            aw_track=state.aw_track,
            umin=state.umin,
            umax=state.umax,
            sp_value=state.sp,
            y0=state.y0,
            u0=state.u0,
            dt=state.dt,
            horizon=state.horizon,
        )
        
        # Create comprehensive plot
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=("Process Variable vs Setpoint", "Controller Output"),
            vertical_spacing=0.12,
            row_heights=[0.6, 0.4]
        )
        
        # PV and SP
        fig.add_trace(
            go.Scatter(x=t, y=y, name="PV", line=dict(color="#ff4b4b", width=2)),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=t, y=sp, name="SP", line=dict(color="#4b7bff", width=2, dash="dash")),
            row=1, col=1
        )
        
        # Controller output
        fig.add_trace(
            go.Scatter(x=t, y=u, name="OP", line=dict(color="#4bff7b", width=2)),
            row=2, col=1
        )
        
        # Add output limits
        fig.add_hline(y=state.umax, line_dash="dot", line_color="red", 
                     annotation_text="Max", row=2, col=1)
        fig.add_hline(y=state.umin, line_dash="dot", line_color="red", 
                     annotation_text="Min", row=2, col=1)
        
        fig.update_xaxes(title_text="Time (s)", row=2, col=1)
        fig.update_yaxes(title_text="PV / SP", row=1, col=1)
        fig.update_yaxes(title_text="OP (%)", row=2, col=1)
        
        fig.update_layout(height=700, showlegend=True, hovermode='x unified')
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Performance metrics
        st.markdown('<div class="section-header">Performance Metrics</div>', unsafe_allow_html=True)
        
        # Calculate metrics
        error = y - sp
        iae = np.trapz(np.abs(error), t)
        ise = np.trapz(error**2, t)
        settling_time = calculate_settling_time(t, y, sp[-1])
        overshoot = calculate_overshoot(y, sp[-1])
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("IAE", f"{iae:.2f}")
        col2.metric("ISE", f"{ise:.2f}")
        col3.metric("Settling Time", f"{settling_time:.2f} s")
        col4.metric("Overshoot", f"{overshoot:.1f}%")
        
        # Download button
        csv_data = create_csv_export(t, y, sp, u)
        st.download_button(
            "📥 Download Results (CSV)",
            data=csv_data,
            file_name="simulation_results.csv",
            mime="text/csv",
            use_container_width=True
        )
        
    except Exception as e:
        st.error(f"Simulation error: {str(e)}")

def calculate_settling_time(t, y, sp_final, tolerance=0.02):
    """Calculate 2% settling time"""
    lower_bound = sp_final * (1 - tolerance)
    upper_bound = sp_final * (1 + tolerance)
    
    for i in range(len(y)-1, 0, -1):
        if y[i] < lower_bound or y[i] > upper_bound:
            return t[i]
    return t[-1]

def calculate_overshoot(y, sp_final):
    """Calculate percentage overshoot"""
    max_y = np.max(y)
    if max_y > sp_final:
        return ((max_y - sp_final) / sp_final) * 100
    return 0.0

def create_csv_export(t, y, sp, u):
    """Create CSV data for export"""
    import io
    import csv
    
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Time (s)", "PV", "SP", "OP"])
    for i in range(len(t)):
        writer.writerow([t[i], y[i], sp[i], u[i]])
    
    return buf.getvalue()

if __name__ == "__main__":
    main()