# ===========================
# pid_tuner/tuning/__init__.py
# ===========================
"""
PID Controller Tuning Methods

Implements Lambda/IMC and SIMC tuning rules for FOPDT, SOPDT,
and integrating processes.
"""

from .simc import (
    simc_pi_fopdt,
    simc_pid_sopdt,
    simc_integrator,
    simc_tau_c_recommendation,
)

from .lambda_method import (
    lambda_fopdt,
    lambda_integrator,
)

from .methods import (
    imc_lambda_fopdt,
    lambda_integrating,
    simc_pi,
    simc_pid,
    simc_integrating,
    simc_tau_c,
)

__all__ = [
    # SIMC methods
    'simc_pi_fopdt',
    'simc_pid_sopdt',
    'simc_integrator',
    'simc_tau_c_recommendation',
    # Lambda/IMC methods
    'lambda_fopdt',
    'lambda_integrator',
    # Convenience wrappers
    'imc_lambda_fopdt',
    'lambda_integrating',
    'simc_pi',
    'simc_pid',
    'simc_integrating',
    'simc_tau_c',
]