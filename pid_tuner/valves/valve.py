# ===========================
# pid_tuner/valves/valve.py
# ===========================
"""
Valve Actuator Models

Implements control valve characteristics and common nonlinearities:
- Flow characteristics (Linear, Equal Percentage, Quick Opening)
- Deadband (mechanical backlash)
- Stiction (stick-slip friction)
- Positioner overshoot
"""

import numpy as np


def characteristic(op_percent: float, characteristic: str = "Linear", R: float = 50.0) -> float:
    """
    Apply valve flow characteristic.
    
    Args:
        op_percent: Valve opening command (0-100%)
        characteristic: "Linear", "Equal Percentage", or "Quick Opening"
        R: Rangeability for equal percentage (default 50:1)
    
    Returns:
        Actual flow percentage (0-100%)
    
    Examples:
        Linear:           flow = opening (most common)
        Equal Percentage: flow = (R^x - 1)/(R-1), high gain near open
        Quick Opening:    flow = √x, high gain near closed
    """
    x = np.clip(op_percent / 100.0, 0.0, 1.0)
    
    if characteristic == "Equal Percentage":
        y = (R**x - 1.0) / (R - 1.0)
    elif characteristic == "Quick Opening":
        y = np.sqrt(x)
    else:  # Linear (default)
        y = x
    
    return 100.0 * y


class ValveActuator:
    """
    Stateful valve actuator with nonlinearities.
    
    Models deadband, stiction, and positioner overshoot.
    Use one instance per valve for proper state management.
    
    Attributes:
        last_output: Previous valve position (%)
        last_delta: Previous position change (%)
    """
    
    def __init__(self):
        self.last_output = 0.0
        self.last_delta = 0.0
    
    def reset(self, position: float = 0.0):
        """Reset valve to initial position."""
        self.last_output = float(np.clip(position, 0.0, 100.0))
        self.last_delta = 0.0
    
    def apply_nonlinearities(self, op: float, *, deadband: float = 0.0,
                            stiction: float = 0.0, pos_overshoot: float = 0.0) -> float:
        """
        Apply valve nonlinearities to controller output.
        
        Args:
            op: Controller output (0-100%)
            deadband: Ignore changes smaller than this (%)
            stiction: Extra force needed to reverse direction (%)
            pos_overshoot: Overshoot on positive moves (%)
        
        Returns:
            Effective valve position (0-100%)
        """
        op = float(np.clip(op, 0.0, 100.0))
        delta = op - self.last_output
        
        # Deadband: ignore small changes
        if abs(delta) < deadband:
            eff = self.last_output
        else:
            # Check for direction reversal (stiction)
            direction_changed = (np.sign(delta) != np.sign(self.last_delta)) and (self.last_delta != 0)
            
            if direction_changed and abs(delta) < stiction:
                # Stuck due to stiction
                eff = self.last_output
            else:
                # Move (possibly with stiction breakthrough)
                eff = self.last_output + delta
                
                # Positioner overshoot (on any movement, not just positive)
                if abs(delta) > deadband and pos_overshoot > 0:
                    eff += np.sign(delta) * pos_overshoot
        
        # Clip final result
        eff = float(np.clip(eff, 0.0, 100.0))
        
        # Update state
        self.last_delta = delta
        self.last_output = eff
        
        return eff


# === Legacy function-based API (backward compatibility) ===

_global_valve_state = ValveActuator()


def apply_deadband_stiction(op: float, prev: float, *, deadband: float = 0.0,
                            stiction: float = 0.0, pos_overshoot: float = 0.0) -> float:
    """
    Apply valve nonlinearities (function-based API).
    
    WARNING: Uses global state. Not thread-safe.
    For multiple valves or concurrent simulations, use ValveActuator class.
    
    Args:
        op: Controller output (0-100%)
        prev: Previous valve position (0-100%)
        deadband: Ignore changes smaller than this (%)
        stiction: Extra force needed to reverse direction (%)
        pos_overshoot: Overshoot on positive moves (%)
    
    Returns:
        Effective valve position (0-100%)
    """
    # Sync global state with prev
    _global_valve_state.last_output = prev
    return _global_valve_state.apply_nonlinearities(
        op, deadband=deadband, stiction=stiction, pos_overshoot=pos_overshoot
    )


def reset_valve_state(position: float = 0.0):
    """Reset global valve state (for function-based API)."""
    _global_valve_state.reset(position)