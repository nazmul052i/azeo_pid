"""
PID Tuner - A comprehensive PID control library for process control applications.

Main Components:
- Control: PID controller implementation
- Models: Process models (FOPDT, SOPDT, Integrator)
- Tuning: Various tuning methods (SIMC, Lambda, Ziegler-Nichols, Cohen-Coon)
- Simulate: Simulation tools
- Identify: System identification from step test data
- Storage: Data logging and retrieval
- OPC: OPC DA/UA client connectivity
"""

__version__ = "1.0.0"
__author__ = "PID Tuner Development Team"

# Core exports - import commonly used classes/functions
from pid_tuner.control.pid import PID
from pid_tuner.models.processes import FOPDT, SOPDT, IntegratorLeak
from pid_tuner.simulate.sim import simulate
from pid_tuner.simulate.realtime import simulate_realtime
from pid_tuner.identify.stepfit import fit_fopdt_from_step

__all__ = [
    # Control
    'PID',
    
    # Models
    'FOPDT',
    'SOPDT',
    'IntegratorLeak',
    
    # Simulation
    'simulate',
    'simulate_realtime',
    
    # Identification
    'fit_fopdt_from_step',
]