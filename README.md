# UZB451 Advanced GEO Link Budget Analyzer (V5)

## 1. Overview

This package is a transparent Python workflow for the UZB451 Spacecraft
Communications term project. It computes a clear-sky static link budget for a
geostationary bent-pipe link and adds a set of optional advanced analyses
(interference, digital metrics, dynamic receive noise, apparent satellite
motion, an educational Monte-Carlo rain-outage model, an ITU-R based
availability study, and DVB-S2 adaptive coding and modulation).

The code is intended for academic link-budget sensitivity and availability
studies. It is not intended for regulatory coordination or commercial
certification, and site-specific accuracy requires replacing the example inputs
with real datasheet and climatological values.

## 2. Scenario

The modelled scenario is a one-way bent-pipe link through a GEO satellite:

```text
Ground Station 1  ->  GEO satellite  ->  Ground Station 2
        (uplink, GS1 transmits)   (downlink, GS2 receives)
```

GS1 is the broadcasting earth station, the satellite is a transparent
transponder, and GS2 is a receive-only terminal. The uplink and downlink are
evaluated separately and then combined.

## 3. Academic baseline (clear-sky static link budget)

The mandatory deliverable is the clear-sky static link budget. It is designed to
be comparable to the MATLAB "Static Link Budget Analyzer" run with the
**"Include P.618 Losses" checkbox left unticked**. Accordingly, the static
baseline in this project **never** includes ITU-R P.618 rain fade or other
atmospheric attenuation; it uses only fixed clear-sky engineering losses
(pointing, polarization, a small fixed atmospheric allowance, implementation).

The static baseline always runs and always produces its CSV outputs.

## 4. Advanced extensions

The following optional layers can each be enabled or disabled independently:

- **Interference** — adjacent-satellite interference (ASI) and intermodulation
  distortion (IMD) as equivalent C/I terms.
- **Digital metrics** — uncoded BER for BPSK/QPSK-type links, an equivalent
  FEC coding-gain model, occupied-bandwidth tradeoff, and a Shannon-Hartley
  capacity check.
- **Dynamic receive system noise temperature** — an elevation- and
  emission-dependent GS2 noise-temperature model.
- **Apparent GEO motion** — a deterministic station-keeping box model
  (not a TLE/SGP4 orbit propagator).
- **Monte-Carlo rain outage** — an educational stochastic weather generator.
- **ITU-R propagation availability** — a self-contained, standards-based
  deterministic slant-path attenuation study.
- **DVB-S2 ACM** — selection of the best MODCOD from the standard ladder for the
  faded downlink.

## 5. Four analyses that must not be confused

| Analysis | Module flag | Nature |
| --- | --- | --- |
| Clear-sky static link budget | always on | MATLAB-comparable; no fade |
| Educational Monte-Carlo rain outage | `RAIN_OUTAGE` | stochastic teaching model |
| ITU-R deterministic availability | `ITU_PROPAGATION` | standards-based engineering approximation |
| DVB-S2 ACM / MODCOD | `MODCOD` | standard MODCOD ladder selection |

- The **clear-sky static baseline** is the academic deliverable and contains no
  rain/atmospheric fade.
- The **Monte-Carlo rain outage** (`simulate_monte_carlo_rain_outage`) is a
  teaching weather generator; it is not climatological truth.
- The **ITU-R availability** study (`calculate_scenario_with_itu`) is a
  self-contained ITU-R based engineering implementation; it uses user-supplied
  inputs and documented approximations rather than the official ITU-R digital
  maps.
- The **DVB-S2 ACM** layer reports the MODCOD that the ITU-faded downlink would
  select; it depends on the ITU-R study being enabled.

## 6. File structure

```text
scenario_inputs.py  Editable GS1, GS2, satellite, link, digital, ITU, and ACM inputs
constants.py        Physical constants and unit conversions
entities.py         Dataclasses for sites, antennas, links, configs, and results
itu_propagation.py  ITU-R P.838 / P.839 / P.618 / P.676 / P.840 attenuation models
modcod.py           DVB-S2 MODCOD table and ACM selection
calculations.py     Geometry, RF budget, interference, digital metrics, ITU pipeline, validation
plotting.py         Centralized plot style and all report figures
main.py             Scenario assembly, validation, CSV export, plot generation, CLI
requirements.txt    Python dependencies
README.md           This document
```

## 7. Where to edit inputs

All scenario values live in `scenario_inputs.py`. Edit the blocks:

- `GS1`, `GS2` — site coordinates, antennas, feeder losses, power/noise figures
- `SATELLITE`, `SATELLITE_UPLINK_RECEIVER`, `SATELLITE_DOWNLINK_TRANSMITTER`
- `UPLINK`, `DOWNLINK`, `UPLINK_LOSSES`, `DOWNLINK_LOSSES`
- `INTERFERENCE`, `DYNAMIC_NOISE`, `APPARENT_MOTION`, `RAIN_OUTAGE`,
  `DIGITAL`, `ITU_PROPAGATION`, `MODCOD`

Every advanced block has an `enabled` flag. When disabled, the analyzer skips
its calculation, writes no CSV and draws no plot for it, and prints a clear skip
message. `main.py` re-reads `scenario_inputs.py` on each run, and validates the
scenario before any analysis: configuration errors abort with a readable
message, and unusual-but-valid values are reported as warnings.

## 8. Command-line usage

```bash
python main.py                              # enabled analyses + enabled plots
python main.py --skip-plots                 # enabled CSV outputs only, no plots
python main.py --static-only                # clear-sky static baseline only
python main.py --static-only --skip-plots   # static clear-sky CSV outputs only
```

`--static-only` forces the apparent-motion, dynamic-Tsys, Monte-Carlo rain,
ITU-R, and DVB-S2 layers off, leaving the MATLAB-comparable clear-sky budget
(plus clean static interference and digital metrics if those remain enabled).

## 9. Output files

CSV files are written under `results/` and figures under `results/plots/`.

Always written (clear-sky static baseline):

```text
geometry_static.csv
link_budget_static.csv
scenario_summary_static.csv
```

Written only when the corresponding analysis is enabled:

```text
interference_summary.csv                  (INTERFERENCE)
digital_metrics_static.csv                (DIGITAL)
scenario_summary_dynamic_clear_sky.csv    (DYNAMIC_NOISE)
digital_metrics_dynamic_clear_sky.csv     (DYNAMIC_NOISE + DIGITAL)
time_varying_link_budget.csv              (APPARENT_MOTION)
time_varying_summary.csv                  (APPARENT_MOTION)
availability_monte_carlo.csv              (RAIN_OUTAGE)
availability_summary.csv                  (RAIN_OUTAGE)
itu_design_point.csv                      (ITU_PROPAGATION)
itu_availability_curve.csv                (ITU_PROPAGATION)
itu_summary.csv                           (ITU_PROPAGATION)
dvbs2_acm_downlink.csv                    (ITU_PROPAGATION + MODCOD)
```

Each figure is written as both PNG (quick viewing) and PDF (report insertion)
with the same basename.

## 10. Core link-budget equations

```text
EIRP   = P_tx + G_tx - L_tx
FSPL   = 92.45 + 20*log10(f_GHz) + 20*log10(R_km)
C/N0   = EIRP + G/T - L_total + 228.6
C/N    = C/N0 - 10*log10(B)
Eb/N0  = C/N0 - 10*log10(Rb)
```

The uplink and downlink are combined by inverse-linear addition of the C/N0
(equivalently C/N) terms:

```text
1 / (C/N_total) = 1/(C/N_uplink) + 1/(C/N_downlink)
```

When interference is enabled, the C/I terms enter the same inverse-linear sum:

```text
1 / (C/(N+I)) = 1/(C/N_up) + 1/(C/N_down)
              + 1/(C/I_ASI_up) + 1/(C/I_ASI_down) + 1/(C/I_IMD)
```

Both the noise-only and interference-included results are reported. When
interference is disabled, the interference-included result equals the noise-only
result and the interference terms are reported as not-applicable.

## 11. Plot guide

Clear-sky static contour plots (01-06):

```text
01_downlink_cn0_dish_vs_frequency      Downlink C/N0 vs GS2 dish and frequency
02_downlink_margin_eirp_vs_tsys        Margin map (diverging, 0 dB closure line)
03_uplink_cn_power_vs_dish             Uplink C/N vs HPA power and dish
04_total_ebn0_bitrate_vs_bandwidth     End-to-end Eb/N0 with required-Eb/N0 line
05_gs2_elevation_latitude_vs_longitude GS2 elevation map with low-elevation limits
06_downlink_asi_ci_spacing_vs_dish     ASI C/I trend map (INTERFERENCE only)
```

Advanced plots (07-22): time-varying margin/elevation/range/FSPL and the
sub-satellite track (APPARENT_MOTION); dynamic Tsys vs elevation (DYNAMIC_NOISE);
the interference bar chart (INTERFERENCE); the Monte-Carlo rain time series,
margin histogram, and outage timeline (RAIN_OUTAGE); and the BER, capacity, and
FEC-bandwidth figures (DIGITAL).

ITU-R and DVB-S2 plots (23-29): attenuation vs unavailability with the design
point marked; faded margin vs availability with the 0 dB crossing; the
per-mechanism attenuation breakdown; rain attenuation vs frequency; the P.838
specific-attenuation curves; the DVB-S2 MODCOD ladder with the selected
operating point; and ACM throughput/efficiency vs availability.

## 12. Input-data limitations

The shipped values are illustrative examples. For a meaningful study, replace
them with real values:

- satellite EIRP footprint value (downlink),
- satellite G/T (uplink),
- GS1/GS2 antenna datasheets (diameter, efficiency, or gain),
- GS2 receiver system noise temperature,
- transmit power and feeder losses,
- real site coordinates,
- `rain_rate_001_mm_per_h` (R0.01) from ITU-R P.837 or a reliable
  climatological source,
- local surface pressure, temperature, and humidity,
- rain height / 0 deg C isotherm height if available,
- cloud columnar liquid water if available,
- adjacent-satellite longitudes and carrier assumptions.

## 13. MATLAB comparison workflow

To cross-check the clear-sky static results against the MATLAB Static Link
Budget Analyzer:

1. In MATLAB, keep the **"Include P.618 Losses" box unticked**.
2. Use the same GS1, GS2, and satellite parameters (coordinates, antennas,
   power, G/T, EIRP, frequencies, bandwidth, bit rate).
3. Deactivate the satellite-to-satellite link so only one uplink and one
   downlink remain.
4. Compare the following quantities against `geometry_static.csv` and
   `link_budget_static.csv` / `scenario_summary_static.csv`:
   geometry (slant range, elevation), FSPL, EIRP, G/T, C/N0, C/N, Eb/N0, and the
   final link margin.

Small differences are expected from differing constants and antenna/gain
conventions; the trends and orders of magnitude should agree.

## 14. Limitations

- The adjacent-satellite interference model is a teaching/engineering trend
  model based on an off-axis discrimination envelope; it is not regulatory
  coordination.
- The apparent-motion model is a deterministic station-keeping box, not a
  TLE/SGP4 orbit propagation.
- The ITU-R propagation suite is a self-contained engineering implementation of
  the Recommendations; it does not embed the official ITU-R digital maps, so the
  R0.01 rain rate and rain height come from user inputs (with a documented
  latitude approximation as a fallback).
- The Monte-Carlo rain model is an educational stochastic generator, not
  climatological truth.
- The digital BER/FEC results are analytical AWGN approximations (FEC modelled
  as an equivalent coding gain), not decoder simulations.

## 15. Requirements and installation

Python 3.10+ with:

```text
numpy
matplotlib
```

Install with:

```bash
pip install -r requirements.txt
```

## 16. Quick start

```bash
pip install -r requirements.txt
python main.py
```

Then inspect `results/` for CSV outputs and `results/plots/` for figures.

## 17. Suggested report usage

- Use the clear-sky static results (`*_static.csv`, plots 01-05) as the core
  required link-budget deliverable and the MATLAB comparison.
- Use the interference, digital, and dynamic-Tsys outputs to discuss design
  sensitivity and margins.
- Use the ITU-R availability study (plots 23-27) and the Monte-Carlo outage
  figures to discuss propagation conditions and outage, clearly labelling each
  as an advanced/illustrative extension.
- Use the DVB-S2 ACM figures (28-29) to discuss the availability/throughput
  tradeoff.
- State clearly in the report which inputs are example values and which were
  replaced with datasheet/climatological data.
