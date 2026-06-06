"""Projenin ana girdi dosyası (Konfigürasyonlar).

Yer istasyonu koordinatları, uydu parametreleri, frekans değerleri ve 
çalıştırılacak opsiyonel analizler (ITU-R, Monte-Carlo, Girişim vb.) buradan ayarlanır.
Kod her çalıştığında güncel parametreleri bu dosyadan okur.
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
    "antenna_gain_dbi": 49.20,  # Prodelin Series 1244 Tx Gain at 14 GHz
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
    "antenna_gain_dbi": 39.02,  # Triax TD88 Rx Gain at 12 GHz (38.8 dBi @ 11.7 GHz extrapolated)
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
    "notes": "Assumed satellite receive G/T; public HOTBIRD 13G uplink G/T data for the selected transponder was not available.",
}

SATELLITE_DOWNLINK_TRANSMITTER = {
    "terminal_name": "Satellite transmitter",
    "eirp_dbw_override": 46.0,
    "notes": "Estimated downlink EIRP from the published HOTBIRD footprint contour at the Ankara receiving site.",
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
    "implementation_loss_db": 0.0,
    "misc_loss_db": 0.2,
}

DOWNLINK_LOSSES = {
    "pointing_loss_db": 0.5,
    "polarization_loss_db": 0.3,
    "atmospheric_loss_db": 0.5,
    "implementation_loss_db": 0.0,
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
# Not: MATLAB'deki varsayılan ödev isterlerinde P.618 sönümlemeleri kapalı varsayılmaktadır.
# Bu blok, projeye gerçekçilik katan opsiyonel ITU-R P.618/P.837/P.838/P.676/P.840
# atmosferik sönümleme (attenuation) modellerini konfigüre eder. İstasyonunuzun 
# değerleriyle (örneğin P.837 yağış oranı) değiştirebilirsiniz.
ITU_PROPAGATION = {
    "enabled": True,
    "rain_rate_001_mm_per_h": 42.0,   # R_0.01 from ITU-R P.837 for the site.
    "polarization_tilt_deg": 90.0,    # Linear vertical polarization assumption for ITU-R P.838 rain attenuation.
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
