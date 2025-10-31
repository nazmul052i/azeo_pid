
from dataclasses import dataclass

@dataclass
class ProcessBase:
    y: float = 0.0
    def reset(self, y0: float = 0.0): self.y = y0
    def step(self, u: float, d: float, dt: float) -> float: raise NotImplementedError

@dataclass
class FOPDT(ProcessBase):
    K: float = 1.0
    tau: float = 5.0
    def step(self, u: float, d: float, dt: float) -> float:
        dydt = (-self.y + self.K*u + d) / max(1e-9, self.tau)
        self.y += dt * dydt
        return self.y

@dataclass
class SOPDT(ProcessBase):
    K: float = 1.0
    tau1: float = 3.0
    tau2: float = 5.0
    dy: float = 0.0
    def step(self, u: float, d: float, dt: float) -> float:
        a = max(1e-9, self.tau1*self.tau2)
        b = self.tau1 + self.tau2
        d2y = (self.K*u + d - self.y - b*self.dy) / a
        self.dy += dt * d2y
        self.y  += dt * self.dy
        return self.y

@dataclass
class IntegratorLeak(ProcessBase):
    K: float = 1.0
    Ki: float = 0.2
    leak: float = 0.0
    y_ss: float = 0.0
    def step(self, u: float, d: float, dt: float) -> float:
        dydt = self.Ki*(self.K*u + d) - max(0.0,self.leak)*(self.y - self.y_ss)
        self.y += dt * dydt
        return self.y
