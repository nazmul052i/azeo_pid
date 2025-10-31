# ===========================
# pid_tuner/control/pid.py
# ===========================
"""
PID Controller with Multiple Vendor Implementations

Supports standard ISA and vendor-specific PID algorithms:
- ISA Standard (Series/Parallel forms)
- Emerson DeltaV
- Honeywell Experion
- Yokogawa Centum VP
"""

from dataclasses import dataclass
from typing import Literal
from ..utils.filters import clamp, lowpass


# Vendor algorithm type hints
VendorType = Literal["ISA", "EMERSON", "HONEYWELL", "YOKOGAWA"]
FormType = Literal["P", "PI", "PID"]
DerivType = Literal["PV", "ERROR"]


@dataclass
class PID:
    """
    Universal PID Controller with vendor-specific algorithms.
    
    Attributes:
        Kp: Proportional gain
        Ti: Integral time (seconds)
        Td: Derivative time (seconds)
        N: Derivative filter factor (Td/N = filter time constant)
        umin: Minimum output (%)
        umax: Maximum output (%)
        beta: Setpoint weight for proportional term (0-1)
        form: Controller mode ("P", "PI", "PID")
        deriv_on: Derivative on "PV" or "ERROR"
        vendor: Vendor algorithm ("ISA", "EMERSON", "HONEYWELL", "YOKOGAWA")
        tau_sp: Setpoint filter time constant (0 = disabled)
        tau_pv: PV filter time constant (0 = disabled)
    
    Vendor-Specific Features:
        ISA: Standard series form with beta weighting
        EMERSON: DeltaV with error-squared integral
        HONEYWELL: TDC/Experion with gap action
        YOKOGAWA: Centum with velocity algorithm option
    """
    
    # Tuning parameters
    Kp: float = 1.0
    Ti: float = 1.0
    Td: float = 0.0
    N: float = 10.0
    umin: float = 0.0
    umax: float = 100.0
    
    # Advanced features
    beta: float = 1.0                    # Setpoint weight for P (0-1)
    form: FormType = "PID"               # P, PI, PID
    deriv_on: DerivType = "PV"           # PV or ERROR
    vendor: VendorType = "ISA"           # Vendor algorithm
    
    # Filtering
    tau_sp: float = 0.0                  # Setpoint filter tau
    tau_pv: float = 0.0                  # PV filter tau
    
    # Vendor-specific parameters
    gap: float = 0.0                     # Honeywell gap action (% deadband)
    error_squared: bool = False          # Emerson error-squared integral
    velocity_mode: bool = False          # Yokogawa velocity algorithm
    
    # Internal states
    I: float = 0.0                       # Integral term
    d_filter: float = 0.0                # Derivative filter state
    y_prev: float = 0.0                  # Previous PV
    _e_prev: float = 0.0                 # Previous error
    _sp_prev: float = 0.0                # Filtered SP state
    _pv_prev: float = 0.0                # Filtered PV state
    u: float = 0.0                       # Current output
    u_prev: float = 0.0                  # Previous output (for velocity)

    def reset(self, u0: float = 0.0, I0: float = 0.0):
        """Reset controller to initial state."""
        self.I = I0
        self.d_filter = 0.0
        self.y_prev = 0.0
        self._e_prev = 0.0
        self._sp_prev = 0.0
        self._pv_prev = 0.0
        self.u = u0
        self.u_prev = u0

    def step(self, sp: float, y_meas: float, dt: float) -> float:
        """
        Execute one controller timestep.
        
        Args:
            sp: Setpoint
            y_meas: Measured process variable
            dt: Timestep (seconds)
        
        Returns:
            Controller output (%)
        """
        # Apply filters
        sp_f = lowpass(self._sp_prev, sp, self.tau_sp, dt) if self.tau_sp > 0 else sp
        self._sp_prev = sp_f
        y = lowpass(self._pv_prev, y_meas, self.tau_pv, dt) if self.tau_pv > 0 else y_meas
        self._pv_prev = y

        # Select vendor algorithm
        if self.vendor == "EMERSON":
            u_out = self._step_emerson(sp_f, y, dt)
        elif self.vendor == "HONEYWELL":
            u_out = self._step_honeywell(sp_f, y, dt)
        elif self.vendor == "YOKOGAWA":
            u_out = self._step_yokogawa(sp_f, y, dt)
        else:  # ISA (default)
            u_out = self._step_isa(sp_f, y, dt)
        
        self.u_prev = self.u
        self.u = u_out
        return self.u

    def _step_isa(self, sp: float, y: float, dt: float) -> float:
        """ISA Standard PID (Series form with beta weighting)."""
        e = sp - y
        ep = self.beta * sp - y  # Weighted error for P-term
        
        # Proportional
        P = self.Kp * ep if self.form in ("P", "PI", "PID") else 0.0
        
        # Integral
        if self.form in ("PI", "PID") and self.Ti > 1e-12:
            self.I += self.Kp * (dt / self.Ti) * e
        
        # Derivative
        D = self._compute_derivative_isa(e, y, dt)
        
        # Combine
        u = P + self.I + D
        u_lim = clamp(u, self.umin, self.umax)
        
        # Anti-windup (back-calculation)
        if u != u_lim and self.form in ("PI", "PID") and self.Ti > 1e-12:
            self.I += (u_lim - u)
        
        self.y_prev = y
        self._e_prev = e
        return u_lim

    def _step_emerson(self, sp: float, y: float, dt: float) -> float:
        """
        Emerson DeltaV PID Algorithm.
        
        Features:
        - Error-squared integral (optional)
        - Enhanced anti-windup
        - Derivative on PV with gap
        """
        e = sp - y
        ep = self.beta * sp - y
        
        # Proportional
        P = self.Kp * ep if self.form in ("P", "PI", "PID") else 0.0
        
        # Integral (with optional error-squared)
        if self.form in ("PI", "PID") and self.Ti > 1e-12:
            if self.error_squared:
                # Error-squared integral for better small-error performance
                sign = 1.0 if e >= 0 else -1.0
                self.I += self.Kp * (dt / self.Ti) * sign * (e ** 2) * 0.1
            else:
                self.I += self.Kp * (dt / self.Ti) * e
        
        # Derivative (typically on PV for DeltaV)
        D = self._compute_derivative_isa(e, y, dt)
        
        # Combine
        u = P + self.I + D
        u_lim = clamp(u, self.umin, self.umax)
        
        # Enhanced anti-windup (DeltaV style)
        if self.form in ("PI", "PID") and self.Ti > 1e-12:
            if u != u_lim:
                # Back-calculation with gain
                self.I += 1.0 * (u_lim - u)
        
        self.y_prev = y
        self._e_prev = e
        return u_lim

    def _step_honeywell(self, sp: float, y: float, dt: float) -> float:
        """
        Honeywell TDC/Experion PID Algorithm.
        
        Features:
        - Gap action (deadband)
        - Independent derivative filter
        - Proportional-on-PV option
        """
        e = sp - y
        
        # Gap action (deadband around setpoint)
        if self.gap > 0 and abs(e) < self.gap:
            e_active = 0.0  # Within gap, no P or I action
        else:
            e_active = e
        
        ep = self.beta * sp - y
        
        # Proportional (with gap)
        P = self.Kp * ep if self.form in ("P", "PI", "PID") else 0.0
        if self.gap > 0 and abs(e) < self.gap:
            P = 0.0
        
        # Integral (with gap)
        if self.form in ("PI", "PID") and self.Ti > 1e-12 and abs(e_active) > 0:
            self.I += self.Kp * (dt / self.Ti) * e_active
        
        # Derivative (always on PV for Honeywell)
        D = self._compute_derivative_honeywell(y, dt)
        
        # Combine
        u = P + self.I + D
        u_lim = clamp(u, self.umin, self.umax)
        
        # Anti-windup
        if u != u_lim and self.form in ("PI", "PID") and self.Ti > 1e-12:
            self.I += (u_lim - u)
        
        self.y_prev = y
        self._e_prev = e
        return u_lim

    def _step_yokogawa(self, sp: float, y: float, dt: float) -> float:
        """
        Yokogawa Centum VP PID Algorithm.
        
        Features:
        - Velocity algorithm option (incremental)
        - Derivative-on-PV with lead-lag filter
        - Enhanced bumpless transfer
        """
        e = sp - y
        ep = self.beta * sp - y
        
        if self.velocity_mode:
            # Velocity (incremental) algorithm
            delta_u = self._compute_velocity_output(ep, e, y, dt)
            u = self.u_prev + delta_u
        else:
            # Position algorithm (standard)
            P = self.Kp * ep if self.form in ("P", "PI", "PID") else 0.0
            
            if self.form in ("PI", "PID") and self.Ti > 1e-12:
                self.I += self.Kp * (dt / self.Ti) * e
            
            D = self._compute_derivative_isa(e, y, dt)
            u = P + self.I + D
        
        u_lim = clamp(u, self.umin, self.umax)
        
        # Anti-windup (Yokogawa conditional integration)
        if u != u_lim and self.form in ("PI", "PID") and self.Ti > 1e-12:
            if not self.velocity_mode:
                self.I += (u_lim - u)
        
        self.y_prev = y
        self._e_prev = e
        return u_lim

    def _compute_derivative_isa(self, e: float, y: float, dt: float) -> float:
        """ISA standard derivative with first-order filter."""
        if self.form != "PID" or self.Td <= 0.0:
            return 0.0
        
        if self.deriv_on.upper() == "PV":
            # Derivative on PV (negative, acts against changes)
            dy = (y - self.y_prev) / max(1e-12, dt)
            a = self.Td / (self.Td + self.N * dt)
            self.d_filter = a * self.d_filter - (1 - a) * self.Kp * self.N * self.Td * dy
        else:
            # Derivative on error
            de = (e - self._e_prev) / max(1e-12, dt)
            a = self.Td / (self.Td + self.N * dt)
            self.d_filter = a * self.d_filter + (1 - a) * self.Kp * self.N * self.Td * de
        
        return self.d_filter

    def _compute_derivative_honeywell(self, y: float, dt: float) -> float:
        """Honeywell derivative (always on PV)."""
        if self.form != "PID" or self.Td <= 0.0:
            return 0.0
        
        dy = (y - self.y_prev) / max(1e-12, dt)
        a = self.Td / (self.Td + self.N * dt)
        self.d_filter = a * self.d_filter - (1 - a) * self.Kp * self.Td * dy
        return self.d_filter

    def _compute_velocity_output(self, ep: float, e: float, y: float, dt: float) -> float:
        """Yokogawa velocity (incremental) algorithm."""
        # Proportional change
        delta_p = self.Kp * (ep - (self.beta * self._sp_prev - self.y_prev))
        
        # Integral increment
        delta_i = 0.0
        if self.form in ("PI", "PID") and self.Ti > 1e-12:
            delta_i = self.Kp * (dt / self.Ti) * e
        
        # Derivative increment
        delta_d = 0.0
        if self.form == "PID" and self.Td > 0.0:
            d2y = ((y - self.y_prev) - (self.y_prev - self._e_prev)) / max(1e-12, dt ** 2)
            delta_d = -self.Kp * self.Td * d2y
        
        return delta_p + delta_i + delta_d


def create_emerson_pid(Kp: float, Ti: float, Td: float = 0.0, **kwargs) -> PID:
    """Factory for Emerson DeltaV PID controller."""
    return PID(
        Kp=Kp, Ti=Ti, Td=Td,
        vendor="EMERSON",
        deriv_on="PV",
        beta=1.0,
        **kwargs
    )


def create_honeywell_pid(Kp: float, Ti: float, Td: float = 0.0, gap: float = 0.0, **kwargs) -> PID:
    """Factory for Honeywell Experion PID controller."""
    return PID(
        Kp=Kp, Ti=Ti, Td=Td,
        vendor="HONEYWELL",
        deriv_on="PV",
        gap=gap,
        beta=1.0,
        **kwargs
    )


def create_yokogawa_pid(Kp: float, Ti: float, Td: float = 0.0, velocity: bool = False, **kwargs) -> PID:
    """Factory for Yokogawa Centum VP PID controller."""
    return PID(
        Kp=Kp, Ti=Ti, Td=Td,
        vendor="YOKOGAWA",
        deriv_on="PV",
        velocity_mode=velocity,
        beta=1.0,
        **kwargs
    )