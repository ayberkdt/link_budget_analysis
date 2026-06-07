from dataclasses import replace

import pytest
from src.calculations import (
    calculate_scenario,
    combine_inverse_db,
    dish_gain_dbi,
    free_space_path_loss_db,
    validate_scenario_config,
)
from src.main import (
    build_mode_definitions_rows,
    build_parameter_source_rows,
    build_scenario_from_inputs,
)

def test_free_space_path_loss():
    # Test typical Ku-band FSPL
    fspl = free_space_path_loss_db(frequency_hz=12e9, range_km=38000.0)
    # Expected: ~205.6 dB
    assert pytest.approx(fspl, 0.1) == 205.6

def test_combine_inverse_db():
    # Two identical links at 10 dB C/N results in approx 7 dB (exactly 6.9897 dB)
    combined = combine_inverse_db([10.0, 10.0])
    assert pytest.approx(combined, 0.01) == 6.99

def test_dish_gain_dbi():
    # Typical uplink dish (2.4m at 14 GHz, 62% efficiency)
    gain = dish_gain_dbi(diameter_m=2.4, frequency_hz=14e9, efficiency=0.62)
    # Expected: ~48.86 dBi
    assert pytest.approx(gain, 0.1) == 48.86

def test_invalid_fspl():
    with pytest.raises(ValueError):
        free_space_path_loss_db(frequency_hz=0.0, range_km=38000.0)

def test_full_static_scenario_regression():
    # End-to-end regression test to ensure core numerical results from the report remain stable
    scenario = build_scenario_from_inputs()
    result = calculate_scenario(scenario)

    assert result.combined_cn0_dbhz == pytest.approx(81.15, abs=0.05)
    assert result.combined_ebn0_db == pytest.approx(11.15, abs=0.05)
    assert result.combined_margin_db == pytest.approx(4.15, abs=0.05)
    
    if result.combined_margin_ni_db is not None:
        assert result.combined_margin_ni_db == pytest.approx(3.69, abs=0.1)

def test_parameter_source_rows():
    scenario = build_scenario_from_inputs()
    rows = build_parameter_source_rows(scenario)
    assert len(rows) > 10
    assert "parameter" in rows[0]

    changed = replace(
        scenario,
        uplink=replace(scenario.uplink, bit_rate_bps=99e6, bandwidth_hz=72e6),
        downlink=replace(scenario.downlink, bit_rate_bps=99e6, bandwidth_hz=72e6),
        required_end_to_end_ebn0_db=12.0,
    )
    changed_rows = {row["parameter"]: row["value"] for row in build_parameter_source_rows(changed)}
    assert changed_rows["Fixed-rate bit rate"] == pytest.approx(99.0)
    assert changed_rows["ACM carrier bandwidth"] == pytest.approx(72.0)
    assert changed_rows["Required fixed-rate Eb/N0"] == pytest.approx(12.0)

    modes = build_mode_definitions_rows(changed)
    assert modes[0]["bit_rate_Mbps"] == "99"
    assert modes[0]["bandwidth_MHz"] == "72"
    assert "12 dB" in modes[0]["threshold_basis"]


def test_validation_rejects_invalid_probabilities_ranges_and_link_mismatch():
    scenario = build_scenario_from_inputs()
    invalid = replace(
        scenario,
        downlink=replace(scenario.downlink, bit_rate_bps=11e6),
        rain_outage=replace(
            scenario.rain_outage,
            light_rain_probability=0.8,
            moderate_rain_probability=0.8,
            heavy_rain_probability=0.8,
            heavy_rain_attenuation_range_db=(18.0, 7.0),
        ),
    )
    _, errors = validate_scenario_config(invalid)

    assert any("bit rates must match" in error for error in errors)
    assert any("probabilities must sum" in error for error in errors)
    assert any("ordered low <= high" in error for error in errors)

    with pytest.raises(ValueError, match="bit rates must match"):
        calculate_scenario(invalid)
