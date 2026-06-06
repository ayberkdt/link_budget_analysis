import pytest
from src.itu_propagation import rain_height_km, rain_coefficients_p838

def test_rain_height_km():
    # Test typical mid-latitude
    # For phi = 40 (between 23 and 71): h0 = 5.0 - 0.075 * (40 - 23) = 5.0 - 1.275 = 3.725
    # hR = h0 + 0.36 = 4.085
    hr = rain_height_km(latitude_deg=40.0)
    assert pytest.approx(hr, 0.01) == 4.085

    # Test equator
    hr_equator = rain_height_km(latitude_deg=10.0)
    assert hr_equator == 5.36

def test_rain_coefficients_p838():
    # Evaluate at 12 GHz, 40 deg elevation, linear (90 deg tilt)
    k, alpha = rain_coefficients_p838(frequency_ghz=12.0, elevation_deg=40.0, polarization_tilt_deg=90.0)
    # k and alpha should be positive real numbers
    assert k > 0.0
    assert alpha > 0.0
    assert isinstance(k, float)
    assert isinstance(alpha, float)

def test_rain_coefficients_invalid_frequency():
    with pytest.raises(ValueError):
        rain_coefficients_p838(frequency_ghz=0.5, elevation_deg=40.0)
