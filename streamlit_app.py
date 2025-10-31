# ===========================
# streamlit_app.py (root) – updated entry for Streamlit to use new module
# ===========================

# Place this file at the project root, replacing the old one.
# It keeps a single import so `streamlit run streamlit_app.py` continues to work.

# streamlit_app.py
import os, sys, importlib

# --- ensure package import paths ---
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# --- load modular UI ---
_mod = importlib.import_module("streamlit_ui.app")
_mod.main()

