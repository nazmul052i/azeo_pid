#!/usr/bin/env python3
"""
Enhanced PID Tuner Application Runner

Run this file to start the enhanced Streamlit interface:
    python run_enhanced.py
"""

import sys
import subprocess
from pathlib import Path

if __name__ == "__main__":
    # Get the path to enhanced_app.py
    app_path = Path(__file__).parent / "enhanced_app.py"
    
    print("=" * 60)
    print("  Enhanced PID Tuner - INCA-Style Interface")
    print("=" * 60)
    print(f"\nStarting application: {app_path}")
    print("\nFeatures:")
    print("  • Professional tabbed interface")
    print("  • Step-test data acquisition")
    print("  • Automatic model identification")
    print("  • Multiple tuning methods (SIMC, Lambda, Z-N)")
    print("  • Real-time simulation")
    print("  • Performance metrics (IAE, ISE, settling time)")
    print("  • CSV import/export")
    print("  • OPC UA/DA support")
    print("\nOpening in your default browser...")
    print("=" * 60)
    print("\nPress Ctrl+C to stop the server")
    print()
    
    # Run streamlit as subprocess
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", str(app_path),
            "--theme.base", "light",
            "--theme.primaryColor", "#1a73e8"
        ])
    except KeyboardInterrupt:
        print("\n\nApplication stopped by user")
        sys.exit(0)