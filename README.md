# GEO Bent-Pipe Ku-Band Satellite Link Budget Analyzer
### UZB451E Spacecraft Communications Term Project Report & Simulation Framework

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Standards](https://img.shields.io/badge/standards-ITU--R%20P.618%20%7C%20P.838%20%7C%20P.676%20%7C%20P.840-orange.svg)](https://www.itu.int/)
[![Academic Baseline](https://img.shields.io/badge/ITU-Aeronautics%20%26%20Astronautics-darkblue.svg)](https://uubf.itu.edu.tr/en)

---

## 🛰️ Project Overview
This repository contains the complete custom Python-based simulation framework and the corresponding LaTeX source code for the **UZB451E Spacecraft Communications** term project report at Istanbul Technical University. 

The project analyzes a geostationary (GEO) bent-pipe Ku-band satellite communication link between **GS1 Rome** (uplink/broadcasting station at 14 GHz) and **GS2 Ankara** (receive-only station at 12 GHz) via the **Eutelsat Hotbird 13G** satellite. The framework models both the static clear-sky baseline (consistent with classical Pratt-style hand calculations) and advanced propagation and system impairments under realistic meteorological conditions.

---

## 🚀 Key Features & Simulation Modules

The framework is organized into modular engineering components that can be configured dynamically:

| Module / Feature | Code Config Flag | Description | Status |
|---|---|---|---|
| **Static Clear-Sky Link Budget** | *Always Active* | Classical static link budget calculation including slant-path geometries, polarization mismatches, free-space path loss (FSPL), transponder gains, and end-to-end signal metrics ($C/N_0$, $E_s/N_0$, $E_b/N_0$). | **Core Requirement** |
| **Parametric Contour Plots** | *Always Active* | Renders 2D parametric curves and contour plots analyzing key design tradeoffs (e.g., dish diameter vs. frequency, EIRP vs. system noise temperature, HPA power vs. bit rate). | **Core Requirement** |
| **ITU-R Slant-Path Propagation** | `ITU_PROPAGATION` | Detailed atmospheric attenuation modeling following ITU-R P.618-13, P.676 (gas absorption), P.838 (rain specific attenuation), and P.840 (cloud liquid water). | **Advanced Feature** |
| **Monte Carlo Rain Outage** | `RAIN_OUTAGE` | Hourly weather profile generator simulating $8,760$ hours of a meteorological year to calculate annual outage probabilities, link availability statistics, and rain margin distribution. | **Advanced Feature** |
| **Interference & IMD Analysis** | `INTERFERENCE` | Computes Adjacent Satellite Interference (ASI) based on orbital spacing and antenna patterns, as well as transponder Intermodulation Distortion (IMD) from multi-carrier backing-off. | **Advanced Feature** |
| **Dynamic System Noise** | `DYNAMIC_NOISE` | Models the dynamic variation of the ground station receiver noise temperature ($T_{sys}$) as a function of the path elevation angle and atmospheric rain attenuation. | **Advanced Feature** |
| **GEO Apparent Orbit Motion** | `APPARENT_MOTION` | Simulates periodic satellite apparent motion due to orbital inclination/eccentricity station-keeping tolerances, showing tracking loss variations over a 24-hour cycle. | **Advanced Feature** |
| **DVB-S2 Adaptive Coding & Modulation (ACM)** | `MODCOD` | Automates the dynamic selection of the optimal DVB-S2 modulation and coding scheme (MODCOD) under time-varying rain fades to maximize link throughput. | **Advanced Feature** |

---

## 📁 Repository Structure

```text
├── src/                      # Python source files
│   ├── main.py               # Main execution script (orchestrates simulation and saves outputs)
│   ├── calculations.py       # Physics-based RF link geometry, link budget math, and Monte Carlo loops
│   ├── constants.py          # Physical constants, speed of light, Boltzmann constant, unit converters
│   ├── entities.py           # Structured dataclasses representing stations, satellites, and transponders
│   ├── itu_propagation.py    # ITU-R P.618/P.676/P.838/P.840 slant-path impairment models
│   ├── modcod.py             # DVB-S2 spectral efficiency/threshold lookup and ACM selector
│   ├── plotting.py           # Publication-quality plotting routines using Matplotlib
│   └── scenario_inputs.py    # Main user configuration file containing input RF parameters and flags
├── LaTeX Rapor/              # Academic report source code (LaTeX)
│   ├── chapters/             # Modular chapter files (Introduction, Equations, Advanced Models, etc.)
│   ├── resimler/             # Figures, block diagrams, and logo assets
│   ├── main.tex              # Main compilation document
│   ├── preamble.tex          # Formatting styles, packages, and custom page geometry
│   ├── parameters.tex        # Globally shared numerical values
│   └── references.bib        # BibTeX citations (ITU-R, DVB-S2, Pratt, etc.)
├── outputs/                  # Automatically generated CSV datasets
│   └── plots/                # High-resolution PNG and vector PDF figures for the report
├── requirements.txt          # Python dependency specifications
└── README.md                 # Project README (this file)
```

---

## 🛠️ Installation & Setup

### Prerequisites
- Python **3.10** or higher is required.
- A LaTeX distribution (e.g., MiKTeX or TeX Live) is needed to compile the report source code.

### 1. Clone the Repository
```bash
git clone https://github.com/ayberkdt/link_budget_analysis.git
cd link_budget_analysis
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

---

## 💻 Running the Simulation

You can execute the entire analysis or run specific modes using command-line arguments:

```bash
# Run all configured simulation modules and generate all figures
python src/main.py

# Run calculations and export CSV data, but skip rendering plots (faster execution)
python src/main.py --skip-plots

# Run only the static clear-sky baseline calculations (disables ITU propagation, Monte Carlo, and ACM)
python src/main.py --static-only

# Run static-only calculations and save to CSV without rendering plots
python src/main.py --static-only --skip-plots
```

---

## 📝 Customizing Input Parameters

All input parameters (e.g., coordinates, HPA power, frequencies, bandwidth, noise figures) are declared in [scenario_inputs.py](file:///c:/Users/ayber/Desktop/Spacecraft%20Communication%20Proje/src/scenario_inputs.py). You can edit this file to run your own link analysis:

```python
# Example snippet from src/scenario_inputs.py
GS1_Rome = {
    "site_name": "GS1 Rome",
    "latitude_deg": 41.8902,
    "longitude_deg": 12.4922,
    "antenna_diameter_m": 2.4,        # Earth station dish diameter (m)
    "tx_power_w": 20.0,               # High Power Amplifier (HPA) saturated output power (W)
    "antenna_efficiency": 0.65,        # Dish aperture efficiency
    ...
}
```

---

## 📊 Exported Outputs

Upon running the code, all tabular calculations are exported to the `outputs/` folder in CSV format. Graphics are saved in both high-resolution **PNG** (for web/doc previewing) and vector **PDF** (for LaTeX insertion) in the `outputs/plots/` subdirectory.

### Static Baseline Outputs
*   `outputs/geometry_static.csv` — Calculated slant-paths, elevation angles, azimuts, and range distances.
*   `outputs/link_budget_static.csv` — Point-by-point gains, losses, noise powers, and carrier-to-noise ratios.
*   `outputs/scenario_summary_static.csv` — Unified end-to-end performance metrics ($C/(N+I)$, margins, spectral efficiencies).

### Visualizations & Plots
*   **01_downlink_cn0_dish_vs_frequency** — Downlink $C/N_0$ contour as a function of GS2 dish diameter and downlink frequency.
*   **02_downlink_margin_eirp_vs_tsys** — System margin vs. satellite EIRP and receiver noise temperature.
*   **03_uplink_cn_power_vs_dish** — Uplink $C/N$ contour vs. transmit power and GS1 dish diameter.
*   **04_total_ebn0_bitrate_vs_bandwidth** — System $E_b/(N_0+I_0)$ contour vs. transmission rate and bandwidth.
*   **23_itu_attenuation_vs_availability** — Slant-path attenuation breakdown for gas, rain, and clouds vs. availability.
*   **28_dvbs2_modcod_ladder** — Visual lookup ladder showing MODCOD thresholds vs. available $E_s/N_0$.
*   **29_dvbs2_acm_vs_availability** — Dynamic link throughput (Mbps) and MODCOD selection curves across the availability spectrum.

---

## 🎓 Academic Credits & Methodology
- This simulation tool was developed for the term project of **UZB451E Spacecraft Communications** at ITU.
- Academic methodology for basic RF link parameters is based on **Pratt, Bostian, and Allnutt - Satellite Communications (2nd Edition)**, Chapter 4.
- Atmospheric propagation models follow **ITU-R P.618-13 (Rain attenuation on slant paths)** and related recommendations.
