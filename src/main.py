# main.py
"""Ana çalıştırıcı dosya (Entry Point).

Bu script, `scenario_inputs.py` dosyasından aldığı parametrelerle 
hat bütçesi analizini baştan sona yürütür. İlgili hesaplamaları (RF bütçesi, 
opsiyonel atmosferik kayıplar vb.) çağırır ve sonuçları CSV ve grafik 
olarak kaydeder.

Komut Satırı Kullanımı
----------------------
`python main.py`                       Tüm aktif analizleri ve grafikleri çalıştırır.
`python main.py --skip-plots`          Grafik çizimlerini atlayarak sadece CSV çıkarır.
`python main.py --static-only`         Yalnızca açık hava (clear-sky) statik hat bütçesini çalıştırır.
"""

# ========================================================================
# 0.                             IMPORTS
# ========================================================================
from __future__ import annotations

import argparse
import csv
from dataclasses import replace
from pathlib import Path
from typing import Iterable, Mapping

from calculations import (
    calculate_itu_availability_curve,
    calculate_scenario,
    calculate_scenario_with_itu,
    simulate_monte_carlo_rain_outage,
    simulate_time_varying_scenario,
    summarize_itu_availability_curve,
    summarize_monte_carlo_availability,
    summarize_time_varying_results,
    validate_scenario_config,
    watts_to_dbw,
)
from constants import GHZ, MHZ
from entities import (
    DigitalLinkConfig,
    DishAntenna,
    DynamicNoiseConfig,
    GeoApparentMotion,
    GeoSatellite,
    InterferenceConfig,
    ITUPropagationConfig,
    LinkConfig,
    LinkEndpoint,
    LinkLosses,
    Location,
    ModcodConfig,
    RainOutageConfig,
    ScenarioConfig,
)
from plotting import generate_advanced_plots, generate_contour_plots, generate_itu_plots
from scenario_inputs import (
    APPARENT_MOTION,
    DIGITAL,
    DOWNLINK,
    DOWNLINK_LOSSES,
    DYNAMIC_NOISE,
    GS1,
    GS2,
    INTERFERENCE,
    ITU_PROPAGATION,
    MODCOD,
    RAIN_OUTAGE,
    SATELLITE,
    SATELLITE_DOWNLINK_TRANSMITTER,
    SATELLITE_UPLINK_RECEIVER,
    SCENARIO_NAME,
    UPLINK,
    UPLINK_LOSSES,
)


RESULTS_DIR = Path("outputs")
PLOTS_DIR = RESULTS_DIR / "plots"


def _optional_float(value: object) -> float | None:
    """Convert a value to ``float`` unless it is ``None``."""

    if value is None:
        return None
    return float(value)


def _build_location(config: Mapping[str, object]) -> Location:
    """Create a ground-station location from an input mapping."""

    return Location(
        name=str(config["site_name"]),
        latitude_deg=float(config["latitude_deg"]),
        longitude_deg=float(config["longitude_deg"]),
        altitude_km=float(config.get("altitude_km", 0.0)),
    )


def _build_dish_antenna(config: Mapping[str, object]) -> DishAntenna:
    """Create a dish antenna model from an input mapping."""

    return DishAntenna(
        name=str(config["antenna_name"]),
        diameter_m=_optional_float(config.get("antenna_diameter_m")),
        efficiency=float(config.get("antenna_efficiency", 0.62)),
        gain_dbi=_optional_float(config.get("antenna_gain_dbi")),
    )


def build_scenario_from_inputs() -> ScenarioConfig:
    """Build the scenario by reading values from ``scenario_inputs.py``.

    Scenario interpretation
    -----------------------
    * GS1 is the broadcasting earth station.
    * The GEO satellite is nominally placed at 13 deg East.
    * GS2 is a receive-only dish terminal.
    * Uplink and downlink are calculated separately.
    * The clear-sky static baseline applies no rain/atmospheric fade.
    * Interference, dynamic Tsys, apparent motion, Monte-Carlo rain, ITU-R
      propagation, and DVB-S2 ACM are optional advanced extensions, each gated
      by its own ``enabled`` flag in ``scenario_inputs.py``.
    """

    gs1_location = _build_location(GS1)
    gs2_location = _build_location(GS2)

    satellite = GeoSatellite(
        name=str(SATELLITE["name"]),
        longitude_deg=float(SATELLITE["longitude_deg"]),
        latitude_deg=float(SATELLITE.get("latitude_deg", 0.0)),
        orbit_radius_km=_optional_float(SATELLITE.get("orbit_radius_km")),
    )

    gs1_tx_antenna = _build_dish_antenna(GS1)
    gs2_rx_antenna = _build_dish_antenna(GS2)

    gs1_tx = LinkEndpoint(
        name=str(GS1["terminal_name"]),
        location=gs1_location,
        antenna=gs1_tx_antenna,
        tx_power_dbw=watts_to_dbw(float(GS1["tx_power_w"])),
        tx_feeder_loss_db=float(GS1.get("tx_feeder_loss_db", 0.0)),
        notes=str(GS1.get("notes", "")),
    )

    sat_rx = LinkEndpoint(
        name=str(SATELLITE_UPLINK_RECEIVER["terminal_name"]),
        g_over_t_db_per_k_override=float(SATELLITE_UPLINK_RECEIVER["g_over_t_db_per_k_override"]),
        notes=str(SATELLITE_UPLINK_RECEIVER.get("notes", "")),
    )

    sat_tx = LinkEndpoint(
        name=str(SATELLITE_DOWNLINK_TRANSMITTER["terminal_name"]),
        eirp_dbw_override=float(SATELLITE_DOWNLINK_TRANSMITTER["eirp_dbw_override"]),
        notes=str(SATELLITE_DOWNLINK_TRANSMITTER.get("notes", "")),
    )

    gs2_rx = LinkEndpoint(
        name=str(GS2["terminal_name"]),
        location=gs2_location,
        antenna=gs2_rx_antenna,
        system_noise_temperature_k=float(GS2["system_noise_temperature_k"]),
        rx_feeder_loss_db=float(GS2.get("rx_feeder_loss_db", 0.0)),
        notes=str(GS2.get("notes", "")),
    )

    uplink_losses = LinkLosses(**UPLINK_LOSSES)
    downlink_losses = LinkLosses(**DOWNLINK_LOSSES)

    uplink = LinkConfig(
        name=str(UPLINK["name"]),
        transmitter=gs1_tx,
        receiver=sat_rx,
        frequency_hz=float(UPLINK["frequency_ghz"]) * GHZ,
        bandwidth_hz=float(UPLINK["bandwidth_mhz"]) * MHZ,
        bit_rate_bps=float(UPLINK["bit_rate_mbps"]) * 1.0e6,
        losses=uplink_losses,
        required_ebn0_db=float(UPLINK["required_ebn0_db"]),
    )

    downlink = LinkConfig(
        name=str(DOWNLINK["name"]),
        transmitter=sat_tx,
        receiver=gs2_rx,
        frequency_hz=float(DOWNLINK["frequency_ghz"]) * GHZ,
        bandwidth_hz=float(DOWNLINK["bandwidth_mhz"]) * MHZ,
        bit_rate_bps=float(DOWNLINK["bit_rate_mbps"]) * 1.0e6,
        losses=downlink_losses,
        required_ebn0_db=float(DOWNLINK["required_ebn0_db"]),
    )

    apparent_motion = GeoApparentMotion(**APPARENT_MOTION)
    interference = InterferenceConfig(**INTERFERENCE)
    dynamic_noise = DynamicNoiseConfig(**DYNAMIC_NOISE)
    rain_outage = RainOutageConfig(**RAIN_OUTAGE)
    digital = DigitalLinkConfig(**DIGITAL)
    itu_propagation = ITUPropagationConfig(**ITU_PROPAGATION)
    modcod = ModcodConfig(**MODCOD)

    return ScenarioConfig(
        name=SCENARIO_NAME,
        satellite=satellite,
        uplink=uplink,
        downlink=downlink,
        apparent_motion=apparent_motion,
        interference=interference,
        dynamic_noise=dynamic_noise,
        rain_outage=rain_outage,
        digital=digital,
        itu_propagation=itu_propagation,
        modcod=modcod,
    )


def apply_static_only(scenario: ScenarioConfig) -> ScenarioConfig:
    """Return a copy of the scenario reduced to the clear-sky static baseline.

    Static-only mode keeps the MATLAB-comparable clear-sky link budget (and its
    optional clean interference and digital metrics, if those are enabled) but
    disables every time-varying or fade-related extension: apparent motion,
    dynamic Tsys, Monte-Carlo rain, ITU-R propagation, and DVB-S2 ACM.
    """

    return replace(
        scenario,
        apparent_motion=replace(scenario.apparent_motion, enabled=False),
        dynamic_noise=replace(scenario.dynamic_noise, enabled=False),
        rain_outage=replace(scenario.rain_outage, enabled=False),
        itu_propagation=replace(scenario.itu_propagation, enabled=False),
        modcod=replace(scenario.modcod, enabled=False),
    )


def _format_value(value: object) -> str:
    """Return a human-readable string for terminal tables."""

    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:,.6f}"
    return str(value)


def print_key_value_table(title: str, rows: dict[str, object]) -> None:
    """Print a simple aligned key-value table to the terminal."""

    print("\n" + title)
    print("-" * len(title))
    max_key = max(len(str(key)) for key in rows)
    for key, value in rows.items():
        print(f"{key:<{max_key}} : {_format_value(value)}")


def write_csv_rows(path: Path, rows: Iterable[dict[str, object]]) -> bool:
    """Write row dictionaries to a UTF-8 CSV file; return True if anything was written."""

    rows = list(rows)
    if not rows or not rows[0]:
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return True


def _enabled_label(flag: bool) -> str:
    """Return ``"enabled"`` / ``"disabled"`` for a boolean flag."""

    return "enabled" if flag else "disabled"


def print_analysis_mode(scenario: ScenarioConfig, skip_plots: bool, static_only: bool) -> None:
    """Print a clear summary of which analyses and outputs are active."""

    print_key_value_table(
        "Analysis mode",
        {
            "Static clear-sky link budget": "enabled",
            "Interference (ASI + IMD)": _enabled_label(scenario.interference.enabled),
            "Digital metrics (BER/FEC/Shannon)": _enabled_label(scenario.digital.enabled),
            "Dynamic Tsys": _enabled_label(scenario.dynamic_noise.enabled),
            "Apparent GEO motion": _enabled_label(scenario.apparent_motion.enabled),
            "Monte-Carlo rain outage": _enabled_label(scenario.rain_outage.enabled),
            "ITU-R propagation": _enabled_label(scenario.itu_propagation.enabled),
            "DVB-S2 ACM": _enabled_label(scenario.modcod.enabled),
            "Plots": _enabled_label(not skip_plots),
            "Static-only mode": _enabled_label(static_only),
        },
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the command-line flags for the analyzer."""

    parser = argparse.ArgumentParser(
        description="UZB451 GEO bent-pipe link-budget analyzer.",
    )
    parser.add_argument(
        "--skip-plots",
        action="store_true",
        help="Write enabled CSV outputs but generate no plots.",
    )
    parser.add_argument(
        "--static-only",
        action="store_true",
        help="Run only the MATLAB-comparable clear-sky static link budget.",
    )
    return parser.parse_args(argv)


def _geometry_rows(static_result) -> list[dict[str, object]]:
    """Return the uplink/downlink geometry rows for CSV export."""

    rows = []
    for label, geometry in (
        ("uplink", static_result.uplink_geometry),
        ("downlink", static_result.downlink_geometry),
    ):
        rows.append(
            {
                "link": label,
                "ground_station": geometry.ground_station_name,
                "satellite": geometry.satellite_name,
                "satellite_longitude_deg": geometry.satellite_longitude_deg,
                "satellite_latitude_deg": geometry.satellite_latitude_deg,
                "satellite_radius_km": geometry.satellite_radius_km,
                "slant_range_km": geometry.slant_range_km,
                "elevation_deg": geometry.elevation_deg,
                "azimuth_deg": geometry.azimuth_deg,
                "central_angle_deg": geometry.central_angle_deg,
            }
        )
    return rows


def main(argv: list[str] | None = None) -> None:
    """Run the analysis pipeline, gating every output by its enabled flag."""

    args = parse_args(argv)

    scenario = build_scenario_from_inputs()
    if args.static_only:
        scenario = apply_static_only(scenario)

    warnings, errors = validate_scenario_config(scenario)
    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        raise ValueError(
            "Scenario configuration is invalid:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    print_analysis_mode(scenario, args.skip_plots, args.static_only)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    written_csvs: list[Path] = []

    def write(name: str, rows: list[dict[str, object]]) -> None:
        path = RESULTS_DIR / name
        if write_csv_rows(path, rows):
            written_csvs.append(path)

    # ---------------------------------------------------------------
    # Clear-sky static baseline (always runs; never includes fade).
    # ---------------------------------------------------------------
    static_result = calculate_scenario(scenario)
    geometry_rows = _geometry_rows(static_result)
    write("geometry_static.csv", geometry_rows)
    write("link_budget_static.csv", [static_result.uplink.to_dict(), static_result.downlink.to_dict()])
    write("scenario_summary_static.csv", [static_result.to_summary_dict()])

    print_key_value_table("Static Uplink Geometry", geometry_rows[0])
    print_key_value_table("Static Downlink Geometry", geometry_rows[1])
    print_key_value_table("Static Uplink Budget (clear-sky)", static_result.uplink.to_dict())
    print_key_value_table("Static Downlink Budget (clear-sky)", static_result.downlink.to_dict())
    print_key_value_table("Static Combined Link Budget (clear-sky)", static_result.to_summary_dict())

    if scenario.interference.enabled:
        write("interference_summary.csv", [static_result.interference.to_dict()])
        print_key_value_table("Interference (ASI + IMD)", static_result.interference.to_dict())

    if scenario.digital.enabled and static_result.digital is not None:
        write("digital_metrics_static.csv", [static_result.digital.to_dict()])
        print_key_value_table("Static Digital BER/FEC/Capacity Metrics", static_result.digital.to_dict())

    # ---------------------------------------------------------------
    # Dynamic clear-sky receiver-noise (advanced; needs dynamic Tsys).
    # ---------------------------------------------------------------
    if scenario.dynamic_noise.enabled:
        dynamic_result = calculate_scenario(scenario, use_dynamic_downlink_tsys=True)
        write("scenario_summary_dynamic_clear_sky.csv", [dynamic_result.to_summary_dict()])
        print_key_value_table("Dynamic Clear-Sky Combined Link", dynamic_result.to_summary_dict())
        if scenario.digital.enabled and dynamic_result.digital is not None:
            write("digital_metrics_dynamic_clear_sky.csv", [dynamic_result.digital.to_dict()])
    else:
        print("\nDynamic Tsys disabled; skipping dynamic clear-sky receiver-noise analysis.")

    # ---------------------------------------------------------------
    # Apparent GEO station-keeping motion (advanced).
    # ---------------------------------------------------------------
    time_samples = []
    if scenario.apparent_motion.enabled:
        time_samples = simulate_time_varying_scenario(scenario)
        write("time_varying_link_budget.csv", [s.to_dict() for s in time_samples])
        write("time_varying_summary.csv", [summarize_time_varying_results(time_samples)])
        print_key_value_table("Time-Varying Summary", summarize_time_varying_results(time_samples))
    else:
        print("Apparent GEO motion disabled; skipping time-varying simulation.")

    # ---------------------------------------------------------------
    # Educational Monte-Carlo rain outage (advanced).
    # ---------------------------------------------------------------
    monte_carlo_samples = []
    if scenario.rain_outage.enabled:
        monte_carlo_samples = simulate_monte_carlo_rain_outage(scenario)
        write("availability_monte_carlo.csv", [s.to_dict() for s in monte_carlo_samples])
        write("availability_summary.csv", [summarize_monte_carlo_availability(monte_carlo_samples)])
        print_key_value_table(
            "Monte-Carlo Availability Summary", summarize_monte_carlo_availability(monte_carlo_samples)
        )
    else:
        print("Rain outage model disabled; skipping Monte-Carlo availability analysis.")

    # ---------------------------------------------------------------
    # Standards-based ITU-R propagation and DVB-S2 ACM (advanced).
    # ---------------------------------------------------------------
    itu_curve = []
    if scenario.itu_propagation.enabled:
        itu_design = calculate_scenario_with_itu(scenario)
        itu_curve = calculate_itu_availability_curve(scenario)
        itu_summary = summarize_itu_availability_curve(itu_curve, itu_design)
        write("itu_design_point.csv", [itu_design.to_dict()])
        write("itu_availability_curve.csv", [r.to_dict() for r in itu_curve])
        write("itu_summary.csv", [itu_summary])
        print_key_value_table(
            f"ITU-R Design Point ({itu_design.design_availability_percent:g}% availability)",
            itu_design.to_dict(),
        )
        print_key_value_table("ITU-R Availability Summary", itu_summary)
        if scenario.modcod.enabled and itu_design.downlink_modcod is not None:
            write("dvbs2_acm_downlink.csv", [itu_design.downlink_modcod.to_dict()])
            print_key_value_table("DVB-S2 ACM Downlink Selection", itu_design.downlink_modcod.to_dict())
    else:
        print("ITU-R propagation disabled; skipping ITU availability analysis.")

    if not scenario.modcod.enabled:
        print("DVB-S2 ACM disabled; skipping MODCOD selection.")
    elif not scenario.itu_propagation.enabled:
        print("DVB-S2 ACM requires the ITU-R faded downlink; skipping MODCOD selection.")

    # ---------------------------------------------------------------
    # CSV summary.
    # ---------------------------------------------------------------
    print("\nCSV outputs:")
    for path in written_csvs:
        print(f"- {path}")

    # ---------------------------------------------------------------
    # Plots (each bundle skips its own disabled sections internally).
    # ---------------------------------------------------------------
    if args.skip_plots:
        print("\nPlots disabled (--skip-plots); no figures generated.")
    else:
        contour_paths = generate_contour_plots(scenario, PLOTS_DIR)
        advanced_paths = generate_advanced_plots(scenario, time_samples, monte_carlo_samples, PLOTS_DIR)
        itu_paths = generate_itu_plots(scenario, itu_curve, PLOTS_DIR)
        for header, paths in (
            ("Generated contour plots:", contour_paths),
            ("Generated advanced plots:", advanced_paths),
            ("Generated ITU-R / DVB-S2 plots:", itu_paths),
        ):
            if paths:
                print(f"\n{header}")
                for path in paths:
                    print(f"- {path}")
                    pdf = path.with_suffix(".pdf")
                    if pdf.exists():
                        print(f"- {pdf}")

    print(
        "\nNote: the default parameters are example values; replace them with "
        "datasheet/measured values before the final report. The clear-sky static "
        "baseline never includes rain or atmospheric fade. ITU-R propagation and "
        "DVB-S2 ACM are separate advanced extensions and are standards-based "
        "engineering implementations, not regulatory-grade or map-exact tools."
    )


if __name__ == "__main__":
    main()
