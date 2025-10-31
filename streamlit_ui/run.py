#!/usr/bin/env python3
"""
PID Tuner Streamlit Application Entry Point

Run this file to start the Streamlit web interface:
    python run.py
    
Or use streamlit directly:
    streamlit run streamlit_ui/app.py
"""

import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

if __name__ == "__main__":
    import streamlit.web.cli as stcli
    
    # Get the path to app.py
    app_path = Path(__file__).parent / "app.py"
    
    # Run streamlit
    sys.argv = ["streamlit", "run", str(app_path)]
    sys.exit(stcli.main())