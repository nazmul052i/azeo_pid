# ===========================
# streamlit_ui/panels/tuner_panel.py
# ===========================
"""
Enhanced Tuner Panel with Complete Data Flow Integration

Provides complete workflow: CSV/OPC Data → SQLite Storage → Identification → Tuning
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Dict, Optional, Tuple

# Import core identification and tuning functions
try:
    from pid_tuner.identify import fit_fopdt, fit_sopdt, fit_integrator
    from pid_tuner.tuning import simc_pi, simc_pid, lambda_fopdt, lambda_integrator
    from pid_tuner.storage.reader import get_series, list_sessions, list_tags
    TUNER_AVAILABLE = True
except ImportError:
    TUNER_AVAILABLE = False


def render(state) -> None:
    """
    Render enhanced tuner panel with complete data flow.
    
    Args:
        state: Session state object
    """
    st.header("🎯 PID Tuner - Complete Workflow")
    
    if not TUNER_AVAILABLE:
        st.error("❌ Tuner modules not available. Install pid_tuner library.")
        return
    
    # Create workflow tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📁 Data Source",
        "🔍 Identification", 
        "⚙️ Tuning",
        "📊 Results"
    ])
    
    # Tab 1: Data Source Selection
    with tab1:
        render_data_source_tab(state)
    
    # Tab 2: Model Identification
    with tab2:
        render_identification_tab(state)
    
    # Tab 3: Controller Tuning
    with tab3:
        render_tuning_tab(state)
    
    # Tab 4: Results and Export
    with tab4:
        render_results_tab(state)


def render_data_source_tab(state) -> None:
    """Render data source selection tab."""
    st.markdown("### Select Data Source")
    
    # Data source selection
    data_source = st.radio(
        "Choose data source:",
        options=["CSV Import", "Database Session", "OPC Live Data"],
        horizontal=True
    )
    
    if data_source == "CSV Import":
        render_csv_import_section(state)
    
    elif data_source == "Database Session":
        render_database_session_section(state)
    
    elif data_source == "OPC Live Data":
        render_opc_live_section(state)


def render_csv_import_section(state) -> None:
    """Render CSV import section."""
    st.markdown("#### Upload CSV File")
    
    uploaded_file = st.file_uploader(
        "Choose CSV file",
        type=['csv'],
        help="CSV must contain: t (time), pv (process variable), sp (setpoint), op/u (output)"
    )
    
    if uploaded_file is not None:
        # Read and validate CSV
        try:
            df = pd.read_csv(uploaded_file)
            df.columns = [c.lower().strip() for c in df.columns]
            
            # Validate required columns
            required = ['t', 'pv']
            if not all(col in df.columns for col in required):
                st.error(f"CSV must contain columns: {', '.join(required)}")
                return
            
            # Store in state
            state.tuner_data = df
            state.tuner_data_source = "CSV"
            
            # Display preview
            st.success(f"✅ Loaded {len(df)} data points")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Duration", f"{df['t'].max() - df['t'].min():.1f} s")
            with col2:
                st.metric("Avg Δt", f"{df['t'].diff().mean():.3f} s")
            with col3:
                st.metric("PV Range", f"{df['pv'].min():.2f} - {df['pv'].max():.2f}")
            
            st.dataframe(df.head(10), use_container_width=True)
            
            # Option to save to database
            if st.checkbox("Save to database for future use"):
                session_note = st.text_input(
                    "Session Description",
                    value=f"CSV Import - {uploaded_file.name}"
                )
                
                if st.button("💾 Save to Database", type="primary"):
                    try:
                        from pid_tuner.storage.writer import SamplesWriter
                        writer = SamplesWriter(db_path=state.get('db_path', 'pid_tuner.db'))
                        session_id = writer.new_session(note=session_note)
                        
                        # Batch insert
                        tag_id_pv = writer.get_tag_id('pv', role='PV')
                        batch = []
                        for idx, row in df.iterrows():
                            batch.append((float(row['t']), tag_id_pv, float(row['pv']), 192, session_id))
                        
                        if 'sp' in df.columns:
                            tag_id_sp = writer.get_tag_id('sp', role='SP')
                            for idx, row in df.iterrows():
                                batch.append((float(row['t']), tag_id_sp, float(row['sp']), 192, session_id))
                        
                        if 'op' in df.columns:
                            tag_id_op = writer.get_tag_id('op', role='OP')
                            for idx, row in df.iterrows():
                                batch.append((float(row['t']), tag_id_op, float(row['op']), 192, session_id))
                        elif 'u' in df.columns:
                            tag_id_u = writer.get_tag_id('u', role='OP')
                            for idx, row in df.iterrows():
                                batch.append((float(row['t']), tag_id_u, float(row['u']), 192, session_id))
                        
                        writer.write_batch(batch)
                        writer.end_session(session_id)
                        
                        st.success(f"✅ Saved to database. Session ID: {session_id}")
                    except Exception as e:
                        st.error(f"Failed to save: {e}")
        
        except Exception as e:
            st.error(f"Error reading CSV: {e}")


def render_database_session_section(state) -> None:
    """Render database session selection section."""
    st.markdown("####  Load from Database")
    
    db_path = state.get('db_path', 'pid_tuner.db')
    
    try:
        # List available sessions
        sessions_df = list_sessions(db_path)
        
        if sessions_df.empty:
            st.info("No sessions found in database. Import CSV data first.")
            return
        
        # Session selector
        selected_session = st.selectbox(
            "Select Session",
            options=sessions_df['session_id'].tolist(),
            format_func=lambda x: f"Session {x}: {sessions_df[sessions_df['session_id']==x]['note'].iloc[0]}"
        )
        
        if selected_session:
            # Display session info
            session = sessions_df[sessions_df['session_id'] == selected_session].iloc[0]
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Session ID", session['session_id'])
            with col2:
                duration = session['ended_utc'] - session['started_utc'] if pd.notna(session['ended_utc']) else 0
                st.metric("Duration", f"{duration:.1f} s")
            
            # Load session data
            if st.button("📂 Load Session Data", type="primary", use_container_width=True):
                with st.spinner("Loading data..."):
                    # Get all tags for this session
                    tags_df = list_tags(db_path)
                    tag_names = tags_df['name'].tolist()
                    
                    # Retrieve data
                    start_time = float(session['started_utc'])
                    end_time = float(session['ended_utc']) if pd.notna(session['ended_utc']) else start_time + 1e9
                    
                    df = get_series(
                        db_path=db_path,
                        tag_names=tag_names,
                        start=start_time,
                        end=end_time
                    )
                    
                    # Rename ts_utc to t if needed
                    if 'ts_utc' in df.columns:
                        df.rename(columns={'ts_utc': 't'}, inplace=True)
                    
                    # Store in state
                    state.tuner_data = df
                    state.tuner_data_source = "Database"
                    state.tuner_session_id = selected_session
                    
                    st.success(f"✅ Loaded {len(df)} data points")
                    st.dataframe(df.head(10), use_container_width=True)
    
    except Exception as e:
        st.error(f"Error loading from database: {e}")


def render_opc_live_section(state) -> None:
    """Render OPC live data section."""
    st.markdown("#### OPC Live Data Acquisition")
    st.info("⚠️ This feature requires active OPC connection. See OPC panel to configure.")
    
    if state.get('opc_connected', False):
        st.success("✅ OPC Server Connected")
        
        # TODO: Implement live data capture from OPC
        st.warning("Live OPC data capture coming soon. Use Database Session to analyze OPC data.")
    else:
        st.warning("❌ No OPC connection. Configure OPC connection first.")


def render_identification_tab(state) -> None:
    """Render model identification tab."""
    st.markdown("### Model Identification")
    
    # Check if data is available
    if not hasattr(state, 'tuner_data') or state.tuner_data is None:
        st.warning("⚠️ No data loaded. Please select a data source first.")
        return
    
    df = state.tuner_data
    
    # Model type selection
    st.markdown("#### Select Process Model Type")
    model_type = st.selectbox(
        "Model Type",
        options=["FOPDT", "SOPDT", "Integrator"],
        help="FOPDT: First Order Plus Dead Time | SOPDT: Second Order Plus Dead Time | Integrator: Integrating Process"
    )
    
    # Get required columns
    col1, col2 = st.columns(2)
    with col1:
        pv_col = st.selectbox("Process Variable (PV)", options=df.columns.tolist(), index=df.columns.tolist().index('pv') if 'pv' in df.columns else 0)
    with col2:
        sp_col = st.selectbox("Setpoint (SP)", options=df.columns.tolist(), index=df.columns.tolist().index('sp') if 'sp' in df.columns else min(1, len(df.columns)-1))
    
    # Plot data
    st.markdown("#### Data Visualization")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['t'], y=df[pv_col], name='PV', line=dict(color='blue')))
    if sp_col in df.columns and sp_col != pv_col:
        fig.add_trace(go.Scatter(x=df['t'], y=df[sp_col], name='SP', line=dict(color='red', dash='dash')))
    
    fig.update_layout(
        title="Process Data",
        xaxis_title="Time (s)",
        yaxis_title="Value",
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Identification button
    if st.button("🔍 Identify Model", type="primary", use_container_width=True):
        with st.spinner(f"Identifying {model_type} model..."):
            try:
                t = df['t'].to_numpy()
                pv = df[pv_col].to_numpy()
                sp = df[sp_col].to_numpy() if sp_col in df.columns else np.ones_like(pv) * pv[0]
                
                if model_type == "FOPDT":
                    K, tau, theta = fit_fopdt(t, sp, pv)
                    state.identified_model = {
                        'type': 'FOPDT',
                        'K': K,
                        'tau': tau,
                        'theta': theta
                    }
                    st.success(f"✅ FOPDT Model Identified: K={K:.3f}, τ={tau:.3f}, θ={theta:.3f}")
                
                elif model_type == "SOPDT":
                    K, tau1, tau2, theta = fit_sopdt(t, sp, pv)
                    state.identified_model = {
                        'type': 'SOPDT',
                        'K': K,
                        'tau1': tau1,
                        'tau2': tau2,
                        'theta': theta
                    }
                    st.success(f"✅ SOPDT Model Identified: K={K:.3f}, τ₁={tau1:.3f}, τ₂={tau2:.3f}, θ={theta:.3f}")
                
                else:  # Integrator
                    K, leak = fit_integrator(t, sp, pv)
                    state.identified_model = {
                        'type': 'Integrator',
                        'K': K,
                        'leak': leak
                    }
                    st.success(f"✅ Integrator Model Identified: K={K:.3f}, leak={leak:.3f}")
                
                st.balloons()
            
            except Exception as e:
                st.error(f"Identification failed: {e}")
                import traceback
                st.code(traceback.format_exc())


def render_tuning_tab(state) -> None:
    """Render controller tuning tab."""
    st.markdown("### Controller Tuning")
    
    # Check if model is identified
    if not hasattr(state, 'identified_model') or state.identified_model is None:
        st.warning("⚠️ No model identified. Please complete identification first.")
        return
    
    model = state.identified_model
    
    # Display identified model
    st.markdown("#### Identified Model")
    if model['type'] == 'FOPDT':
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Gain (K)", f"{model['K']:.3f}")
        with col2:
            st.metric("Time Constant (τ)", f"{model['tau']:.3f} s")
        with col3:
            st.metric("Dead Time (θ)", f"{model['theta']:.3f} s")
    
    elif model['type'] == 'SOPDT':
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Gain (K)", f"{model['K']:.3f}")
        with col2:
            st.metric("τ₁", f"{model['tau1']:.3f} s")
        with col3:
            st.metric("τ₂", f"{model['tau2']:.3f} s")
        with col4:
            st.metric("Dead Time (θ)", f"{model['theta']:.3f} s")
    
    else:  # Integrator
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Gain (K)", f"{model['K']:.3f}")
        with col2:
            st.metric("Leak", f"{model['leak']:.3f}")
    
    # Tuning method selection
    st.markdown("#### Select Tuning Method")
    
    if model['type'] == 'Integrator':
        tuning_method = st.selectbox(
            "Tuning Method",
            options=["Lambda (IMC)", "SIMC"],
            help="Lambda and SIMC are recommended for integrating processes"
        )
    else:
        tuning_method = st.selectbox(
            "Tuning Method",
            options=["SIMC PI", "SIMC PID", "Lambda PI", "Lambda PID"],
            help="SIMC is recommended for self-regulating processes"
        )
    
    # Controller type
    controller_form = st.radio(
        "Controller Form",
        options=["PI", "PID"],
        horizontal=True
    )
    
    # Tuning parameter (tau_c / lambda)
    if "Lambda" in tuning_method:
        param_name = "Lambda (λ)"
        default_value = model.get('theta', 1.0) if model['type'] != 'Integrator' else 1.0
    else:  # SIMC
        param_name = "Closed-Loop Time Constant (τc)"
        default_value = model.get('theta', 1.0) if model['type'] != 'Integrator' else model.get('tau', 1.0)
    
    tuning_param = st.number_input(
        param_name,
        min_value=0.1,
        value=float(default_value),
        step=0.1,
        format="%.2f",
        help="Smaller values = faster response, larger values = more robust"
    )
    
    # Calculate tuning button
    if st.button("⚙️ Calculate Tuning Parameters", type="primary", use_container_width=True):
        with st.spinner("Calculating tuning parameters..."):
            try:
                if model['type'] == 'FOPDT':
                    K, tau, theta = model['K'], model['tau'], model['theta']
                    
                    if "SIMC" in tuning_method:
                        if controller_form == "PI":
                            Kp, Ti, Td = simc_pi(K=K, tau=tau, theta=theta, tau_c=tuning_param)
                        else:  # PID
                            Kp, Ti, Td = simc_pid(K=K, tau=tau, theta=theta, tau_c=tuning_param)
                    
                    else:  # Lambda
                        Kp, Ti, Td = lambda_fopdt(K=K, tau=tau, theta=theta, lambda_=tuning_param)
                        if controller_form == "PI":
                            Td = 0.0
                
                elif model['type'] == 'Integrator':
                    K = model['K']
                    
                    if "Lambda" in tuning_method:
                        Kp, Ti = lambda_integrator(K=K, lambda_=tuning_param)
                        Td = 0.0
                    else:  # SIMC
                        from pid_tuner.tuning import simc_integrating
                        Kp, Ti = simc_integrating(K=K, tau_c=tuning_param)
                        Td = 0.0
                
                else:  # SOPDT
                    K, tau1, tau2, theta = model['K'], model['tau1'], model['tau2'], model['theta']
                    
                    # For SOPDT, use equivalent FOPDT
                    tau_eq = tau1 + tau2
                    theta_eq = theta
                    
                    if "SIMC" in tuning_method:
                        if controller_form == "PI":
                            Kp, Ti, Td = simc_pi(K=K, tau=tau_eq, theta=theta_eq, tau_c=tuning_param)
                        else:
                            Kp, Ti, Td = simc_pid(K=K, tau=tau_eq, theta=theta_eq, tau_c=tuning_param)
                    else:
                        Kp, Ti, Td = lambda_fopdt(K=K, tau=tau_eq, theta=theta_eq, lambda_=tuning_param)
                        if controller_form == "PI":
                            Td = 0.0
                
                # Store tuning results
                state.tuning_results = {
                    'Kp': Kp,
                    'Ti': Ti,
                    'Td': Td,
                    'method': tuning_method,
                    'form': controller_form
                }
                
                st.success("✅ Tuning parameters calculated!")
                
                # Display results
                st.markdown("#### Tuning Parameters")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Proportional Gain (Kp)", f"{Kp:.4f}")
                with col2:
                    st.metric("Integral Time (Ti)", f"{Ti:.4f} s" if Ti > 0 else "N/A")
                with col3:
                    st.metric("Derivative Time (Td)", f"{Td:.4f} s" if Td > 0 else "N/A")
            
            except Exception as e:
                st.error(f"Tuning calculation failed: {e}")
                import traceback
                st.code(traceback.format_exc())


def render_results_tab(state) -> None:
    """Render results and export tab."""
    st.markdown("### Results Summary")
    
    # Check if tuning is complete
    if not hasattr(state, 'tuning_results') or state.tuning_results is None:
        st.warning("⚠️ No tuning results available. Complete identification and tuning first.")
        return
    
    # Display complete workflow results
    st.markdown("#### Complete Workflow Summary")
    
    # Data source
    if hasattr(state, 'tuner_data_source'):
        st.info(f"📁 Data Source: {state.tuner_data_source}")
    
    # Identified model
    if hasattr(state, 'identified_model'):
        model = state.identified_model
        st.markdown("**🔍 Identified Model:**")
        st.json(model)
    
    # Tuning results
    results = state.tuning_results
    st.markdown("**⚙️ Tuning Results:**")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Kp", f"{results['Kp']:.4f}")
    with col2:
        st.metric("Ti", f"{results['Ti']:.4f} s" if results['Ti'] > 0 else "N/A")
    with col3:
        st.metric("Td", f"{results['Td']:.4f} s" if results['Td'] > 0 else "N/A")
    
    st.info(f"Method: {results['method']} | Form: {results['form']}")
    
    # Export options
    st.markdown("#### Export Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📋 Copy to Clipboard", use_container_width=True):
            export_text = f"""PID Tuning Results
Method: {results['method']}
Form: {results['form']}

Proportional Gain (Kp): {results['Kp']:.4f}
Integral Time (Ti): {results['Ti']:.4f} s
Derivative Time (Td): {results['Td']:.4f} s

Model: {model['type']}
{model}
"""
            st.code(export_text)
            st.success("✅ Results formatted for copying")
    
    with col2:
        if st.button("💾 Save to File", use_container_width=True):
            # Create export data
            export_data = {
                'tuning_results': results,
                'identified_model': state.identified_model if hasattr(state, 'identified_model') else None,
                'data_source': state.tuner_data_source if hasattr(state, 'tuner_data_source') else None,
            }
            
            import json
            json_str = json.dumps(export_data, indent=2)
            
            st.download_button(
                label="📥 Download JSON",
                data=json_str,
                file_name="pid_tuning_results.json",
                mime="application/json",
                use_container_width=True
            )
    
    # Apply to simulator
    st.markdown("#### Apply to Simulator")
    if st.button("▶️ Apply to Simulation", type="primary", use_container_width=True):
        # Update simulation state with tuning parameters
        state.Kp = results['Kp']
        state.Ti = results['Ti']
        state.Td = results['Td']
        state.form = results['form']
        
        st.success("✅ Tuning parameters applied to simulator!")
        st.info("Go to Simulation tab to test these parameters")