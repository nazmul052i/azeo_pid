# ===========================
# pid_tuner/identify/__init__.py
# ===========================
"""
Process Model Identification from Step Test Data

Fits FOPDT, SOPDT, and Integrator models to experimental step response data.
"""

from .stepfit import fit_fopdt_from_step
from .sopdtfit import fit_sopdt_from_step
from .intfit import fit_integrator_from_step
from .segment import detect_steps_by_diff, cusum_change_points


# === High-level wrappers for consistency with UI expectations ===

def fit_fopdt(t, sp, pv):
    """
    Fit FOPDT model from step test data.
    
    Args:
        t: time array
        sp: setpoint array (or input u)
        pv: process variable array
    
    Returns:
        (K, tau, theta) tuple
    """
    result = fit_fopdt_from_step(t, sp, pv)
    return result['K'], result['tau'], result['theta']


def fit_sopdt(t, sp, pv):
    """
    Fit SOPDT model from step test data.
    
    Args:
        t: time array
        sp: setpoint array (or input u)
        pv: process variable array
    
    Returns:
        (K, tau1, tau2, theta) tuple
    """
    result = fit_sopdt_from_step(t, sp, pv)
    return result['K'], result['tau1'], result['tau2'], result['theta']


def fit_integrator(t, sp, pv):
    """
    Fit integrator model from step test data.
    
    Args:
        t: time array
        sp: setpoint array (or input u)
        pv: process variable array
    
    Returns:
        (K, leak) tuple where K is the integrator gain (slope)
    """
    result = fit_integrator_from_step(t, sp, pv)
    # Return slope (kprime) and leak=0 for compatibility
    return result['kprime'], 0.0


__all__ = [
    # High-level wrappers
    'fit_fopdt',
    'fit_sopdt',
    'fit_integrator',
    
    # Low-level functions
    'fit_fopdt_from_step',
    'fit_sopdt_from_step',
    'fit_integrator_from_step',
    
    # Utilities
    'detect_steps_by_diff',
    'cusum_change_points',
]