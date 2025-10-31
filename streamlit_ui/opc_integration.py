# ===========================
# streamlit_ui/opc_integration.py
# ===========================
"""
OPC Integration Module for Streamlit UI

Provides a bridge between OPC clients (DA/UA), SQLite storage, and Streamlit UI.
Handles connection management, data acquisition, and real-time updates.
"""

import streamlit as st
import threading
import time
import asyncio
from typing import Dict, List, Optional, Callable
from datetime import datetime
import pandas as pd

# Import core library
try:
    from pid_tuner.opc.da_client import DaPoller
    from pid_tuner.opc.ua_client import UaAcquirer
    from pid_tuner.storage.writer import SamplesWriter
    from pid_tuner.storage.reader import get_series, list_sessions, list_tags
except ImportError as e:
    st.error(f"Failed to import OPC/Storage modules: {e}")
    DaPoller = None
    UaAcquirer = None
    SamplesWriter = None


class OPCDataAcquisition:
    """
    Manages OPC data acquisition with SQLite storage integration.
    Supports both OPC DA and OPC UA protocols.
    """
    
    def __init__(self, db_path: str = "pid_tuner.db"):
        """
        Initialize OPC data acquisition manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.writer: Optional[SamplesWriter] = None
        self.session_id: Optional[int] = None
        self.is_running = False
        self.acquisition_thread: Optional[threading.Thread] = None
        self.opc_client = None
        self.client_type: Optional[str] = None  # 'DA' or 'UA'
        
        # Data buffers for UI updates
        self.latest_values: Dict[str, float] = {}
        self.latest_qualities: Dict[str, str] = {}
        self.latest_timestamps: Dict[str, str] = {}
        self.sample_count = 0
        
    def initialize_storage(self):
        """Initialize SQLite storage writer."""
        if self.writer is None:
            self.writer = SamplesWriter(db_path=self.db_path)
            
    def start_session(self, note: str = "") -> int:
        """
        Start a new data acquisition session.
        
        Args:
            note: Optional note/description for the session
            
        Returns:
            session_id: Unique identifier for this session
        """
        self.initialize_storage()
        self.session_id = self.writer.new_session(note=note)
        return self.session_id
    
    def end_session(self):
        """End the current data acquisition session."""
        if self.writer and self.session_id:
            self.writer.end_session(self.session_id)
            
    def _quality_code_to_string(self, quality: int) -> str:
        """Convert OPC quality code to readable string."""
        # OPC UA quality codes (simplified)
        if quality == 192 or quality == 0:  # Good
            return "Good"
        elif quality >= 64 and quality < 128:  # Uncertain
            return "Uncertain"
        else:
            return "Bad"
    
    def _on_sample_callback(self, ts: float, tag: str, value: float, quality: int):
        """
        Callback for OPC data samples.
        Stores to database and updates UI buffers.
        
        Args:
            ts: Unix timestamp
            tag: Tag name or node ID
            value: Measured value
            quality: Quality code
        """
        # Write to database
        if self.writer and self.session_id:
            self.writer.write_sample(
                ts=ts,
                tag=tag,
                value=value,
                quality=quality,
                session_id=self.session_id
            )
        
        # Update UI buffers
        self.latest_values[tag] = value
        self.latest_qualities[tag] = self._quality_code_to_string(quality)
        self.latest_timestamps[tag] = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        self.sample_count += 1
    
    # ========== OPC DA Methods ==========
    
    def connect_opc_da(self, server_progid: str, tags: Dict[str, str]) -> bool:
        """
        Connect to OPC DA server.
        
        Args:
            server_progid: OPC DA server ProgID (e.g., "Kepware.KEPServerEX.V6")
            tags: Dictionary mapping role to tag name
                  e.g., {"PV": "Channel1.Device1.PV", "SP": "Channel1.Device1.SP"}
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            if DaPoller is None:
                st.error("OPC DA support not available. Install OpenOPC and pywin32.")
                return False
            
            self.opc_client = DaPoller(
                server_progid=server_progid,
                tags=tags,
                on_sample=self._on_sample_callback
            )
            
            # Try to connect
            self.opc_client.connect()
            self.client_type = 'DA'
            return True
            
        except Exception as e:
            st.error(f"Failed to connect to OPC DA server: {e}")
            return False
    
    def start_opc_da_acquisition(self, poll_period: float = 0.5):
        """
        Start OPC DA data acquisition in background thread.
        
        Args:
            poll_period: Polling interval in seconds
        """
        if self.opc_client and self.client_type == 'DA':
            self.is_running = True
            
            def poll_loop():
                try:
                    self.opc_client.poll_loop(period_s=poll_period)
                except Exception as e:
                    st.error(f"OPC DA polling error: {e}")
                    self.is_running = False
            
            self.acquisition_thread = threading.Thread(target=poll_loop, daemon=True)
            self.acquisition_thread.start()
    
    # ========== OPC UA Methods ==========
    
    def connect_opc_ua(self, endpoint: str, node_map: Dict[str, str]) -> bool:
        """
        Connect to OPC UA server.
        
        Args:
            endpoint: OPC UA endpoint URL (e.g., "opc.tcp://localhost:4840")
            node_map: Dictionary mapping role to node ID
                     e.g., {"PV": "ns=2;s=Process.PV", "SP": "ns=2;s=Process.SP"}
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            if UaAcquirer is None:
                st.error("OPC UA support not available. Install asyncua.")
                return False
            
            self.opc_client = UaAcquirer(
                endpoint=endpoint,
                node_map=node_map,
                on_sample=self._on_sample_callback
            )
            
            self.client_type = 'UA'
            return True
            
        except Exception as e:
            st.error(f"Failed to configure OPC UA client: {e}")
            return False
    
    def start_opc_ua_acquisition(self, subscription_period: int = 250):
        """
        Start OPC UA data acquisition in background thread.
        
        Args:
            subscription_period: Subscription period in milliseconds
        """
        if self.opc_client and self.client_type == 'UA':
            self.is_running = True
            
            def async_loop():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.opc_client.run(period_ms=subscription_period))
                except Exception as e:
                    st.error(f"OPC UA acquisition error: {e}")
                    self.is_running = False
            
            self.acquisition_thread = threading.Thread(target=async_loop, daemon=True)
            self.acquisition_thread.start()
    
    # ========== Common Methods ==========
    
    def stop_acquisition(self):
        """Stop data acquisition."""
        self.is_running = False
        
        if self.client_type == 'UA' and self.opc_client:
            # Stop UA client gracefully
            async def stop_ua():
                await self.opc_client.stop()
            
            try:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(stop_ua())
            except:
                pass
        
        # Wait for thread to finish
        if self.acquisition_thread and self.acquisition_thread.is_alive():
            self.acquisition_thread.join(timeout=2.0)
        
        self.acquisition_thread = None
        self.opc_client = None
    
    def disconnect(self):
        """Disconnect from OPC server."""
        self.stop_acquisition()
        self.end_session()
        
        if self.writer:
            self.writer.close()
            self.writer = None
    
    def get_latest_data(self) -> pd.DataFrame:
        """
        Get latest acquired data for display in UI.
        
        Returns:
            DataFrame with columns: Tag, Value, Quality, Timestamp
        """
        if not self.latest_values:
            return pd.DataFrame(columns=["Tag", "Value", "Quality", "Timestamp"])
        
        data = {
            "Tag": list(self.latest_values.keys()),
            "Value": [f"{v:.2f}" for v in self.latest_values.values()],
            "Quality": [self.latest_qualities.get(k, "Unknown") for k in self.latest_values.keys()],
            "Timestamp": [self.latest_timestamps.get(k, "") for k in self.latest_values.keys()]
        }
        
        return pd.DataFrame(data)
    
    def get_acquisition_stats(self) -> Dict[str, any]:
        """
        Get acquisition statistics.
        
        Returns:
            Dictionary with stats
        """
        return {
            "is_running": self.is_running,
            "session_id": self.session_id,
            "sample_count": self.sample_count,
            "tag_count": len(self.latest_values),
            "client_type": self.client_type
        }
    
    def retrieve_session_data(self, session_id: int, 
                             tags: List[str], 
                             start_time: float, 
                             end_time: float) -> pd.DataFrame:
        """
        Retrieve historical data from SQLite database.
        
        Args:
            session_id: Session ID to retrieve
            tags: List of tag names to retrieve
            start_time: Start time (Unix timestamp)
            end_time: End time (Unix timestamp)
            
        Returns:
            DataFrame with time series data
        """
        try:
            df = get_series(
                db_path=self.db_path,
                tag_names=tags,
                start=start_time,
                end=end_time
            )
            return df
        except Exception as e:
            st.error(f"Failed to retrieve session data: {e}")
            return pd.DataFrame()


# ========== Helper Functions for Streamlit ==========

def init_opc_acquisition(db_path: str = "pid_tuner.db") -> OPCDataAcquisition:
    """
    Initialize OPC data acquisition manager in session state.
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        OPCDataAcquisition instance
    """
    if 'opc_acquisition' not in st.session_state:
        st.session_state.opc_acquisition = OPCDataAcquisition(db_path=db_path)
    
    return st.session_state.opc_acquisition


def get_opc_acquisition() -> Optional[OPCDataAcquisition]:
    """Get OPC acquisition manager from session state."""
    return st.session_state.get('opc_acquisition', None)