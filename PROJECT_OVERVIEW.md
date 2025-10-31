# 📦 Project Overview: `azeo_pid`
**Location**: `C:\Users\nhasan\Documents\GitHub\azeo_pid`
**Options**: follow_links=False, max_depth=∞, hash=none, count_lines=False, tree_style=True, exclude_dotfiles=True
**Exclude patterns**: 204 total (204 default + 0 user-defined)

## 📊 Statistics
- 📁 **Directories**: 24
- 📄 **Files**: 54
- 🐍 **Python files**: 50

### File Types (Top 15)
- 🐍 `.py`: **50**
- 📝 `.md`: **2**
- 🗄️ `.sql`: **1**
- 📄 `.txt`: **1**

### Largest Files (Top 10)
- 🐍 `streamlit_ui\enhanced_app.py` — **32.4 KB**
- 🐍 `pid_tuner\control\pid.py` — **11.6 KB**
- 📝 `PROJECT_OVERVIEW.md` — **10.5 KB**
- 🐍 `streamlit_ui\enhanced_styles.py` — **7.2 KB**
- 🐍 `streamlit_ui\compat.py` — **6.2 KB**
- 📝 `README.md` — **5.6 KB**
- 🐍 `pid_tuner\tuning\methods.py` — **5.0 KB**
- 🐍 `pid_tuner\valves\valve.py` — **4.6 KB**
- 🐍 `pid_tuner\storage\writer.py` — **4.1 KB**
- 🐍 `streamlit_ui\panels\simulation_panel.py` — **3.5 KB**

---
## 📂 Directory Structure

📁 **pid_tuner/
├── 📁 **__pycache__/**
├── 📁 **control/**
│   ├── 📁 **__pycache__/**
│   │   ├── 🐍 **__init__.py** — *769 B*
│   │   └── 🐍 **pid.py** — *11.6 KB* *(1 class, 3 functions)*
├── 📁 **identify/**
│   ├── 📁 **__pycache__/**
│   │   ├── 🐍 **__init__.py** — *2.0 KB* *(3 functions)*
│   │   ├── 🐍 **intfit.py** — *1.0 KB* *(2 functions)*
│   │   ├── 🐍 **segment.py** — *1.6 KB* *(3 functions)*
│   │   ├── 🐍 **sopdtfit.py** — *2.3 KB* *(4 functions)*
│   │   └── 🐍 **stepfit.py** — *2.6 KB* *(3 functions)*
├── 📁 **models/**
│   ├── 📁 **__pycache__/**
│   │   ├── 🐍 **__init__.py** — *590 B*
│   │   └── 🐍 **processes.py** — *1.2 KB* *(4 classes)*
├── 📁 **opc/**
│   │   ├── 🐍 **__init__.py** — *176 B*
│   │   ├── 🐍 **da_client.py** — *1.9 KB* *(1 class)*
│   │   └── 🐍 **ua_client.py** — *2.0 KB* *(1 class)*
├── 📁 **simulate/**
│   ├── 📁 **__pycache__/**
│   │   ├── 🐍 **__init__.py** — *459 B*
│   │   ├── 🐍 **realtime.py** — *1.7 KB* *(1 function)*
│   │   └── 🐍 **sim.py** — *1.3 KB* *(1 function)*
├── 📁 **storage/**
│   │   ├── 🐍 **__init__.py** — *237 B*
│   │   ├── 🐍 **reader.py** — *1.5 KB* *(3 functions)*
│   │   ├── 🗄️ **schema.sql** — *1.5 KB*
│   │   └── 🐍 **writer.py** — *4.1 KB* *(1 class)*
├── 📁 **tuning/**
│   ├── 📁 **__pycache__/**
│   │   ├── 🐍 **__init__.py** — *942 B*
│   │   ├── 🐍 **lambda_method.py** — *745 B* *(1 class, 2 functions)*
│   │   ├── 🐍 **methods.py** — *5.0 KB* *(9 functions)*
│   │   └── 🐍 **simc.py** — *1.6 KB* *(2 classes, 4 functions)*
├── 📁 **utils/**
│   ├── 📁 **__pycache__/**
│   │   ├── 🐍 **__init__.py** — *13 B*
│   │   └── 🐍 **filters.py** — *582 B* *(3 functions)*
├── 📁 **valves/**
│   ├── 📁 **__pycache__/**
│   │   ├── 🐍 **__init__.py** — *459 B*
│   │   └── 🐍 **valve.py** — *4.6 KB* *(1 class, 3 functions)*
│   └── 🐍 **__init__.py** — *1.1 KB*
📁 **streamlit_ui/
├── 📁 **__pycache__/**
├── 📁 **components/**
│   ├── 📁 **__pycache__/**
│   │   ├── 🐍 **__init__.py** — *0 B*
│   │   ├── 🐍 **charts.py** — *722 B* *(2 functions)*
│   │   ├── 🐍 **forms.py** — *287 B* *(1 function)*
│   │   └── 🐍 **tables.py** — *345 B* *(1 function)*
├── 📁 **panels/**
│   ├── 📁 **__pycache__/**
│   │   ├── 🐍 **__init__.py** — *294 B*
│   │   ├── 🐍 **controller_panel.py** — *1.1 KB* *(1 function)*
│   │   ├── 🐍 **opc_panel.py** — *814 B* *(1 function)*
│   │   ├── 🐍 **process_panel.py** — *1.2 KB* *(1 function)*
│   │   ├── 🐍 **simulation_panel.py** — *3.5 KB* *(2 functions)*
│   │   └── 🐍 **stepid_panel.py** — *2.9 KB* *(1 function)*
│   ├── 🐍 **__init__.py** — *0 B*
│   ├── 🐍 **app.py** — *891 B* *(1 function)*
│   ├── 🐍 **compat.py** — *6.2 KB* *(4 functions)*
│   ├── 🐍 **enhanced_app.py** — *32.4 KB* *(17 functions)*
│   ├── 🐍 **enhanced_styles.py** — *7.2 KB* *(2 functions)*
│   ├── 🐍 **router.py** — *847 B* *(1 class, 1 function)*
│   ├── 🐍 **run.py** — *631 B*
│   ├── 🐍 **run_enhanced.py** — *1.3 KB*
│   ├── 🐍 **state.py** — *1.9 KB* *(1 class, 2 functions)*
│   ├── 🐍 **styles.py** — *375 B* *(1 function)*
│   └── 🐍 **tune_compat.py** — *2.9 KB* *(5 functions)*
├── 📝 **PROJECT_OVERVIEW.md** — *10.5 KB*
├── 📝 **README.md** — *5.6 KB*
├── 📄 **requirements.txt** — *505 B*
├── 🐍 **setup.py** — *2.3 KB*
└── 🐍 **streamlit_app.py** — *580 B*

---
## 🐍 Python Files Analysis

### 📄 `pid_tuner\control\pid.py`

**Classes**:
- `PID (9 methods)`

**Functions**:
- `create_emerson_pid()`
- `create_honeywell_pid()`
- `create_yokogawa_pid()`

### 📄 `pid_tuner\identify\__init__.py`

**Functions**:
- `fit_fopdt()`
- `fit_sopdt()`
- `fit_integrator()`

### 📄 `pid_tuner\identify\intfit.py`

**Functions**:
- `_largest_step()`
- `fit_integrator_from_step()`

### 📄 `pid_tuner\identify\segment.py`

**Functions**:
- `moving_median()`
- `detect_steps_by_diff()`
- `cusum_change_points()`

### 📄 `pid_tuner\identify\sopdtfit.py`

**Functions**:
- `_largest_step()`
- `_median_segment()`
- `_sopdt_step_kernel()`
- `fit_sopdt_from_step()`

### 📄 `pid_tuner\identify\stepfit.py`

**Functions**:
- `_largest_step()`
- `_median_segment()`
- `fit_fopdt_from_step()`

### 📄 `pid_tuner\models\processes.py`

**Classes**:
- `ProcessBase (2 methods)`
- `FOPDT (1 methods)`
- `SOPDT (1 methods)`
- `IntegratorLeak (1 methods)`

### 📄 `pid_tuner\opc\da_client.py`

**Classes**:
- `DaPoller (3 methods)`

### 📄 `pid_tuner\opc\ua_client.py`

**Classes**:
- `UaAcquirer (4 methods)`

### 📄 `pid_tuner\simulate\realtime.py`

**Functions**:
- `simulate_realtime()`

### 📄 `pid_tuner\simulate\sim.py`

**Functions**:
- `simulate()`

### 📄 `pid_tuner\storage\reader.py`

**Functions**:
- `get_series()`
- `list_sessions()`
- `list_tags()`

### 📄 `pid_tuner\storage\writer.py`

**Classes**:
- `SamplesWriter (9 methods)`

### 📄 `pid_tuner\tuning\lambda_method.py`

**Classes**:
- `FOPDT (0 methods)`

**Functions**:
- `lambda_fopdt()`
- `lambda_integrator()`

### 📄 `pid_tuner\tuning\methods.py`

**Functions**:
- `simc_from_model()`
- `lambda_from_model()`
- `zn_reaction_curve()`
- `imc_lambda_fopdt()`
- `lambda_integrating()`
- `simc_pi()`
- `simc_pid()`
- `simc_integrating()`
- `simc_tau_c()`

### 📄 `pid_tuner\tuning\simc.py`

**Classes**:
- `FOPDT (0 methods)`
- `SOPDT (0 methods)`

**Functions**:
- `simc_pi_fopdt()`
- `simc_pid_sopdt()`
- `simc_integrator()`
- `simc_tau_c_recommendation()`

### 📄 `pid_tuner\utils\filters.py`

**Functions**:
- `clamp()`
- `deadtime_buffer()`
- `lowpass()`

### 📄 `pid_tuner\valves\valve.py`

**Classes**:
- `ValveActuator (3 methods)`

**Functions**:
- `characteristic()`
- `apply_deadband_stiction()`
- `reset_valve_state()`

### 📄 `streamlit_ui\app.py`

**Functions**:
- `main()`

### 📄 `streamlit_ui\compat.py`

**Functions**:
- `_build_process()`
- `_build_controller()`
- `simulate_closed_loop()`
- `streaming_closed_loop()`

### 📄 `streamlit_ui\components\charts.py`

**Functions**:
- `pv_sp_chart()`
- `op_chart()`

### 📄 `streamlit_ui\components\forms.py`

**Functions**:
- `num()`

### 📄 `streamlit_ui\components\tables.py`

**Functions**:
- `dict_table()`

### 📄 `streamlit_ui\enhanced_app.py`

**Functions**:
- `main()`
- `render_acquisition_tab()`
- `render_identification_tab()`
- `render_controller_tab()`
- `render_simulation_tab()`
- `render_opc_tab()`
- `identify_model_from_data()`
- `apply_identified_model()`
- `calculate_tuning()`
- `create_controller_diagram()`
- `run_continuous_simulation()`
- `create_live_plot()`
- `display_final_results()`
- `run_pid_simulation()`
- `calculate_settling_time()`
- `calculate_overshoot()`
- `create_csv_export()`

### 📄 `streamlit_ui\enhanced_styles.py`

**Functions**:
- `inject_enhanced_css()`
- `get_color()`

### 📄 `streamlit_ui\panels\controller_panel.py`

**Functions**:
- `render()`

### 📄 `streamlit_ui\panels\opc_panel.py`

**Functions**:
- `render()`

### 📄 `streamlit_ui\panels\process_panel.py`

**Functions**:
- `render()`

### 📄 `streamlit_ui\panels\simulation_panel.py`

**Functions**:
- `render()`
- `_to_csv()`

### 📄 `streamlit_ui\panels\stepid_panel.py`

**Functions**:
- `render()`

### 📄 `streamlit_ui\router.py`

**Classes**:
- `Page (0 methods)`

**Functions**:
- `route_sidebar()`

### 📄 `streamlit_ui\state.py`

**Classes**:
- `SessionState (0 methods)`

**Functions**:
- `get_state()`
- `init_defaults()`

### 📄 `streamlit_ui\styles.py`

**Functions**:
- `inject_css()`

### 📄 `streamlit_ui\tune_compat.py`

**Functions**:
- `_call_first()`
- `identify_model()`
- `tuning_simc()`
- `tuning_lambda()`
- `tuning_zn_reaction()`

