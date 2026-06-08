# GEO Bent-Pipe Ku-Band Link Budget

Python and LaTeX sources for the UZB451E Spacecraft Communications term
project. The modeled path is a 14 GHz uplink from Rome to HOTBIRD 13G and a
12 GHz downlink to Ankara through a transparent GEO transponder.

Repository: <https://github.com/ayberkdt/link_budget_analysis>

## Scope

The project contains:

- static clear-sky GEO geometry, antenna gain, FSPL, fixed engineering losses,
  and bent-pipe noise combination;
- adjacent-satellite interference and an assumed transponder IMD term;
- dynamic receive-system noise temperature and apparent GEO motion models;
- a sampled Monte Carlo rain-state availability model;
- ITU-R-informed rain, gas, cloud, and scintillation calculations;
- DVB-S2 MODCOD selection and throughput estimates;
- controlled module-ablation outputs for tracing each model contribution.

The static branch uses a fixed 0.5 dB atmospheric allowance on each path. The
ITU-R branch replaces that allowance with modeled absolute attenuation; it does
not add both values.

The default `p=0.1%` atmospheric calculation is exported as uplink-only,
downlink-only, and coincident dual-site cases. The coincident case is a stress
case, not a statistically derived 99.9% end-to-end availability claim.

## Repository Layout

```text
src/                  Python model, configuration, GUI, and plotting code
tests/                Regression, validation, and ablation tests
LaTeX Rapor/          Report source, bibliography, figures, and generated macros
sources/              Primary operator, manufacturer, and standards evidence
outputs/              Ignored generated CSV files and plots
```

`outputs/` is intentionally ignored by Git. Recreate it with:

```bash
python -m src.main
```

Root-level PDF/ZIP deliverables and LaTeX build artifacts are also ignored.
The Git-tracked material should be the code, tests, report source, bibliography,
source evidence documents, and documentation.

## Source Evidence

The retained files in `sources/` are the primary local evidence copies used by
the report: Eutelsat HOTBIRD, Intelsat 39, SES fleet map, Andrew Type 243,
Norsat ATOMBKU, and Triax TD88. Locally prepared legacy summary sheets for
Prodelin and Triax were removed because they are not primary manufacturer or
operator sources and are not cited by the report.

The bibliography was checked again on 2026-06-08. Online entries use `url` and
`urldate` fields, with short notes describing whether the source is official,
a retained local copy, or a clearly labelled mirror.

## Setup

Python 3.10 or newer is recommended.

```bash
pip install -r requirements.txt
```

A LaTeX distribution such as MiKTeX or TeX Live is required to rebuild the
report PDF.

## Running The Model

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

## Rebuilding The Report

Run the model first so `LaTeX Rapor/parameters.tex` and `outputs/plots/` are
fresh. Then build the report from the `LaTeX Rapor/` directory, for example:

```bash
pdflatex main
bibtex main
pdflatex main
pdflatex main
```

or with `latexmk` if available:

```bash
latexmk -pdf main.tex
```

The compiled PDF is ignored by Git and should be treated as a local deliverable.

## Tests

```bash
pytest -q
```

The suite covers:

- FSPL, dish gain, inverse-dB combination, and static end-to-end regression;
- HOTBIRD 13G, ASTRA 1P, and Intelsat 39 geometry checks;
- parameter-source and operating-mode traceability;
- invalid probability, attenuation-range, and link-consistency rejection;
- deterministic Monte Carlo behavior and annual time scaling;
- replacement of static atmospheric allowances in the ITU-R branch;
- uplink-only, downlink-only, and coincident p-point behavior;
- ASI, IMD, rain carrier loss, dynamic receiver temperature, atmospheric
  emission, GEO motion, and ACM ablation.

## Generated Outputs

`python -m src.main` creates:

- `outputs/parameter_sources.csv`: configured values and evidence status;
- `outputs/mode_definitions.csv`: fixed-rate and ACM metric definitions;
- `outputs/geometry_static.csv`: range, elevation, azimuth, and central angle;
- `outputs/link_budget_static.csv`: per-link gains, losses, and noise metrics;
- `outputs/scenario_summary_static.csv`: end-to-end clear-sky result;
- `outputs/itu_design_cases.csv`: uplink-only, downlink-only, and coincident
  per-path p-point cases;
- `outputs/ablation_summary.csv`: incremental model comparison;
- `outputs/plots/`: report figures in PNG and PDF formats.

`LaTeX Rapor/parameters.tex` is generated from the current Python results, so
headline values in the report are not maintained by hand.

## Model Limits

This is an academic engineering model. The current atmospheric inputs include a
shared representative rainfall rate, a fixed cloud-liquid-water value, and a
latitude-based rain-height fallback. An operational design should use separate
mapped or measured meteorological inputs for Rome and Ankara, transponder- and
beam-specific EIRP and G/T, verified polarization and loading data, measured
antenna patterns, and explicit amplifier back-off.
