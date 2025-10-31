# PID Tuner - Professional Process Control Library

A comprehensive PID control library for process control applications with advanced simulation, tuning methods, and system identification tools.

## 🌟 Features

### Core Library (`pid_tuner`)
- **PID Controller**: Full-featured PID with various forms (P, PI, PID), anti-windup, derivative filtering
- **Process Models**: FOPDT, SOPDT, Integrator with leak
- **Tuning Methods**: 
  - SIMC (Simple Internal Model Control)
  - Lambda/IMC tuning
  - Ziegler-Nichols (Ultimate, FOPDT, Integrating)
  - Cohen-Coon
- **Simulation**: Batch and real-time simulation with valve models
- **System Identification**: Step test analysis and model fitting
- **Valve Models**: Dead band, stiction, positioner overshoot, characteristics
- **Data Storage**: SQLite-based historian with OPC DA/UA connectivity

### Streamlit Web Interface
- Interactive process and controller configuration
- Real-time simulation with live plotting
- Tuning calculator toolbox
- Step test identification from CSV data
- Educational materials and examples

## 📦 Installation

### Basic Installation (Library Only)
```bash
pip install -e .
```

### With Streamlit UI
```bash
pip install -e ".[streamlit]"
```

### Development Installation
```bash
pip install -e ".[dev]"
```

## 🚀 Quick Start

### Using the Library

```python
from pid_tuner import PID, FOPDT, simulate
from pid_tuner.tuning import simc_pi

# Create process model
process = FOPDT(K=1.0, tau=5.0, y=0.0)

# Get tuning parameters
Kp, Ti, Td = simc_pi(K=1.0, tau=5.0, theta=1.0, tau_c=1.0)

# Create controller
controller = PID(Kp=Kp, Ti=Ti, Td=Td, form="PI")

# Simulate
t, sp, y, u, d, u_valve = simulate(
    process, controller,
    t_end=100, dt=0.1, sp=1.0,
    u0=0.0, y0=0.0
)
```

### Running the Streamlit UI

```bash
# Method 1: Using the entry point
python streamlit_ui/run.py

# Method 2: Using streamlit directly
streamlit run streamlit_ui/app.py

# Method 3: If installed with setuptools
pid-tuner-streamlit
```

## 📚 Documentation

### Project Structure

```
pid_tuner_restructured/
├── pid_tuner/              # Core library (importable package)
│   ├── control/           # PID controller
│   ├── models/            # Process models
│   ├── tuning/            # Tuning methods
│   ├── simulate/          # Simulation tools
│   ├── identify/          # System identification
│   ├── storage/           # Data storage
│   ├── opc/               # OPC connectivity
│   ├── utils/             # Utilities
│   └── valves/            # Valve models
├── streamlit_ui/          # Web interface
│   ├── app.py            # Main Streamlit app
│   ├── run.py            # Entry point
│   └── components/       # Reusable components
├── tests/                 # Test suite
├── examples/              # Example scripts
├── docs/                  # Documentation
└── data/                  # Sample data
```

### Tuning Methods

#### SIMC (Simple Internal Model Control)
Recommended method for robust, smooth control:
```python
from pid_tuner.tuning import simc_pi, simc_pid

# For FOPDT process
Kp, Ti, Td = simc_pi(K=1.0, tau=5.0, theta=1.0, tau_c=1.0)

# For SOPDT process (PID)
Kp, Ti, Td = simc_pid(K=1.0, tau1=3.0, tau2=5.0, theta=1.0, tau_c=1.0)
```

#### Lambda Tuning
Universal method for non-oscillatory response:
```python
from pid_tuner.tuning import lambda_fopdt, lambda_integrator

# For FOPDT
Kp, Ti, Td = lambda_fopdt(K=1.0, tau=5.0, theta=1.0, lam=3.0)

# For integrating process
Kp, Ti, Td = lambda_integrator(kprime=0.2, theta=1.0, lam=3.0)
```

#### Ziegler-Nichols
Classic empirical tuning:
```python
from pid_tuner.tuning import zn_ultimate, zn_fopdt, zn_integrating

# Ultimate cycle method
Kp, Ti, Td = zn_ultimate(Ku=2.0, Pu=10.0, mode='PID')

# From FOPDT model
Kp, Ti, Td = zn_fopdt(K=1.0, tau=5.0, theta=1.0, mode='PID')

# For integrating process
Kp, Ti, Td = zn_integrating(Ki=0.2, theta=1.0)
```

### System Identification

Identify process model from step test data:
```python
from pid_tuner.identify import fit_fopdt_from_step
import numpy as np

# Step test data
t = np.linspace(0, 100, 1000)
u = np.ones_like(t)  # Step input
y = ...  # Measured output

# Fit FOPDT model
result = fit_fopdt_from_step(t, u, y)
print(f"K={result['K']:.3f}, tau={result['tau']:.3f}, theta={result['theta']:.3f}")
```

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=pid_tuner tests/

# Run specific test
pytest tests/test_control.py -v
```

## 📖 Examples

See the `examples/` directory for detailed usage examples:
- `basic_simulation.py` - Simple PID simulation
- `step_test_analysis.py` - Model identification
- `tuning_comparison.py` - Compare different tuning methods
- `opc_data_collection.py` - OPC DA/UA data acquisition

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:
1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Tuning methods based on:
  - Skogestad & Grimholt: SIMC method
  - Coughran: Lambda tuning
  - Ziegler & Nichols: Classic tuning rules
  - Cohen & Coon: Process reaction curve method

## 📧 Contact

For questions and support, please open an issue on GitHub.

## 🗺️ Roadmap

See `docs/development_roadmap.md` for planned features and improvements.

---

**Note**: This is a professional restructuring of the PID Tuner project with clean separation between the core library and user interfaces.