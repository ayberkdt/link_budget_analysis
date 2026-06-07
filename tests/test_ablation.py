from dataclasses import replace

import pytest

from src.calculations import (
    calculate_geo_link_geometry,
    simulate_monte_carlo_rain_outage,
    summarize_monte_carlo_availability,
)
from src.entities import GeoSatellite, Location
from src.main import (
    apply_static_only,
    build_ablation_rows,
    build_scenario_from_inputs,
)


@pytest.fixture(scope="module")
def ablation_rows():
    return {
        row["stage"]: row
        for row in build_ablation_rows(build_scenario_from_inputs())
    }


def test_geo_geometry_regression_for_hotbird_and_intelsat():
    rome = Location("Rome", 41.9028, 12.4964)
    ankara = Location("Ankara", 39.9334, 32.8597)

    hotbird = GeoSatellite("HOTBIRD 13G", 13.0)
    intelsat = GeoSatellite("Intelsat 39", 62.0)

    assert calculate_geo_link_geometry(rome, hotbird).elevation_deg == pytest.approx(41.60, abs=0.02)
    assert calculate_geo_link_geometry(ankara, hotbird).elevation_deg == pytest.approx(39.44, abs=0.02)
    assert calculate_geo_link_geometry(rome, intelsat).elevation_deg == pytest.approx(20.77, abs=0.02)
    assert calculate_geo_link_geometry(ankara, intelsat).elevation_deg == pytest.approx(34.92, abs=0.02)


def test_static_only_disables_time_varying_and_fade_modules():
    static = apply_static_only(build_scenario_from_inputs())

    assert not static.apparent_motion.enabled
    assert not static.dynamic_noise.enabled
    assert not static.rain_outage.enabled
    assert not static.itu_propagation.enabled
    assert not static.modcod.enabled


def test_ablation_separates_asi_and_imd_penalties(ablation_rows):
    assert ablation_rows["A0"]["fixed_rate_margin_dB"] > ablation_rows["A1"]["fixed_rate_margin_dB"]
    assert ablation_rows["A1"]["fixed_rate_margin_dB"] > ablation_rows["A2"]["fixed_rate_margin_dB"]
    assert ablation_rows["A1"]["delta_margin_dB"] == pytest.approx(-0.445, abs=0.01)
    assert ablation_rows["A2"]["delta_margin_dB"] == pytest.approx(-0.014, abs=0.005)


def test_ablation_separates_rain_loss_and_dynamic_sky_noise(ablation_rows):
    assert ablation_rows["A3"]["fixed_rate_margin_dB"] > ablation_rows["A4"]["fixed_rate_margin_dB"]
    assert ablation_rows["A4"]["fixed_rate_margin_dB"] > ablation_rows["A5"]["fixed_rate_margin_dB"]
    assert ablation_rows["A4"]["fixed_rate_10Mbps_closed"]
    assert not ablation_rows["A5"]["fixed_rate_10Mbps_closed"]
    assert ablation_rows["A5"]["downlink_Tsys_K"] > ablation_rows["A4"]["downlink_Tsys_K"]
    assert ablation_rows["A5"]["downlink_Tsys_K"] == pytest.approx(239.1, abs=0.5)


def test_acm_changes_service_mode_not_physical_margin(ablation_rows):
    assert ablation_rows["A6"]["fixed_rate_margin_dB"] == pytest.approx(
        ablation_rows["A5"]["fixed_rate_margin_dB"], abs=1.0e-12
    )
    assert ablation_rows["A6"]["selected_MODCOD"] == "QPSK 1/2"
    assert ablation_rows["A6"]["ACM_net_throughput_Mbps"] == pytest.approx(29.67, abs=0.02)


def test_clear_sky_dynamic_tsys_and_geo_motion_diagnostics(ablation_rows):
    assert ablation_rows["D0"]["downlink_Tsys_K"] < 150.0
    assert ablation_rows["D0"]["delta_margin_dB"] > 0.0
    assert 0.0 < ablation_rows["D1"]["margin_peak_to_peak_dB"] < 0.03
    assert ablation_rows["D1"]["margin_min_dB"] < ablation_rows["D1"]["margin_max_dB"]


def test_monte_carlo_is_reproducible_for_fixed_seed():
    scenario = build_scenario_from_inputs()
    compact = replace(
        scenario,
        apparent_motion=replace(scenario.apparent_motion, enabled=False),
        rain_outage=replace(scenario.rain_outage, samples_per_year=256),
    )

    first = simulate_monte_carlo_rain_outage(compact)
    second = simulate_monte_carlo_rain_outage(compact)
    first_summary = summarize_monte_carlo_availability(first)
    second_summary = summarize_monte_carlo_availability(second)

    assert [sample.downlink_rain_attenuation_db for sample in first] == [
        sample.downlink_rain_attenuation_db for sample in second
    ]
    assert first_summary == second_summary
    assert 0.0 <= float(first_summary["availability_percent"]) <= 100.0
