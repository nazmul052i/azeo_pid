# ===========================
# Enhanced Styles for PID Tuner
# ===========================

import streamlit as st

ENHANCED_CSS = """
<style>
/* Global Styles */
.main {
    background-color: #f5f7fa;
}

/* Tab Styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 3px;
    background-color: #e8eaed;
    padding: 5px;
    border-radius: 8px;
}

.stTabs [data-baseweb="tab"] {
    height: 55px;
    padding: 10px 25px;
    background-color: #ffffff;
    border-radius: 6px 6px 0 0;
    font-weight: 500;
    font-size: 14px;
    color: #5f6368;
    border: none;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.stTabs [aria-selected="true"] {
    background-color: #ffffff;
    color: #1a73e8;
    border-top: 4px solid #1a73e8;
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
}

/* Metric Cards */
.metric-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    margin: 10px 0;
}

.metric-card strong {
    font-size: 13px;
    opacity: 0.9;
}

/* Section Headers */
.section-header {
    background: linear-gradient(90deg, #1a73e8 0%, #4285f4 100%);
    color: white;
    padding: 12px 20px;
    border-radius: 8px;
    font-weight: 600;
    font-size: 16px;
    margin: 20px 0 15px 0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

/* Buttons */
.stButton > button {
    border-radius: 6px;
    font-weight: 500;
    border: none;
    transition: all 0.3s ease;
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
}

/* Primary Button */
button[kind="primary"] {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* Input Fields */
.stNumberInput > div > div > input,
.stTextInput > div > div > input,
.stSelectbox > div > div > select {
    border-radius: 6px;
    border: 2px solid #e0e0e0;
    padding: 8px 12px;
    transition: border-color 0.3s ease;
}

.stNumberInput > div > div > input:focus,
.stTextInput > div > div > input:focus,
.stSelectbox > div > div > select:focus {
    border-color: #1a73e8;
    box-shadow: 0 0 0 3px rgba(26, 115, 232, 0.1);
}

/* Dataframes */
.stDataFrame {
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

/* Success/Error/Warning/Info Messages */
.stSuccess, .stError, .stWarning, .stInfo {
    border-radius: 8px;
    padding: 15px;
    margin: 10px 0;
}

.stSuccess {
    background-color: #d4edda;
    border-left: 4px solid #28a745;
}

.stError {
    background-color: #f8d7da;
    border-left: 4px solid #dc3545;
}

.stWarning {
    background-color: #fff3cd;
    border-left: 4px solid #ffc107;
}

.stInfo {
    background-color: #d1ecf1;
    border-left: 4px solid #17a2b8;
}

/* Sidebar */
.css-1d391kg {
    background-color: #f8f9fa;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #ffffff 0%, #f5f7fa 100%);
}

/* Metrics Display */
[data-testid="stMetricValue"] {
    font-size: 28px;
    font-weight: 700;
    color: #1a73e8;
}

[data-testid="stMetricLabel"] {
    font-size: 14px;
    font-weight: 500;
    color: #5f6368;
}

/* File Uploader */
[data-testid="stFileUploader"] {
    border: 2px dashed #1a73e8;
    border-radius: 8px;
    padding: 20px;
    background-color: #f8f9fa;
    transition: all 0.3s ease;
}

[data-testid="stFileUploader"]:hover {
    background-color: #e8f0fe;
    border-color: #4285f4;
}

/* Radio Buttons */
.stRadio > div {
    flex-direction: row;
    gap: 10px;
}

.stRadio > div > label {
    background-color: #f8f9fa;
    padding: 10px 20px;
    border-radius: 6px;
    border: 2px solid #e0e0e0;
    cursor: pointer;
    transition: all 0.3s ease;
}

.stRadio > div > label:hover {
    background-color: #e8f0fe;
    border-color: #1a73e8;
}

/* Checkboxes */
.stCheckbox > label {
    font-weight: 500;
    color: #202124;
}

/* Sliders */
.stSlider > div > div > div {
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
}

/* Expander */
.streamlit-expanderHeader {
    background-color: #f8f9fa;
    border-radius: 6px;
    font-weight: 600;
    color: #202124;
}

.streamlit-expanderHeader:hover {
    background-color: #e8eaed;
}

/* Table Styling */
table {
    border-collapse: separate;
    border-spacing: 0;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

thead tr {
    background: linear-gradient(90deg, #1a73e8 0%, #4285f4 100%);
    color: white;
}

thead th {
    padding: 15px;
    font-weight: 600;
    text-align: left;
}

tbody tr {
    background-color: white;
}

tbody tr:nth-child(even) {
    background-color: #f8f9fa;
}

tbody td {
    padding: 12px 15px;
    border-bottom: 1px solid #e0e0e0;
}

tbody tr:hover {
    background-color: #e8f0fe;
}

/* Controller Diagram Box */
.controller-diagram {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 30px;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    text-align: center;
    margin: 20px 0;
}

/* Signal Flow Diagram */
.signal-flow {
    background-color: white;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    padding: 20px;
    margin: 15px 0;
}

.signal-box {
    display: inline-block;
    background-color: #e8f0fe;
    border: 2px solid #1a73e8;
    border-radius: 6px;
    padding: 10px 20px;
    margin: 5px;
    font-weight: 600;
    color: #1a73e8;
}

/* Status Indicators */
.status-connected {
    display: inline-block;
    width: 12px;
    height: 12px;
    background-color: #28a745;
    border-radius: 50%;
    margin-right: 8px;
    animation: pulse 2s infinite;
}

.status-disconnected {
    display: inline-block;
    width: 12px;
    height: 12px;
    background-color: #dc3545;
    border-radius: 50%;
    margin-right: 8px;
}

@keyframes pulse {
    0%, 100% {
        opacity: 1;
    }
    50% {
        opacity: 0.5;
    }
}

/* Plot Container */
.js-plotly-plot {
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

/* Loading Spinner */
.stSpinner > div {
    border-top-color: #1a73e8!important;
}

/* Scrollbar */
::-webkit-scrollbar {
    width: 10px;
    height: 10px;
}

::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 5px;
}

::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    border-radius: 5px;
}

::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(180deg, #764ba2 0%, #667eea 100%);
}

/* Responsive Design */
@media (max-width: 768px) {
    .section-header {
        font-size: 14px;
        padding: 10px 15px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        padding: 8px 15px;
        font-size: 12px;
    }
}
</style>
"""

def inject_enhanced_css():
    """Inject enhanced CSS styling"""
    st.markdown(ENHANCED_CSS, unsafe_allow_html=True)

# Color palette for consistent theming
COLORS = {
    "primary": "#1a73e8",
    "secondary": "#4285f4",
    "success": "#28a745",
    "danger": "#dc3545",
    "warning": "#ffc107",
    "info": "#17a2b8",
    "light": "#f8f9fa",
    "dark": "#202124",
    "gradient_start": "#667eea",
    "gradient_end": "#764ba2"
}

def get_color(name: str) -> str:
    """Get color from palette"""
    return COLORS.get(name, COLORS["primary"])