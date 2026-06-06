import pytest
from src.calculations import free_space_path_loss_db, combine_inverse_db, dish_gain_dbi, calculate_scenario
from src.main import build_scenario_from_inputs, build_parameter_source_rows

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
