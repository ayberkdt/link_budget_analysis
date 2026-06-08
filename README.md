# GEO Bent-Pipe Ku-Band Link Budget

Python and LaTeX sources for the UZB451E Spacecraft Communications term
project. The modeled path is a 14 GHz uplink from Rome to HOTBIRD 13G and a
12 GHz downlink to Ankara through a transparent GEO transponder.

Repository: <https://github.com/ayberkdt/link_budget_analysis>

## Scope

- Static clear-sky GEO geometry and link budget
- Bent-pipe uplink/downlink noise combination
- Adjacent-satellite interference and transponder IMD terms
- Dynamic receive-system noise temperature
- Apparent GEO motion sensitivity
- Monte Carlo rain-state availability model
- ITU-R rain, gas, cloud, and scintillation calculations
- DVB-S2 MODCOD selection and throughput estimates
- Ablation tables for tracing model contributions

The static branch uses a fixed 0.5 dB atmospheric allowance on each path. The
ITU-R branch replaces that allowance with modeled attenuation; the two are not
added together.

The default `p=0.1%` atmospheric result is reported as uplink-only,
downlink-only, and coincident dual-site cases. The coincident case is a stress
case, not a statistical 99.9% end-to-end availability claim.

## Layout

```text
src/                  Python model, scenario inputs, GUI, and plotting code
tests/                Regression, validation, and ablation tests
LaTeX Rapor/          Report source, bibliography, figures, and generated macros
sources/              Local copies of source documents cited by the report
outputs/              Generated CSV results and PNG report figures
```

Tracked report inputs include `outputs/*.csv` and `outputs/plots/*.png`. PDF
plot duplicates, root-level delivery PDFs/ZIPs, LaTeX build artifacts, and
Python cache files stay local.

## Source Documents

The local source files are listed in `sources/README.md`. The bibliography uses
the same online URLs with `\url{...}` links and `urldate = {2026-06-08}` fields.
Mirror or third-party hosted documents are labelled as such in the bibliography.

## Setup

Python 3.10 or newer is recommended.

```bash
pip install -r requirements.txt
```

A LaTeX distribution such as MiKTeX or TeX Live is required to rebuild the
report PDF.

## Run

```bash
python -m src.main
```

Useful alternatives:

```bash
python -m src.main --skip-plots
python -m src.main --static-only
python -m src.main --static-only --skip-plots
```

Scenario inputs are defined in `src/scenario_inputs.py`. The GUI edits the same
configuration file:

```bash
python src/gui.py
```

## Report Build

Run the model first so `LaTeX Rapor/parameters.tex`, `outputs/*.csv`, and
`outputs/plots/*.png` match the current code.

```bash
cd "LaTeX Rapor"
pdflatex main
bibtex main
pdflatex main
pdflatex main
```

or:

```bash
cd "LaTeX Rapor"
latexmk -pdf main.tex
```

The compiled PDF is a local deliverable and is not tracked.

## Tests

```bash
pytest -q
```

The test suite covers the core link-budget equations, geometry checks,
scenario validation, deterministic Monte Carlo behavior, ITU-R p-point cases,
static-atmosphere replacement, interference terms, dynamic receiver noise,
GEO motion, and DVB-S2 ACM selection.

## Main Generated Files

- `LaTeX Rapor/parameters.tex`
- `outputs/parameter_sources.csv`
- `outputs/mode_definitions.csv`
- `outputs/geometry_static.csv`
- `outputs/link_budget_static.csv`
- `outputs/scenario_summary_static.csv`
- `outputs/itu_design_cases.csv`
- `outputs/ablation_summary.csv`
- `outputs/plots/*.png`

`LaTeX Rapor/parameters.tex` is generated from the Python results, so headline
report values are not edited by hand.

## Model Limits

The current atmospheric inputs include a shared representative rainfall rate,
a fixed cloud-liquid-water value, and a latitude-based rain-height fallback. A
deployment study would use separate mapped or measured meteorological inputs,
transponder- and beam-specific EIRP and G/T, verified polarization and loading
data, measured antenna patterns, and explicit amplifier back-off.
