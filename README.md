# GEO Bent-Pipe Ku-Band Link Budget

Python and LaTeX sources for the UZB451E Spacecraft Communications term
project. The modeled path is a 14 GHz uplink from Rome to HOTBIRD 13G and a
12 GHz downlink to Ankara through a transparent GEO transponder.

Repository: <https://github.com/ayberkdt/link_budget_analysis>

## Analysis Scope

The project contains:

- a static clear-sky link budget with GEO geometry, antenna gain, FSPL,
  fixed engineering losses, and bent-pipe noise combination;
- adjacent-satellite interference and an assumed transponder IMD term;
- a dynamic receive-system noise-temperature model;
- a simplified GEO station-keeping sensitivity model;
- an illustrative Monte Carlo weather-state generator;
- ITU-R-informed rain, gas, cloud, and scintillation calculations;
- DVB-S2 MODCOD selection and throughput estimates;
- controlled module-ablation outputs.

The static branch uses a fixed 0.5 dB atmospheric allowance on each path. The
advanced atmospheric branch replaces that allowance with the modeled absolute
attenuation; it does not add both values.

The default `p=0.1%` calculation is exported in three forms: uplink-only,
downlink-only, and coincident dual-site. The coincident result is a conservative
stress case, not a statistically derived 99.9% end-to-end availability claim.

## Repository Layout

```text
src/                 Python model, configuration, GUI, and plotting code
tests/               Equation, regression, validation, and ablation tests
LaTeX Rapor/          Report source and bibliography
sources/              Operator and manufacturer source documents
outputs/              Generated CSV files and plots
```

`sources/README.md` distinguishes original operator/manufacturer documents from
locally prepared legacy summaries and records the main source-audit caveats.

## Setup

Python 3.10 or newer is recommended.

```bash
pip install -r requirements.txt
```

A LaTeX distribution such as MiKTeX or TeX Live is required to rebuild the
report PDF.

## Running the Model

```bash
python src/main.py
python src/main.py --skip-plots
python src/main.py --static-only
python src/main.py --static-only --skip-plots
```

Package execution is also supported:

```bash
python -m src.main --skip-plots
```

Scenario inputs are defined in `src/scenario_inputs.py`. The GUI can edit the
same configuration file:

```bash
python src/gui.py
```

## Tests

```bash
pytest -q
```

The suite currently covers:

- FSPL, dish gain, inverse-dB combination, and static end-to-end regression;
- HOTBIRD 13G, ASTRA 1P, and Intelsat 39 geometry checks;
- parameter-source and operating-mode traceability;
- invalid probability, attenuation-range, and link-consistency rejection;
- deterministic Monte Carlo behavior and annual time scaling;
- replacement of static atmospheric allowances in the advanced branch;
- uplink-only, downlink-only, and coincident p-point behavior;
- ASI, IMD, rain carrier loss, dynamic receiver temperature, atmospheric
  emission, GEO motion, and ACM ablation.

## Main Outputs

- `outputs/parameter_sources.csv`: configured values and their evidence status.
- `outputs/mode_definitions.csv`: fixed-rate and ACM metric definitions.
- `outputs/geometry_static.csv`: range, elevation, azimuth, and central angle.
- `outputs/link_budget_static.csv`: per-link gains, losses, and noise metrics.
- `outputs/scenario_summary_static.csv`: end-to-end clear-sky result.
- `outputs/itu_design_cases.csv`: uplink-only, downlink-only, and coincident
  per-path p-point cases.
- `outputs/ablation_summary.csv`: controlled incremental model comparison.
- `outputs/plots/`: report figures in PNG and PDF formats.

`LaTeX Rapor/parameters.tex` is generated from the current Python results, so
reported headline values are not maintained by hand.

## Model Limits

This is an academic engineering model. The current atmospheric inputs include a
shared representative rainfall rate, a fixed cloud-liquid-water value, and a
latitude-based rain-height fallback. An operational design should use separate
mapped or measured meteorological inputs for Rome and Ankara, transponder- and
beam-specific EIRP and G/T, verified polarization and loading data, measured
antenna patterns, and explicit amplifier back-off.
