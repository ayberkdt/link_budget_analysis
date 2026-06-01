"""Editable scenario inputs for the GEO link-budget analyzer.

Update the values in this file when you want to analyze a different GS1, GS2,
or satellite setup. ``main.py`` reads this module each time it runs, so any
changes made here are applied automatically on the next execution.
 adds two new input blocks at the bottom:

* ``ITU_PROPAGATION`` drives the standards-based ITU-R P.618/P.676/P.840 fade
  model. Replace ``rain_rate_001_mm_per_h`` with the ITU-R P.837 value for your
  site and set ``design_availability_percent`` to your link requirement.
* ``MODCOD`` configures the DVB-S2 adaptive coding-and-modulation layer.
"""

SCENARIO_NAME = "Rome to Ankara Link via Hotbird 13G "


# ========================================================================
# 1.                          GROUND STATION 1 
# ========================================================================
GS1 = {
    "site_name": "GS1 Rome",
    "latitude_deg": 41.9028,
    "longitude_deg": 12.4964,
    "altitude_km": 0.0,
    "terminal_name": "GS1 transmitter",
    "antenna_name": "GS1 Ku-band uplink dish",
    "antenna_diameter_m": 2.4,
    "antenna_efficiency": 0.62,
    "antenna_gain_dbi": None,  # Use this instead of diameter if you have a datasheet gain.
    "tx_power_w": 20.0,
    "tx_feeder_loss_db": 1.0,
    "notes": "Rome broadcasting earth station.",
}


# ========================================================================
# 2.                 GROUND STATION 2 (Downlink Receiver)
# ========================================================================
GS2 = {
    "site_name": "GS2 Ankara",
    "latitude_deg": 39.9334,
    "longitude_deg": 32.8597,
    "altitude_km": 0.94,
    "terminal_name": "GS2 receiver",
    "antenna_name": "GS2 Ku-band receive dish",
    "antenna_diameter_m": 0.9,
    "antenna_efficiency": 0.62,
    "antenna_gain_dbi": None,  # Use this instead of diameter if you have a datasheet gain.
    "system_noise_temperature_k": 150.0,
    "rx_feeder_loss_db": 0.5,
    "notes": "Ankara receive terminal.",
}


# ========================================================================
# 3.                 Satellite State and Transponder
# ========================================================================
SATELLITE = {
    "name": "Eutelsat Hotbird 13G at 13E",
    "longitude_deg": 13.0,
    "latitude_deg": 0.0,
    "orbit_radius_km": None,
}

SATELLITE_UPLINK_RECEIVER = {
    "terminal_name": "Satellite receiver",
    "g_over_t_db_per_k_override": 3.0,
    "notes": "Example satellite receive G/T; replace with selected satellite data.",
}

SATELLITE_DOWNLINK_TRANSMITTER = {
    "terminal_name": "Satellite transmitter",
    "eirp_dbw_override": 46.0,
    "notes": "Example downlink EIRP; replace with selected satellite footprint value.",
}

# ========================================================================
# 4.                        LINK Definitions
# ========================================================================
UPLINK = {
    "name": "Uplink: GS1 to GEO satellite",
    "frequency_ghz": 14.0,
    "bandwidth_mhz": 36.0,
    "bit_rate_mbps": 10.0,
    "required_ebn0_db": 7.0,
}

DOWNLINK = {
    "name": "Downlink: GEO satellite to GS2",
    "frequency_ghz": 12.0,
    "bandwidth_mhz": 36.0,
    "bit_rate_mbps": 10.0,
    "required_ebn0_db": 7.0,
}

UPLINK_LOSSES = {
    "pointing_loss_db": 0.5,
    "polarization_loss_db": 0.3,
    "atmospheric_loss_db": 0.5,
    "implementation_loss_db": 1.0,
    "misc_loss_db": 0.2,
}

DOWNLINK_LOSSES = {
    "pointing_loss_db": 0.5,
    "polarization_loss_db": 0.3,
    "atmospheric_loss_db": 0.5,
    "implementation_loss_db": 1.0,
    "misc_loss_db": 0.2,
}

# ========================================================================
# 5.                    Optional Advanced Models
# ========================================================================
APPARENT_MOTION = {
    "enabled": True,
    "duration_hours": 48.0,
    "step_minutes": 10.0,
    "east_west_amplitude_deg": 0.06,
    "north_south_amplitude_deg": 0.04,
    "radial_amplitude_km": 40.0,
}

INTERFERENCE = {
    "enabled": True,
    "adjacent_satellite_longitudes_deg": (11.0, 15.0),
    "adjacent_activity_factor_db": -3.0,
    "imd_c_i_db": 30.0,
}

DYNAMIC_NOISE = {
    "enabled": True,
    "receiver_internal_noise_k": 90.0,
    "spillover_noise_k": 20.0,
    "clear_sky_base_noise_k": 12.0,
    "low_elevation_extra_noise_k": 35.0,
    "rain_emission_temperature_k": 275.0,
}

RAIN_OUTAGE = {
    "enabled": True,
    "random_seed": 451,
    "samples_per_year": 8760,
    "light_rain_probability": 0.020,
    "moderate_rain_probability": 0.006,
    "heavy_rain_probability": 0.001,
}

DIGITAL = {
    "enabled": True,
    "modulation": "QPSK",
    "code_rate": 0.75,
    "coding_gain_db": 3.0,
    "rolloff_factor": 0.35,
    "target_ber": 1.0e-6,
    "uncoded_required_ebn0_db": 7.0,
}

# ========================================================================
# 6.            ITU-R PROPAGATION (V5 standards-based fade model)
# ========================================================================
# This block enables the real ITU-R P.618/P.676/P.840 slant-path attenuation
# suite. The base assignment runs the static MATLAB analyzer with P.618 losses
# OFF; this layer is the deliberate professional extension that lets the link
# be sized for a true availability target. Replace the example atmosphere with
# values for your own site (ITU-R P.837 rain map, local pressure/humidity).
ITU_PROPAGATION = {
    "enabled": True,
    "rain_rate_001_mm_per_h": 42.0,   # R_0.01 from ITU-R P.837 for the site.
    "polarization_tilt_deg": 45.0,    # 45 deg = circular polarization.
    "rain_height_h0_override_km": None,  # Set to the mapped 0 deg C isotherm if known.
    "surface_pressure_hpa": 1013.25,
    "surface_temperature_c": 15.0,
    "water_vapour_density_g_m3": 7.5,
    "relative_humidity_percent": 60.0,
    "columnar_liquid_water_kg_m2": 0.6,
    "include_gaseous": True,
    "include_cloud": True,
    "include_scintillation": True,
    "design_availability_percent": 99.9,  # Exceedance p = 0.1% of the year.
}

# ========================================================================
# 7.                  DVB-S2 ADAPTIVE CODING & MODULATION 
# ========================================================================
MODCOD = {
    "enabled": True,
    "rolloff_factor": 0.20,
    "implementation_margin_db": 1.0,
}
