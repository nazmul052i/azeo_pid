# ===========================
# streamlit_ui/panels/opc_panel_enhanced.py
# ===========================
"""
Enhanced OPC Panel with Full Integration

Connects to OPC DA/UA servers, acquires data, stores in SQLite,
and displays real-time updates.
"""

import streamlit as st
import time
from datetime import datetime
from ..state import SessionState

# Import OPC integration
try:
    from ..opc_integration import init_opc_acquisition, get_opc_acquisition
    OPC_AVAILABLE = True
except ImportError:
    OPC_AVAILABLE = False


def render_enhanced(state: SessionState) -> None:
    """
    Render enhanced OPC panel with full functionality.
    
    Args:
        state: Session state object
    """
    st.header("🔌 OPC Data Acquisition")
    
    if not OPC_AVAILABLE:
        st.error("❌ OPC integration module not available. Check opc_integration.py")
        return
    
    # Initialize OPC acquisition manager
    opc_mgr = init_opc_acquisition(db_path=state.get("db_path", "pid_tuner.db"))
    
    # Create tabs for different protocols
    tab1, tab2, tab3 = st.tabs(["📡 OPC UA", "💾 OPC DA", "📊 Data View"])
    
    # ========== OPC UA Tab ==========
    with tab1:
        render_opc_ua_panel(state, opc_mgr)
    
    # ========== OPC DA Tab ==========
    with tab2:
        render_opc_da_panel(state, opc_mgr)
    
    # ========== Data View Tab ==========
    with tab3:
        render_data_view_panel(state, opc_mgr)


def render_opc_ua_panel(state: SessionState, opc_mgr):
    """Render OPC UA connection and acquisition panel."""
    
    st.markdown("### OPC UA Configuration")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Endpoint configuration
        endpoint = st.text_input(
            "Endpoint URL",
            value=state.get("opc_ua_endpoint", "opc.tcp://localhost:4840"),
            placeholder="opc.tcp://hostname:port"
        )
        state.opc_ua_endpoint = endpoint
        
        # Node mapping
        st.markdown("**Node Mapping**")
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.text("Role")
            pv_role = st.text("PV (Process Variable)")
            sp_role = st.text("SP (Set Point)")
            op_role = st.text("OP (Output)")
        
        with col_b:
            st.text("Node ID")
            pv_node = st.text_input("PV_node", value=state.get("pv_node", "ns=2;s=Process.PV"), 
                                   label_visibility="collapsed")
            sp_node = st.text_input("SP_node", value=state.get("sp_node", "ns=2;s=Process.SP"),
                                   label_visibility="collapsed")
            op_node = st.text_input("OP_node", value=state.get("op_node", "ns=2;s=Controller.OP"),
                                   label_visibility="collapsed")
        
        # Save node mappings
        state.pv_node = pv_node
        state.sp_node = sp_node
        state.op_node = op_node
        
        # Session note
        session_note = st.text_input("Session Note (optional)", 
                                     value=state.get("session_note", ""),
                                     placeholder="Step test for flow loop")
        state.session_note = session_note
    
    with col2:
        # Connection status
        stats = opc_mgr.get_acquisition_stats()
        
        if stats["is_running"] and stats["client_type"] == "UA":
            st.success("✅ Connected & Acquiring")
            st.metric("Samples Collected", stats["sample_count"])
            st.metric("Active Tags", stats["tag_count"])
            
            if st.button("🛑 Stop Acquisition", type="primary", use_container_width=True):
                opc_mgr.stop_acquisition()
                st.rerun()
        else:
            st.warning("⚠️ Not Connected")
            
            if st.button("🔌 Connect & Start", type="primary", use_container_width=True):
                # Build node map
                node_map = {
                    "PV": pv_node,
                    "SP": sp_node,
                    "OP": op_node
                }
                
                # Start session
                session_id = opc_mgr.start_session(note=session_note)
                st.info(f"Started session #{session_id}")
                
                # Connect to OPC UA
                if opc_mgr.connect_opc_ua(endpoint=endpoint, node_map=node_map):
                    st.success("Connected to OPC UA server")
                    
                    # Start acquisition
                    subscription_period = int(state.get("ua_period", 250))
                    opc_mgr.start_opc_ua_acquisition(subscription_period=subscription_period)
                    
                    time.sleep(0.5)  # Give it a moment to start
                    st.rerun()
                else:
                    st.error("Failed to connect to OPC UA server")
        
        # Advanced settings
        with st.expander("⚙️ Advanced Settings"):
            ua_period = st.number_input(
                "Subscription Period (ms)",
                min_value=100,
                max_value=5000,
                value=int(state.get("ua_period", 250)),
                step=50
            )
            state.ua_period = ua_period
    
    # Show live data if acquiring
    if stats["is_running"] and stats["client_type"] == "UA":
        st.markdown("---")
        st.markdown("### 📊 Live Data")
        
        # Create placeholder for live updates
        data_placeholder = st.empty()
        
        # Display latest data
        df = opc_mgr.get_latest_data()
        if not df.empty:
            data_placeholder.dataframe(df, use_container_width=True, hide_index=True)
        
        # Auto-refresh
        if state.get("auto_refresh", True):
            time.sleep(1)
            st.rerun()


def render_opc_da_panel(state: SessionState, opc_mgr):
    """Render OPC DA connection and acquisition panel."""
    
    st.markdown("### OPC DA Configuration")
    
    st.info("📝 **Note**: OPC DA requires OpenOPC and pywin32. Windows only.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Server ProgID
        server_progid = st.text_input(
            "Server ProgID",
            value=state.get("opc_da_progid", "Kepware.KEPServerEX.V6"),
            placeholder="Vendor.Product.Version"
        )
        state.opc_da_progid = server_progid
        
        # Tag mapping
        st.markdown("**Tag Mapping**")
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.text("Role")
            st.text("PV (Process Variable)")
            st.text("SP (Set Point)")
            st.text("OP (Output)")
        
        with col_b:
            st.text("Tag Name")
            pv_tag = st.text_input("PV_tag", value=state.get("pv_tag_da", "Channel1.Device1.PV"),
                                  label_visibility="collapsed")
            sp_tag = st.text_input("SP_tag", value=state.get("sp_tag_da", "Channel1.Device1.SP"),
                                  label_visibility="collapsed")
            op_tag = st.text_input("OP_tag", value=state.get("op_tag_da", "Channel1.Device1.OP"),
                                  label_visibility="collapsed")
        
        state.pv_tag_da = pv_tag
        state.sp_tag_da = sp_tag
        state.op_tag_da = op_tag
        
        # Session note
        session_note = st.text_input("Session Note", 
                                     value=state.get("session_note_da", ""),
                                     placeholder="OPC DA acquisition")
        state.session_note_da = session_note
    
    with col2:
        # Connection status
        stats = opc_mgr.get_acquisition_stats()
        
        if stats["is_running"] and stats["client_type"] == "DA":
            st.success("✅ Connected & Acquiring")
            st.metric("Samples Collected", stats["sample_count"])
            st.metric("Active Tags", stats["tag_count"])
            
            if st.button("🛑 Stop Acquisition", type="primary", use_container_width=True, key="stop_da"):
                opc_mgr.stop_acquisition()
                st.rerun()
        else:
            st.warning("⚠️ Not Connected")
            
            if st.button("🔌 Connect & Start", type="primary", use_container_width=True, key="connect_da"):
                # Build tag map
                tag_map = {
                    "PV": pv_tag,
                    "SP": sp_tag,
                    "OP": op_tag
                }
                
                # Start session
                session_id = opc_mgr.start_session(note=session_note)
                st.info(f"Started session #{session_id}")
                
                # Connect to OPC DA
                if opc_mgr.connect_opc_da(server_progid=server_progid, tags=tag_map):
                    st.success("Connected to OPC DA server")
                    
                    # Start acquisition
                    poll_period = float(state.get("da_poll_period", 0.5))
                    opc_mgr.start_opc_da_acquisition(poll_period=poll_period)
                    
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Failed to connect to OPC DA server")
        
        # Advanced settings
        with st.expander("⚙️ Advanced Settings"):
            da_poll_period = st.number_input(
                "Poll Period (seconds)",
                min_value=0.1,
                max_value=10.0,
                value=float(state.get("da_poll_period", 0.5)),
                step=0.1
            )
            state.da_poll_period = da_poll_period
    
    # Show live data if acquiring
    if stats["is_running"] and stats["client_type"] == "DA":
        st.markdown("---")
        st.markdown("### 📊 Live Data")
        
        data_placeholder = st.empty()
        df = opc_mgr.get_latest_data()
        if not df.empty:
            data_placeholder.dataframe(df, use_container_width=True, hide_index=True)
        
        if state.get("auto_refresh", True):
            time.sleep(1)
            st.rerun()


def render_data_view_panel(state: SessionState, opc_mgr):
    """Render historical data view panel."""
    
    st.markdown("### 📊 Historical Data Viewer")
    
    # Check if we have any sessions
    try:
        from pid_tuner.storage.reader import list_sessions
        
        sessions_df = list_sessions(db_path=state.get("db_path", "pid_tuner.db"))
        
        if sessions_df.empty:
            st.info("No data sessions available yet. Start an acquisition to collect data.")
            return
        
        # Session selection
        st.markdown("**Select Session**")
        
        # Format session display
        sessions_df['display'] = sessions_df.apply(
            lambda row: f"Session #{row['session_id']}: {row['note'] if row['note'] else 'Untitled'} "
                       f"({datetime.fromtimestamp(row['started_utc']).strftime('%Y-%m-%d %H:%M:%S')})",
            axis=1
        )
        
        selected_session_display = st.selectbox(
            "Session",
            options=sessions_df['display'].tolist()
        )
        
        # Get selected session ID
        selected_idx = sessions_df['display'].tolist().index(selected_session_display)
        selected_session_id = int(sessions_df.iloc[selected_idx]['session_id'])
        
        # Get available tags for this session
        from pid_tuner.storage.reader import list_tags
        tags_df = list_tags(db_path=state.get("db_path", "pid_tuner.db"))
        
        if not tags_df.empty:
            selected_tags = st.multiselect(
                "Select Tags to Display",
                options=tags_df['name'].tolist(),
                default=tags_df['name'].tolist()[:3]  # Default to first 3 tags
            )
            
            if selected_tags and st.button("📈 Load Data"):
                # Get session time range
                session_start = float(sessions_df.iloc[selected_idx]['started_utc'])
                session_end = float(sessions_df.iloc[selected_idx]['ended_utc']) if \
                             sessions_df.iloc[selected_idx]['ended_utc'] else time.time()
                
                # Retrieve data
                with st.spinner("Loading data..."):
                    df = opc_mgr.retrieve_session_data(
                        session_id=selected_session_id,
                        tags=selected_tags,
                        start_time=session_start,
                        end_time=session_end
                    )
                
                if not df.empty:
                    st.success(f"Loaded {len(df)} samples")
                    
                    # Display data
                    st.markdown("**Time Series Data**")
                    st.dataframe(df.head(100), use_container_width=True)
                    
                    # Plot data
                    st.markdown("**Trend Plot**")
                    import plotly.graph_objects as go
                    
                    fig = go.Figure()
                    for tag in selected_tags:
                        if tag in df.columns:
                            fig.add_trace(go.Scatter(
                                x=df['ts_utc'],
                                y=df[tag],
                                mode='lines',
                                name=tag
                            ))
                    
                    fig.update_layout(
                        xaxis_title="Time (Unix Timestamp)",
                        yaxis_title="Value",
                        hovermode='x unified',
                        height=400
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Download button
                    csv_data = df.to_csv(index=False)
                    st.download_button(
                        "📥 Download CSV",
                        data=csv_data,
                        file_name=f"session_{selected_session_id}_data.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("No data found for selected tags and time range")
        else:
            st.info("No tags available in database")
            
    except Exception as e:
        st.error(f"Error accessing database: {e}")


# Export the render function
def render(state: SessionState) -> None:
    """Main render function (wrapper for backwards compatibility)."""
    render_enhanced(state)