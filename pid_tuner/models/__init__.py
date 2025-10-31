# ===========================
# pid_tuner/models/processes.py → __init__.py
# ===========================
"""
Process Dynamics Models

Numerical simulation models for common process control systems:
- FOPDT: First-order plus dead time
- SOPDT: Second-order plus dead time  
- IntegratorLeak: Integrating process with optional leak term

All models use Euler integration with mutable state.
"""

from .processes import (
    ProcessBase,
    FOPDT,
    SOPDT,
    IntegratorLeak,
)

__all__ = [
    'ProcessBase',
    'FOPDT',
    'SOPDT',
    'IntegratorLeak',
]