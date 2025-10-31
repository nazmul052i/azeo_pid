# ===========================
# pid_tuner/control/__init__.py
# ===========================
"""
PID Controller Module

Provides PID controller implementation with support for:
- P, PI, and PID control modes
- Derivative on PV or Error
- Anti-windup protection
- Setpoint and PV filtering
- Configurable setpoint weighting (beta)

Vendor-Specific Algorithms:
- ISA Standard (default)
- Emerson DeltaV (error-squared integral)
- Honeywell Experion (gap action)
- Yokogawa Centum VP (velocity mode)
"""

from .pid import (
    PID,
    create_emerson_pid,
    create_honeywell_pid,
    create_yokogawa_pid,
)

__all__ = [
    'PID',
    'create_emerson_pid',
    'create_honeywell_pid',
    'create_yokogawa_pid',
]

__version__ = '2.0.0'