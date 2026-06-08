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

if __package__:
    from .calculations import (
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
    from .constants import GHZ, MHZ
    from .entities import (
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
    from .plotting import generate_advanced_plots, generate_contour_plots, generate_itu_plots
    from .scenario_inputs import (
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
else:
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
REPORT_PARAMETERS_PATH = Path("LaTeX Rapor") / "parameters.tex"


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
      propagation, and DVB-S2 ACM are optional modules, each gated
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


def build_parameter_source_rows(scenario: ScenarioConfig) -> list[dict[str, object]]:
    """Return rows for the parameter_sources.csv output."""
    gs1 = scenario.uplink.transmitter.location
    gs2 = scenario.downlink.receiver.location
    gs1_antenna = scenario.uplink.transmitter.antenna
    gs2_antenna = scenario.downlink.receiver.antenna
    tx_power_dbw = scenario.uplink.transmitter.tx_power_dbw
    tx_power_w = 10.0 ** (tx_power_dbw / 10.0) if tx_power_dbw is not None else None

    return [
        {"parameter": "GS1 latitude", "value": gs1.latitude_deg if gs1 else None, "unit": "deg", "status": "sourced", "source_or_note": "Rome coordinate input"},
        {"parameter": "GS1 longitude", "value": gs1.longitude_deg if gs1 else None, "unit": "deg", "status": "sourced", "source_or_note": "Rome coordinate input"},
        {"parameter": "GS1 dish diameter", "value": gs1_antenna.diameter_m if gs1_antenna else None, "unit": "m", "status": "datasheet_or_selected", "source_or_note": "Andrew Type 243 selected project dish"},
        {"parameter": "GS1 antenna efficiency", "value": gs1_antenna.efficiency if gs1_antenna else None, "unit": "-", "status": "assumed", "source_or_note": "Representative aperture efficiency"},
        {"parameter": "GS1 HPA power", "value": tx_power_w, "unit": "W", "status": "datasheet_supported", "source_or_note": "Norsat ATOMBKU020 P1dB 43 dBm minimum"},
        {"parameter": "GS1 feeder loss", "value": scenario.uplink.transmitter.tx_feeder_loss_db, "unit": "dB", "status": "assumed", "source_or_note": "Representative uplink feeder allowance"},
        {"parameter": "Satellite longitude", "value": scenario.satellite.longitude_deg, "unit": "deg", "status": "sourced", "source_or_note": "Selected GEO orbital slot"},
        {"parameter": "Satellite downlink EIRP", "value": scenario.downlink.transmitter.eirp_dbw_override, "unit": "dBW", "status": "estimated", "source_or_note": "Estimated from HOTBIRD footprint contour at Ankara"},
        {"parameter": "Satellite receive G/T", "value": scenario.uplink.receiver.g_over_t_db_per_k_override, "unit": "dB/K", "status": "assumed", "source_or_note": "Selected-transponder uplink G/T unavailable"},
        {"parameter": "GS2 latitude", "value": gs2.latitude_deg if gs2 else None, "unit": "deg", "status": "sourced", "source_or_note": "Ankara coordinate input"},
        {"parameter": "GS2 longitude", "value": gs2.longitude_deg if gs2 else None, "unit": "deg", "status": "sourced", "source_or_note": "Ankara coordinate input"},
        {"parameter": "GS2 dish diameter", "value": gs2_antenna.diameter_m if gs2_antenna else None, "unit": "m", "status": "datasheet_or_selected", "source_or_note": "Triax TD88 represented by an equivalent circular aperture"},
        {"parameter": "GS2 antenna efficiency", "value": gs2_antenna.efficiency if gs2_antenna else None, "unit": "-", "status": "assumed", "source_or_note": "Representative aperture efficiency"},
        {"parameter": "GS2 system noise temperature", "value": scenario.downlink.receiver.system_noise_temperature_k, "unit": "K", "status": "assumed", "source_or_note": "Representative Ku-band receive-system estimate"},
        {"parameter": "GS2 receiver feeder loss", "value": scenario.downlink.receiver.rx_feeder_loss_db, "unit": "dB", "status": "assumed", "source_or_note": "Representative receive feeder allowance"},
        {"parameter": "Uplink pointing loss", "value": scenario.uplink.losses.pointing_loss_db, "unit": "dB", "status": "assumed", "source_or_note": "Engineering pointing allowance"},
        {"parameter": "Downlink pointing loss", "value": scenario.downlink.losses.pointing_loss_db, "unit": "dB", "status": "assumed", "source_or_note": "Engineering pointing allowance"},
        {"parameter": "Uplink polarization loss", "value": scenario.uplink.losses.polarization_loss_db, "unit": "dB", "status": "assumed", "source_or_note": "Engineering polarization mismatch allowance"},
        {"parameter": "Downlink polarization loss", "value": scenario.downlink.losses.polarization_loss_db, "unit": "dB", "status": "assumed", "source_or_note": "Engineering polarization mismatch allowance"},
        {"parameter": "Static uplink atmospheric allowance", "value": scenario.uplink.losses.atmospheric_loss_db, "unit": "dB", "status": "assumed", "source_or_note": "Replaced, not added, in the advanced ITU branch"},
        {"parameter": "Static downlink atmospheric allowance", "value": scenario.downlink.losses.atmospheric_loss_db, "unit": "dB", "status": "assumed", "source_or_note": "Replaced, not added, in the advanced ITU branch"},
        {"parameter": "Required fixed-rate Eb/N0", "value": scenario.required_end_to_end_ebn0_db, "unit": "dB", "status": "assumed", "source_or_note": "Conservative fixed-rate design threshold"},
        {"parameter": "R0.01 rainfall rate", "value": scenario.itu_propagation.rain_rate_001_mm_per_h, "unit": "mm/h", "status": "representative", "source_or_note": "Shared representative P.837-based input; not a map extraction"},
        {"parameter": "ITU-R polarization tilt", "value": scenario.itu_propagation.polarization_tilt_deg, "unit": "deg", "status": "assumed", "source_or_note": "Vertical linear polarization for P.838"},
        {"parameter": "DVB-S2 rolloff", "value": scenario.modcod.rolloff_factor, "unit": "-", "status": "assumed", "source_or_note": "DVB-S2 ACM carrier roll-off"},
        {"parameter": "DVB-S2 implementation margin", "value": scenario.modcod.implementation_margin_db, "unit": "dB", "status": "assumed", "source_or_note": "Representative modem threshold back-off"},
        {"parameter": "ACM carrier bandwidth", "value": scenario.downlink.bandwidth_hz / MHZ, "unit": "MHz", "status": "configured", "source_or_note": "DVB-S2 carrier bandwidth"},
        {"parameter": "Fixed-rate bit rate", "value": scenario.downlink.bit_rate_bps / 1.0e6, "unit": "Mbps", "status": "configured", "source_or_note": "Fixed-rate closure-mode bit rate"},
    ]


def build_mode_definitions_rows(scenario: ScenarioConfig) -> list[dict[str, object]]:
    """Return rows defining fixed-rate vs ACM modes."""
    bit_rate_mbps = scenario.downlink.bit_rate_bps / 1.0e6
    bandwidth_mhz = scenario.downlink.bandwidth_hz / MHZ
    return [
        {
            "mode": "fixed_rate",
            "bit_rate_Mbps": f"{bit_rate_mbps:g}",
            "bandwidth_MHz": f"{bandwidth_mhz:g}",
            "metric": "Eb/N0",
            "threshold_basis": f"required Eb/N0 = {scenario.required_end_to_end_ebn0_db:g} dB",
            "note": "Fixed-rate closure mode",
        },
        {
            "mode": "DVB-S2 ACM",
            "bit_rate_Mbps": "variable",
            "bandwidth_MHz": f"{bandwidth_mhz:g}",
            "metric": "Es/N0",
            "threshold_basis": "DVB-S2 MODCOD table + implementation margin",
            "note": f"Variable-throughput carrier mode; separate from fixed {bit_rate_mbps:g} Mbps closure",
        },
    ]


def write_report_parameters(
    scenario: ScenarioConfig,
    static_result,
    itu_design,
    uplink_only_design,
    downlink_only_design,
) -> Path:
    """Write LaTeX macros directly from the current computed results."""

    selection = itu_design.downlink_modcod
    throughput_mbps = (
        selection.net_throughput_bps / 1.0e6
        if selection is not None and selection.selected is not None
        else 0.0
    )
    available_esn0_db = selection.available_esn0_db if selection is not None else float("nan")
    text = f"""% parameters.tex
% Auto-generated by src/main.py. Do not edit numerical values by hand.

% --- Geometry and system ---
\\newcommand{{\\gsOneDish}}{{{scenario.uplink.transmitter.antenna.diameter_m:g}}}
\\newcommand{{\\gsTwoDish}}{{{scenario.downlink.receiver.antenna.diameter_m:g}}}
\\newcommand{{\\satEIRP}}{{{scenario.downlink.transmitter.eirp_dbw_override:g}}}
\\newcommand{{\\satGT}}{{{scenario.uplink.receiver.g_over_t_db_per_k_override:.1f}}}
\\newcommand{{\\reqEbNo}}{{{scenario.required_end_to_end_ebn0_db:.2f}}}
\\newcommand{{\\upSlantRange}}{{{static_result.uplink.range_km:,.2f}}}
\\newcommand{{\\downSlantRange}}{{{static_result.downlink.range_km:,.2f}}}

% --- Static clear-sky results ---
\\newcommand{{\\cnTotal}}{{{static_result.combined_cn0_dbhz:.2f}}}
\\newcommand{{\\ebnoTotal}}{{{static_result.combined_ebn0_db:.2f}}}
\\newcommand{{\\marginClear}}{{{static_result.combined_margin_db:.2f}}}
\\newcommand{{\\marginASI}}{{{static_result.combined_margin_ni_db:.2f}}}
\\newcommand{{\\upFSPL}}{{{static_result.uplink.free_space_loss_db:.2f}}}
\\newcommand{{\\downFSPL}}{{{static_result.downlink.free_space_loss_db:.2f}}}

% --- Per-path p-point and coincident dual-site stress results ---
\\newcommand{{\\marginUplinkFade}}{{{uplink_only_design.faded_result.combined_margin_ni_db:.2f}}}
\\newcommand{{\\marginDownlinkFade}}{{{downlink_only_design.faded_result.combined_margin_ni_db:.2f}}}
\\newcommand{{\\marginRain}}{{{itu_design.faded_result.combined_margin_ni_db:.2f}}}
\\newcommand{{\\downlinkEsnoRain}}{{{available_esn0_db:.2f}}}
\\newcommand{{\\throughputRain}}{{{throughput_mbps:.2f}}}
\\newcommand{{\\upRainAtten}}{{{itu_design.uplink_breakdown.total_db:.2f}}}
\\newcommand{{\\downRainAtten}}{{{itu_design.downlink_breakdown.total_db:.2f}}}
"""
    REPORT_PARAMETERS_PATH.write_text(text, encoding="utf-8")
    return REPORT_PARAMETERS_PATH


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


def build_ablation_rows(scenario: ScenarioConfig) -> list[dict[str, object]]:
    """Return cumulative and diagnostic rows for the advanced-model ablation study.

    The cumulative chain separates carrier degradation from receiver-noise
    degradation: interference is added first, the fixed atmospheric allowance
    is replaced by the ITU-R-informed model, rain attenuation is added, the
    receiver-temperature model is changed under otherwise identical conditions,
    atmospheric emission is added, and ACM is evaluated as a response.
    """

    no_interference = replace(
        scenario,
        interference=replace(scenario.interference, enabled=False),
        dynamic_noise=replace(scenario.dynamic_noise, enabled=False),
    )
    asi_only = replace(
        scenario,
        interference=replace(scenario.interference, enabled=True, imd_c_i_db=None),
        dynamic_noise=replace(scenario.dynamic_noise, enabled=False),
    )
    asi_imd = replace(
        scenario,
        interference=replace(scenario.interference, enabled=True),
        dynamic_noise=replace(scenario.dynamic_noise, enabled=False),
    )

    thermal_result = calculate_scenario(no_interference)
    asi_result = calculate_scenario(asi_only)
    asi_imd_result = calculate_scenario(asi_imd)

    non_rain_fixed_scenario = replace(
        asi_imd,
        itu_propagation=replace(
            scenario.itu_propagation,
            enabled=True,
            rain_rate_001_mm_per_h=0.0,
        ),
    )
    non_rain_fixed = calculate_scenario_with_itu(non_rain_fixed_scenario)

    full_fixed_scenario = replace(
        asi_imd,
        itu_propagation=replace(scenario.itu_propagation, enabled=True),
    )
    full_fixed = calculate_scenario_with_itu(full_fixed_scenario)

    full_dynamic_scenario = replace(
        scenario,
        interference=replace(scenario.interference, enabled=True),
        dynamic_noise=replace(scenario.dynamic_noise, enabled=True),
        itu_propagation=replace(scenario.itu_propagation, enabled=True),
        modcod=replace(scenario.modcod, enabled=True),
    )
    full_dynamic_no_emission = calculate_scenario_with_itu(
        full_dynamic_scenario,
        include_atmospheric_emission=False,
    )
    full_dynamic = calculate_scenario_with_itu(full_dynamic_scenario)

    dynamic_clear_result = calculate_scenario(
        full_dynamic_scenario,
        use_dynamic_downlink_tsys=True,
    )
    motion_scenario = replace(
        full_dynamic_scenario,
        apparent_motion=replace(scenario.apparent_motion, enabled=True),
    )
    motion_summary = summarize_time_varying_results(
        simulate_time_varying_scenario(motion_scenario)
    )

    def result_row(
        stage: str,
        evaluation: str,
        active_effects: str,
        result,
        delta_margin_db: float | None,
        uplink_attenuation_db: float = 0.0,
        downlink_attenuation_db: float = 0.0,
        selected_modcod: str = "not evaluated",
        throughput_mbps: float | None = None,
        margin_min_db: float | None = None,
        margin_max_db: float | None = None,
        margin_peak_to_peak_db: float = 0.0,
        interpretation: str = "",
    ) -> dict[str, object]:
        margin = result.combined_margin_ni_db
        return {
            "stage": stage,
            "evaluation": evaluation,
            "active_effects": active_effects,
            "fixed_rate_margin_dB": margin,
            "delta_margin_dB": delta_margin_db,
            "margin_min_dB": margin if margin_min_db is None else margin_min_db,
            "margin_max_dB": margin if margin_max_db is None else margin_max_db,
            "margin_peak_to_peak_dB": margin_peak_to_peak_db,
            "uplink_excess_attenuation_dB": uplink_attenuation_db,
            "downlink_excess_attenuation_dB": downlink_attenuation_db,
            "downlink_Tsys_K": result.downlink.system_noise_temperature_k,
            "fixed_rate_bit_rate_Mbps": scenario.downlink.bit_rate_bps / 1.0e6,
            "fixed_rate_closed": margin >= 0.0,
            "selected_MODCOD": selected_modcod,
            "ACM_net_throughput_Mbps": throughput_mbps,
            "interpretation": interpretation,
        }

    margin_thermal = thermal_result.combined_margin_ni_db
    margin_asi = asi_result.combined_margin_ni_db
    margin_asi_imd = asi_imd_result.combined_margin_ni_db
    margin_non_rain = non_rain_fixed.faded_result.combined_margin_ni_db
    margin_full_fixed = full_fixed.faded_result.combined_margin_ni_db
    margin_full_dynamic_no_emission = (
        full_dynamic_no_emission.faded_result.combined_margin_ni_db
    )
    margin_full_dynamic = full_dynamic.faded_result.combined_margin_ni_db

    selection = full_dynamic.downlink_modcod
    selected_name = (
        selection.selected.name
        if selection is not None and selection.selected is not None
        else "outage"
    )
    throughput_mbps = (
        selection.net_throughput_bps / 1.0e6 if selection is not None else None
    )

    rows = [
        result_row(
            "A0",
            "cumulative",
            "Thermal-noise-only static baseline",
            thermal_result,
            0.0,
            interpretation="Reference clear-sky fixed-rate link.",
        ),
        result_row(
            "A1",
            "cumulative",
            "A0 + adjacent-satellite interference",
            asi_result,
            margin_asi - margin_thermal,
            interpretation="Isolates the ASI penalty.",
        ),
        result_row(
            "A2",
            "cumulative",
            "A1 + transponder IMD",
            asi_imd_result,
            margin_asi_imd - margin_asi,
            interpretation="Isolates the additional IMD penalty.",
        ),
        result_row(
            "A3",
            "cumulative",
            "A2 + replace fixed atmosphere with gas, cloud, and scintillation; fixed Tsys",
            non_rain_fixed.faded_result,
            margin_non_rain - margin_asi_imd,
            uplink_attenuation_db=non_rain_fixed.uplink_breakdown.total_db,
            downlink_attenuation_db=non_rain_fixed.downlink_breakdown.total_db,
            interpretation="Replaces the fixed clear-sky atmospheric allowance.",
        ),
        result_row(
            "A4",
            "cumulative",
            "A3 + rain attenuation; fixed Tsys",
            full_fixed.faded_result,
            margin_full_fixed - margin_non_rain,
            uplink_attenuation_db=full_fixed.uplink_breakdown.total_db,
            downlink_attenuation_db=full_fixed.downlink_breakdown.total_db,
            interpretation="Adds rain carrier attenuation without rain-emission noise.",
        ),
        result_row(
            "A5",
            "cumulative",
            "A4 + dynamic clear-sky receiver Tsys; emission disabled",
            full_dynamic_no_emission.faded_result,
            margin_full_dynamic_no_emission - margin_full_fixed,
            uplink_attenuation_db=full_dynamic_no_emission.uplink_breakdown.total_db,
            downlink_attenuation_db=full_dynamic_no_emission.downlink_breakdown.total_db,
            interpretation="Changes only the receiver-temperature baseline.",
        ),
        result_row(
            "A6",
            "cumulative",
            "A5 + atmospheric emission in downlink Tsys",
            full_dynamic.faded_result,
            margin_full_dynamic - margin_full_dynamic_no_emission,
            uplink_attenuation_db=full_dynamic.uplink_breakdown.total_db,
            downlink_attenuation_db=full_dynamic.downlink_breakdown.total_db,
            interpretation="Isolates the receiver-noise increase caused by the lossy sky.",
        ),
        result_row(
            "A7",
            "response",
            "A6 + DVB-S2 ACM selection",
            full_dynamic.faded_result,
            0.0,
            uplink_attenuation_db=full_dynamic.uplink_breakdown.total_db,
            downlink_attenuation_db=full_dynamic.downlink_breakdown.total_db,
            selected_modcod=selected_name,
            throughput_mbps=throughput_mbps,
            interpretation="ACM changes the service mode, not the physical fixed-rate margin.",
        ),
        result_row(
            "D1",
            "isolated diagnostic",
            "ASI + IMD + dynamic clear-sky Tsys + 48-hour GEO motion",
            dynamic_clear_result,
            None,
            margin_min_db=float(motion_summary["combined_margin_with_interference_min_dB"]),
            margin_max_db=float(motion_summary["combined_margin_with_interference_max_dB"]),
            margin_peak_to_peak_db=float(
                motion_summary["combined_margin_with_interference_peak_to_peak_dB"]
            ),
            interpretation="Reports the margin envelope rather than a one-sided penalty.",
        ),
    ]
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
    write("parameter_sources.csv", build_parameter_source_rows(scenario))
    write("mode_definitions.csv", build_mode_definitions_rows(scenario))
    write("geometry_static.csv", geometry_rows)
    write("link_budget_static.csv", [static_result.uplink.to_dict(), static_result.downlink.to_dict()])
    write("scenario_summary_static.csv", [static_result.to_summary_dict()])
    if not args.static_only:
        write("ablation_summary.csv", build_ablation_rows(scenario))

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
    # Monte-Carlo rain outage.
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
    itu_design = None
    if scenario.itu_propagation.enabled:
        uplink_only_design = calculate_scenario_with_itu(scenario, fade_application="uplink")
        downlink_only_design = calculate_scenario_with_itu(scenario, fade_application="downlink")
        itu_design = calculate_scenario_with_itu(scenario, fade_application="both")
        itu_curve = calculate_itu_availability_curve(scenario)
        itu_summary = summarize_itu_availability_curve(itu_curve, itu_design)
        write("itu_design_point.csv", [itu_design.to_dict()])
        write(
            "itu_design_cases.csv",
            [
                uplink_only_design.to_dict(),
                downlink_only_design.to_dict(),
                itu_design.to_dict(),
            ],
        )
        write("itu_availability_curve.csv", [r.to_dict() for r in itu_curve])
        write("itu_summary.csv", [itu_summary])
        parameters_path = write_report_parameters(
            scenario,
            static_result,
            itu_design,
            uplink_only_design,
            downlink_only_design,
        )
        print(f"\nUpdated report parameters: {parameters_path}")
        print_key_value_table(
            (
                "ITU-R Coincident Dual-Site Stress Point "
                f"(per-path p={itu_design.design_exceedance_percent:g}%)"
            ),
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
        "\nNote: several scenario parameters are representative engineering assumptions "
        "or footprint-based estimates, as documented in parameter_sources.csv and the report. "
        "The clear-sky static baseline never includes rain fade. The ITU-R-informed "
        "propagation and DVB-S2 ACM extensions are engineering models, not regulatory-grade "
        "or map-exact tools. The dual-site p-point is a coincident stress case, not a joint "
        "end-to-end availability guarantee."
    )


if __name__ == "__main__":
    main()
