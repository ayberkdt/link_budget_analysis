# calculations.py
"""RF hat bütçesi ve geometri hesaplamaları.

Serbest uzay yol kaybı (FSPL), anten kazancı, gürültü sıcaklıkları ve C/N oranlarını hesaplar.
Ayrıca statik hat bütçesi haricindeki opsiyonel modüller (ITU-R, Monte-Carlo, Girişim vb.)
için gereken fiziksel ve istatistiksel simülasyon algoritmalarını barındırır.
"""

# ========================================================================
# 0.                             IMPORTS
# ========================================================================
from __future__ import annotations

from dataclasses import replace
from math import asin, atan2, cos, degrees, erfc, log10, radians, sin, sqrt
from typing import Iterable, Optional, Sequence

import numpy as np

try:
    from .constants import (
        ATMOSPHERIC_EFFECTIVE_TEMPERATURE_K,
        BOLTZMANN_DB_CONSTANT,
        COSMIC_BACKGROUND_TEMPERATURE_K,
        EARTH_EQUATORIAL_RADIUS_KM,
        FSPL_CONSTANT,
        GEO_ORBIT_RADIUS_KM,
        GHZ,
        PARABOLIC_BEAMWIDTH_FACTOR,
        SIDELOBE_ENVELOPE_CONSTANT_A,
        SIDELOBE_ENVELOPE_CONSTANT_B,
        SPEED_OF_LIGHT_M_PER_S,
    )
    from .entities import (
        DigitalLinkConfig,
        DigitalMetrics,
        DishAntenna,
        DynamicNoiseConfig,
        GeoApparentMotion,
        GeoSatellite,
        InterferenceResult,
        ITUPropagationConfig,
        ITUPropagationResult,
        LinkBudgetResult,
        LinkConfig,
        LinkEndpoint,
        LinkEnvironment,
        LinkGeometry,
        Location,
        ModcodConfig,
        RainOutageConfig,
        ScenarioConfig,
        ScenarioResult,
        TimeVaryingSample,
    )
    from . import itu_propagation as itu
    from .modcod import ModcodSelection, esn0_from_cn0_db, select_best_modcod
except ImportError:  # Support direct execution with ``python src/main.py``.
    from constants import (
        ATMOSPHERIC_EFFECTIVE_TEMPERATURE_K,
        BOLTZMANN_DB_CONSTANT,
        COSMIC_BACKGROUND_TEMPERATURE_K,
        EARTH_EQUATORIAL_RADIUS_KM,
        FSPL_CONSTANT,
        GEO_ORBIT_RADIUS_KM,
        GHZ,
        PARABOLIC_BEAMWIDTH_FACTOR,
        SIDELOBE_ENVELOPE_CONSTANT_A,
        SIDELOBE_ENVELOPE_CONSTANT_B,
        SPEED_OF_LIGHT_M_PER_S,
    )
    from entities import (
        DigitalLinkConfig,
        DigitalMetrics,
        DishAntenna,
        DynamicNoiseConfig,
        GeoApparentMotion,
        GeoSatellite,
        InterferenceResult,
        ITUPropagationConfig,
        ITUPropagationResult,
        LinkBudgetResult,
        LinkConfig,
        LinkEndpoint,
        LinkEnvironment,
        LinkGeometry,
        Location,
        ModcodConfig,
        RainOutageConfig,
        ScenarioConfig,
        ScenarioResult,
        TimeVaryingSample,
    )
    import itu_propagation as itu
    from modcod import ModcodSelection, esn0_from_cn0_db, select_best_modcod


# ========================================================================
# 1.                       db Conversion HELPERS 
# ========================================================================
def linear_to_db(value: float) -> float:
    """Convert a positive linear value to dB."""

    if value <= 0.0:
        raise ValueError("linear_to_db expects a positive value.")
    return 10.0 * log10(value)


def db_to_linear(value_db: float) -> float:
    """Convert dB to a linear power ratio."""

    return 10.0 ** (value_db / 10.0)


def watts_to_dbw(power_w: float) -> float:
    """Convert power in watts to dBW."""

    if power_w <= 0.0:
        raise ValueError("watts_to_dbw expects a positive power.")
    return 10.0 * log10(power_w)


def dbw_to_watts(power_dbw: float) -> float:
    """Convert power in dBW to watts."""

    return 10.0 ** (power_dbw / 10.0)



# ========================================================================
# 2.                      Antenna and RF Equations
# ========================================================================
def wavelength_m(frequency_hz: float) -> float:
    """Return wavelength in meters for a given frequency in hertz."""

    if frequency_hz <= 0.0:
        raise ValueError("Frequency must be positive.")
    return SPEED_OF_LIGHT_M_PER_S / frequency_hz


def dish_gain_dbi(diameter_m: float, frequency_hz: float, efficiency: float = 0.62) -> float:
    """Compute parabolic dish gain in dBi.

    Formula
    -------
    G = eta * (pi*D/lambda)^2
    G_dBi = 10*log10(G)
    """

    if diameter_m <= 0.0:
        raise ValueError("Dish diameter must be positive.")
    if not (0.0 < efficiency <= 1.0):
        raise ValueError("Dish efficiency must be between 0 and 1.")

    lam = wavelength_m(frequency_hz)
    gain_linear = efficiency * (np.pi * diameter_m / lam) ** 2
    return float(10.0 * np.log10(gain_linear))


def half_power_beamwidth_deg(diameter_m: float, frequency_hz: float) -> float:
    """Return an approximate parabolic-dish half-power beamwidth in degrees."""

    lam = wavelength_m(frequency_hz)
    return PARABOLIC_BEAMWIDTH_FACTOR * lam / diameter_m


def off_axis_gain_dbi(
    antenna: DishAntenna,
    frequency_hz: float,
    off_axis_angle_deg: float,
    minimum_angle_deg: float = 0.05,
) -> float:
    """Estimate off-axis gain for adjacent-satellite interference studies.

    The function combines a smooth main-lobe approximation near boresight with a
    conservative side-lobe envelope for larger angles. It is appropriate for a
    teaching-level ASI sensitivity study, not for regulatory coordination.
    """

    main_gain = resolve_antenna_gain_dbi(antenna, frequency_hz)
    if main_gain is None:
        raise ValueError("An antenna gain or diameter is required for off-axis gain.")
    if antenna.diameter_m is None:
        # A datasheet gain may not include diameter. In that case, use a generic
        # side-lobe envelope after a small boresight protection angle.
        theta = max(abs(off_axis_angle_deg), minimum_angle_deg)
        if theta <= 0.25:
            return main_gain - 12.0 * (theta / 0.25) ** 2
        return min(main_gain - 3.0, SIDELOBE_ENVELOPE_CONSTANT_A - SIDELOBE_ENVELOPE_CONSTANT_B * log10(theta))

    theta = max(abs(off_axis_angle_deg), minimum_angle_deg)
    hpbw = half_power_beamwidth_deg(antenna.diameter_m, frequency_hz)

    # Smooth main lobe: about 3 dB down at half the HPBW.
    if theta <= max(hpbw, minimum_angle_deg):
        return main_gain - 12.0 * (theta / max(hpbw, minimum_angle_deg)) ** 2

    # Educational side-lobe envelope. The value is intentionally not presented as
    # an official mask. It gives realistic discrimination trends for contour work.
    side_lobe_gain = SIDELOBE_ENVELOPE_CONSTANT_A - SIDELOBE_ENVELOPE_CONSTANT_B * log10(theta)
    return min(main_gain - 3.0, side_lobe_gain)


def resolve_antenna_gain_dbi(antenna: Optional[DishAntenna], frequency_hz: float) -> Optional[float]:
    """Return antenna gain in dBi from either datasheet gain or dish diameter."""

    if antenna is None:
        return None
    if antenna.gain_dbi is not None:
        return antenna.gain_dbi
    if antenna.diameter_m is None:
        return None
    return dish_gain_dbi(antenna.diameter_m, frequency_hz, antenna.efficiency)


def resolve_eirp_dbw(endpoint: LinkEndpoint, frequency_hz: float) -> tuple[float, Optional[float]]:
    """Resolve endpoint EIRP in dBW and return ``(eirp_dbw, tx_gain_dbi)``."""

    if endpoint.eirp_dbw_override is not None:
        tx_gain = resolve_antenna_gain_dbi(endpoint.antenna, frequency_hz)
        return endpoint.eirp_dbw_override, tx_gain

    if endpoint.tx_power_dbw is None:
        raise ValueError(f"{endpoint.name} needs tx_power_dbw or eirp_dbw_override.")

    tx_gain = resolve_antenna_gain_dbi(endpoint.antenna, frequency_hz)
    if tx_gain is None:
        raise ValueError(f"{endpoint.name} needs an antenna gain or diameter for EIRP calculation.")

    eirp = endpoint.tx_power_dbw + tx_gain - endpoint.tx_feeder_loss_db
    return eirp, tx_gain


def resolve_g_over_t_db_per_k(
    endpoint: LinkEndpoint,
    frequency_hz: float,
    dynamic_tsys_k: Optional[float] = None,
) -> tuple[float, Optional[float], Optional[float]]:
    """Resolve receiver G/T and return ``(G/T, rx_gain_dbi, Tsys_K)``."""

    rx_gain = resolve_antenna_gain_dbi(endpoint.antenna, frequency_hz)

    if dynamic_tsys_k is not None:
        if rx_gain is None:
            raise ValueError(f"{endpoint.name} needs antenna gain for dynamic Tsys G/T.")
        if dynamic_tsys_k <= 0.0:
            raise ValueError("Dynamic system noise temperature must be positive.")
        g_over_t = rx_gain - endpoint.rx_feeder_loss_db - 10.0 * log10(dynamic_tsys_k)
        return g_over_t, rx_gain, dynamic_tsys_k

    if endpoint.g_over_t_db_per_k_override is not None:
        return endpoint.g_over_t_db_per_k_override, rx_gain, endpoint.system_noise_temperature_k

    if endpoint.system_noise_temperature_k is None:
        raise ValueError(f"{endpoint.name} needs system_noise_temperature_k or G/T override.")
    if rx_gain is None:
        raise ValueError(f"{endpoint.name} needs an antenna gain or diameter for G/T calculation.")
    if endpoint.system_noise_temperature_k <= 0.0:
        raise ValueError("System noise temperature must be positive.")

    g_over_t = rx_gain - endpoint.rx_feeder_loss_db - 10.0 * log10(endpoint.system_noise_temperature_k)
    return g_over_t, rx_gain, endpoint.system_noise_temperature_k


def free_space_path_loss_db(frequency_hz: float, range_km: float) -> float:
    """Compute free-space path loss in dB.

    FSPL[dB] = FSPL_CONSTANT + 20log10(f_GHz) + 20log10(R_km)
    """

    if frequency_hz <= 0.0:
        raise ValueError("Frequency must be positive.")
    if range_km <= 0.0:
        raise ValueError("Range must be positive.")

    frequency_ghz = frequency_hz / GHZ
    return FSPL_CONSTANT + 20.0 * log10(frequency_ghz) + 20.0 * log10(range_km)



# ========================================================================
# 3.                             GEOMETRY 
# ========================================================================
def _ecef_from_spherical(radius_km: float, latitude_deg: float, longitude_deg: float) -> np.ndarray:
    """Return an ECEF vector from spherical Earth coordinates."""

    lat = radians(latitude_deg)
    lon = radians(longitude_deg)
    return np.array(
        [
            radius_km * cos(lat) * cos(lon),
            radius_km * cos(lat) * sin(lon),
            radius_km * sin(lat),
        ],
        dtype=float,
    )


def _look_unit_vector(location: Location, satellite: GeoSatellite) -> np.ndarray:
    """Return the topocentric line-of-sight unit vector in ECEF coordinates."""

    earth_radius = EARTH_EQUATORIAL_RADIUS_KM + location.altitude_km
    satellite_radius = satellite.orbit_radius_km or GEO_ORBIT_RADIUS_KM
    r_ground = _ecef_from_spherical(earth_radius, location.latitude_deg, location.longitude_deg)
    r_sat = _ecef_from_spherical(satellite_radius, satellite.latitude_deg, satellite.longitude_deg)
    rho = r_sat - r_ground
    return rho / np.linalg.norm(rho)


def angular_separation_deg(location: Location, sat_a: GeoSatellite, sat_b: GeoSatellite) -> float:
    """Return apparent angular separation between two satellites as seen by a site."""

    u_a = _look_unit_vector(location, sat_a)
    u_b = _look_unit_vector(location, sat_b)
    return degrees(float(np.arccos(np.clip(np.dot(u_a, u_b), -1.0, 1.0))))


def calculate_geo_link_geometry(location: Location, satellite: GeoSatellite) -> LinkGeometry:
    """Calculate pointing geometry from a ground site to a GEO satellite."""

    earth_radius = EARTH_EQUATORIAL_RADIUS_KM + location.altitude_km
    satellite_radius = satellite.orbit_radius_km or GEO_ORBIT_RADIUS_KM

    r_ground = _ecef_from_spherical(earth_radius, location.latitude_deg, location.longitude_deg)
    r_sat = _ecef_from_spherical(satellite_radius, satellite.latitude_deg, satellite.longitude_deg)
    rho = r_sat - r_ground
    slant_range_km = float(np.linalg.norm(rho))
    rho_hat = rho / slant_range_km

    lat = radians(location.latitude_deg)
    lon = radians(location.longitude_deg)
    local_up = np.array([cos(lat) * cos(lon), cos(lat) * sin(lon), sin(lat)])
    local_east = np.array([-sin(lon), cos(lon), 0.0])
    local_north = np.array([-sin(lat) * cos(lon), -sin(lat) * sin(lon), cos(lat)])

    elevation_deg = degrees(asin(float(np.clip(np.dot(rho_hat, local_up), -1.0, 1.0))))
    east_component = float(np.dot(rho_hat, local_east))
    north_component = float(np.dot(rho_hat, local_north))
    azimuth_deg = (degrees(atan2(east_component, north_component)) + 360.0) % 360.0

    ground_hat = r_ground / np.linalg.norm(r_ground)
    sat_hat = r_sat / np.linalg.norm(r_sat)
    central_angle_deg = degrees(float(np.arccos(np.clip(np.dot(ground_hat, sat_hat), -1.0, 1.0))))

    return LinkGeometry(
        ground_station_name=location.name,
        satellite_name=satellite.name,
        slant_range_km=slant_range_km,
        elevation_deg=elevation_deg,
        azimuth_deg=azimuth_deg,
        central_angle_deg=central_angle_deg,
        satellite_longitude_deg=satellite.longitude_deg,
        satellite_latitude_deg=satellite.latitude_deg,
        satellite_radius_km=satellite_radius,
    )



# ========================================================================
# 4.                   Dynamic NOISE and RAIN Models
# ========================================================================
def calculate_rain_emission_noise_temperature_k(
    rain_attenuation_db: float,
    emission_temperature_k: float = ATMOSPHERIC_EFFECTIVE_TEMPERATURE_K,
) -> float:
    """Estimate the equivalent noise temperature contributed by rain.

    A lossy atmospheric layer also emits thermal noise. The simplified radiative
    transfer expression is: T_rain = T_medium * (1 - 10^(-A/10)).
    """

    attenuation_linear = db_to_linear(max(rain_attenuation_db, 0.0))
    transmissivity = 1.0 / attenuation_linear
    return emission_temperature_k * (1.0 - transmissivity)


def calculate_dynamic_system_noise_temperature_k(
    elevation_deg: float,
    rain_attenuation_db: float,
    config: DynamicNoiseConfig,
) -> float:
    """Calculate receive system temperature for a given elevation and rain loss."""

    effective_el = max(elevation_deg, config.minimum_elevation_deg)
    sin_el = max(sin(radians(effective_el)), 0.03)

    # Low-elevation atmosphere term. It rises as elevation decreases but is
    # bounded enough to remain a teaching model rather than a propagation code.
    clear_sky = (
        COSMIC_BACKGROUND_TEMPERATURE_K
        + config.clear_sky_base_noise_k
        + config.low_elevation_extra_noise_k * (1.0 / sin_el - 1.0) / 8.0
    )
    clear_sky = min(clear_sky, 120.0)

    rain_noise = calculate_rain_emission_noise_temperature_k(
        rain_attenuation_db,
        emission_temperature_k=config.rain_emission_temperature_k,
    )

    return (
        config.receiver_internal_noise_k
        + config.spillover_noise_k
        + clear_sky
        + rain_noise
    )


def _sample_rain_attenuation_base_db(rng: np.random.Generator, config: RainOutageConfig) -> tuple[str, float]:
    """Sample a base downlink rain attenuation and weather label."""

    u = float(rng.random())
    heavy_p = config.heavy_rain_probability
    moderate_p = heavy_p + config.moderate_rain_probability
    light_p = moderate_p + config.light_rain_probability

    if u < heavy_p:
        lo, hi = config.heavy_rain_attenuation_range_db
        return "heavy rain", float(rng.uniform(lo, hi))
    if u < moderate_p:
        lo, hi = config.moderate_rain_attenuation_range_db
        return "moderate rain", float(rng.uniform(lo, hi))
    if u < light_p:
        lo, hi = config.light_rain_attenuation_range_db
        return "light rain", float(rng.uniform(lo, hi))
    return "clear", float(rng.uniform(0.0, config.clear_attenuation_max_db))


def scale_rain_attenuation_for_frequency(
    base_attenuation_db: float,
    frequency_hz: float,
    reference_frequency_hz: float = 12.0e9,
    exponent: float = 1.0,
) -> float:
    """Scale a sampled attenuation roughly with frequency for Ku-band sensitivity."""

    ratio = max(frequency_hz / reference_frequency_hz, 0.1)
    return base_attenuation_db * ratio**exponent


# ========================================================================
# 5.                            LINK BUDGET
# ========================================================================
def calculate_link_budget(
    link: LinkConfig,
    geometry: LinkGeometry,
    environment: Optional[LinkEnvironment] = None,
) -> LinkBudgetResult:
    """Calculate one one-way link budget for the supplied geometry and environment."""

    environment = environment or LinkEnvironment()
    eirp_dbw, tx_gain_dbi = resolve_eirp_dbw(link.transmitter, link.frequency_hz)
    g_over_t, rx_gain_dbi, effective_tsys_k = resolve_g_over_t_db_per_k(
        link.receiver,
        link.frequency_hz,
        dynamic_tsys_k=environment.dynamic_tsys_k,
    )
    fspl = free_space_path_loss_db(link.frequency_hz, geometry.slant_range_km)
    fixed_losses = link.losses.total_loss_db
    rain_loss = max(environment.rain_attenuation_db, 0.0)
    total_losses = fspl + fixed_losses + rain_loss

    cn0 = eirp_dbw + g_over_t - total_losses + BOLTZMANN_DB_CONSTANT
    cn = cn0 - 10.0 * log10(link.bandwidth_hz)
    ebn0 = cn0 - 10.0 * log10(link.bit_rate_bps)
    margin = ebn0 - link.required_ebn0_db

    carrier_power_dbw: Optional[float]
    if rx_gain_dbi is not None:
        carrier_power_dbw = eirp_dbw - total_losses + rx_gain_dbi - link.receiver.rx_feeder_loss_db
    else:
        carrier_power_dbw = None

    return LinkBudgetResult(
        link_name=link.name,
        frequency_hz=link.frequency_hz,
        bandwidth_hz=link.bandwidth_hz,
        bit_rate_bps=link.bit_rate_bps,
        range_km=geometry.slant_range_km,
        elevation_deg=geometry.elevation_deg,
        tx_gain_dbi=tx_gain_dbi,
        rx_gain_dbi=rx_gain_dbi,
        eirp_dbw=eirp_dbw,
        g_over_t_db_per_k=g_over_t,
        system_noise_temperature_k=effective_tsys_k,
        free_space_loss_db=fspl,
        fixed_losses_db=fixed_losses,
        rain_attenuation_db=rain_loss,
        total_losses_db=total_losses,
        cn0_dbhz=cn0,
        cn_db=cn,
        ebn0_db=ebn0,
        required_ebn0_db=link.required_ebn0_db,
        margin_db=margin,
        carrier_power_dbw=carrier_power_dbw,
    )


def combine_inverse_db(values_db: Iterable[Optional[float]]) -> float:
    """Combine C/N or C/I terms by inverse-linear addition.

    1/X_total = sum(1/X_i)
    """

    inverse_sum = 0.0
    used = 0
    for value_db in values_db:
        if value_db is None:
            continue
        inverse_sum += 1.0 / db_to_linear(value_db)
        used += 1
    if used == 0 or inverse_sum <= 0.0:
        raise ValueError("At least one finite dB ratio is required.")
    return linear_to_db(1.0 / inverse_sum)


def cn_to_ebn0_db(cn_db: float, bandwidth_hz: float, bit_rate_bps: float) -> float:
    """Convert C/N over bandwidth to Eb/N0 using Eb/N0 = C/N + 10log(B/Rb)."""

    return cn_db + 10.0 * log10(bandwidth_hz / bit_rate_bps)



# ========================================================================
# 6.                   Digital-Layer BER, FEC, Shannon
# ========================================================================
def modulation_bits_per_symbol(modulation: str) -> int:
    """Return ideal bits per symbol for common PSK/QAM modulations.

    The BER model below is exact only for coherent BPSK and Gray-coded QPSK in
    AWGN. Other modulations can be added later with their own analytical or
    simulated BER curves.
    """

    name = modulation.strip().upper().replace("-", "").replace("_", "")
    if name in {"BPSK"}:
        return 1
    if name in {"QPSK", "OQPSK", "4QAM"}:
        return 2
    if name in {"8PSK"}:
        return 3
    if name in {"16QAM"}:
        return 4
    raise ValueError(f"Unsupported modulation '{modulation}'. Supported defaults: BPSK, QPSK, 8PSK, 16QAM.")


def theoretical_ber_awgn(ebn0_db: float, modulation: str = "QPSK") -> float:
    """Return an uncoded theoretical BER estimate from Eb/N0 in dB.

    BPSK and Gray-coded QPSK in AWGN have the same bit-error probability:

        Pb = 0.5 * erfc(sqrt(Eb/N0))

    The 8PSK and 16QAM branches are common high-SNR engineering approximations
    and are included only for sensitivity studies.
    """

    gamma_b = db_to_linear(ebn0_db)
    name = modulation.strip().upper().replace("-", "").replace("_", "")

    if name in {"BPSK", "QPSK", "OQPSK", "4QAM"}:
        pb = 0.5 * erfc(sqrt(gamma_b))
    elif name == "8PSK":
        # Approximate Gray-coded coherent M-PSK BER at moderate/high SNR.
        m = 8.0
        k = log10(m) / log10(2.0)
        pb = (1.0 / k) * erfc(sqrt(k * gamma_b) * sin(np.pi / m))
    elif name == "16QAM":
        # Approximate square M-QAM BER.
        m = 16.0
        k = log10(m) / log10(2.0)
        pb = (4.0 / k) * (1.0 - 1.0 / sqrt(m)) * 0.5 * erfc(sqrt(3.0 * k * gamma_b / (2.0 * (m - 1.0))))
    else:
        raise ValueError(f"Unsupported modulation '{modulation}'.")

    return float(min(max(pb, 0.0), 1.0))


def fec_adjusted_ber_awgn(ebn0_db: float, config: DigitalLinkConfig) -> float:
    """Approximate coded BER by shifting Eb/N0 by the coding gain.

    This is not a replacement for a real Viterbi/LDPC/Turbo/RS decoder curve. It
    is an explicit engineering approximation: FEC is represented as an
    equivalent coding gain in dB.
    """

    return theoretical_ber_awgn(ebn0_db + config.coding_gain_db, config.modulation)


def shannon_capacity_bps(bandwidth_hz: float, cn_db: float) -> float:
    """Return Shannon-Hartley capacity C = B log2(1 + SNR)."""

    if bandwidth_hz <= 0.0:
        raise ValueError("Bandwidth must be positive.")
    snr_linear = db_to_linear(cn_db)
    return float(bandwidth_hz * np.log2(1.0 + snr_linear))


def shannon_ebn0_limit_db(spectral_efficiency_bps_hz: float) -> float:
    """Return the Shannon minimum Eb/N0 for a given spectral efficiency.

    For spectral efficiency eta = R/B, the AWGN limit is:

        Eb/N0 >= (2^eta - 1) / eta
    """

    eta = spectral_efficiency_bps_hz
    if eta <= 0.0:
        raise ValueError("Spectral efficiency must be positive.")
    limit_linear = (2.0**eta - 1.0) / eta
    return linear_to_db(float(limit_linear))


def calculate_digital_metrics(
    scenario: ScenarioConfig,
    combined_ebn0_db: float,
    combined_ebn0_ni_db: float,
    combined_cn_db: float,
    combined_cni_db: float,
) -> Optional[DigitalMetrics]:
    """Calculate BER, FEC, bandwidth, and Shannon-capacity metrics."""

    cfg = scenario.digital
    if not cfg.enabled:
        return None
    if not (0.0 < cfg.code_rate <= 1.0):
        raise ValueError("Digital code_rate must be in the interval (0, 1].")
    if cfg.rolloff_factor < 0.0:
        raise ValueError("Rolloff factor must be non-negative.")

    info_rate = scenario.uplink.bit_rate_bps
    bandwidth = scenario.uplink.bandwidth_hz
    bits_per_symbol = modulation_bits_per_symbol(cfg.modulation)
    coded_channel_rate = info_rate / cfg.code_rate
    symbol_rate = coded_channel_rate / bits_per_symbol
    occupied_bw = symbol_rate * (1.0 + cfg.rolloff_factor)

    info_eta = info_rate / bandwidth
    coded_eta = coded_channel_rate / bandwidth
    shannon_limit = shannon_ebn0_limit_db(info_eta)

    capacity_noise = shannon_capacity_bps(bandwidth, combined_cn_db)
    capacity_ni = shannon_capacity_bps(bandwidth, combined_cni_db)

    coded_required = cfg.required_coded_ebn0_db

    return DigitalMetrics(
        modulation=cfg.modulation,
        bits_per_symbol=bits_per_symbol,
        code_rate=cfg.code_rate,
        coding_gain_db=cfg.coding_gain_db,
        rolloff_factor=cfg.rolloff_factor,
        target_ber=cfg.target_ber,
        information_bit_rate_bps=info_rate,
        coded_channel_bit_rate_bps=coded_channel_rate,
        symbol_rate_baud=symbol_rate,
        estimated_occupied_bandwidth_hz=occupied_bw,
        allocated_bandwidth_hz=bandwidth,
        information_spectral_efficiency_bps_hz=info_eta,
        coded_spectral_efficiency_bps_hz=coded_eta,
        uncoded_required_ebn0_db=cfg.uncoded_required_ebn0_db,
        coded_required_ebn0_db=coded_required,
        noise_only_ber_uncoded=theoretical_ber_awgn(combined_ebn0_db, cfg.modulation),
        interference_ber_uncoded=theoretical_ber_awgn(combined_ebn0_ni_db, cfg.modulation),
        noise_only_ber_with_coding_gain=fec_adjusted_ber_awgn(combined_ebn0_db, cfg),
        interference_ber_with_coding_gain=fec_adjusted_ber_awgn(combined_ebn0_ni_db, cfg),
        digital_margin_noise_only_db=combined_ebn0_db - coded_required,
        digital_margin_with_interference_db=combined_ebn0_ni_db - coded_required,
        shannon_capacity_noise_only_bps=capacity_noise,
        shannon_capacity_with_interference_bps=capacity_ni,
        shannon_capacity_margin_noise_only_bps=capacity_noise - info_rate,
        shannon_capacity_margin_with_interference_bps=capacity_ni - info_rate,
        shannon_ebn0_limit_db=shannon_limit,
        gap_to_shannon_noise_only_db=combined_ebn0_db - shannon_limit,
        gap_to_shannon_with_interference_db=combined_ebn0_ni_db - shannon_limit,
    )

def _dominant_interference_name(values: dict[str, Optional[float]]) -> str:
    """Return the label of the smallest finite C/I term."""

    finite = {key: value for key, value in values.items() if value is not None}
    if not finite:
        return "none"
    return min(finite, key=lambda key: finite[key] if finite[key] is not None else 1e9)


def _single_adjacent_ci_downlink_db(
    scenario: ScenarioConfig,
    adjacent_satellite: GeoSatellite,
    desired_satellite: GeoSatellite,
) -> Optional[float]:
    """Estimate downlink C/I from one adjacent satellite into GS2."""

    gs2 = scenario.downlink.receiver.location
    rx_ant = scenario.downlink.receiver.antenna
    if gs2 is None or rx_ant is None:
        return None

    theta = angular_separation_deg(gs2, desired_satellite, adjacent_satellite)
    g_main = resolve_antenna_gain_dbi(rx_ant, scenario.downlink.frequency_hz)
    if g_main is None:
        return None
    g_off = off_axis_gain_dbi(
        rx_ant,
        scenario.downlink.frequency_hz,
        theta,
        scenario.interference.minimum_off_axis_angle_deg,
    )

    desired_geom = calculate_geo_link_geometry(gs2, desired_satellite)
    adjacent_geom = calculate_geo_link_geometry(gs2, adjacent_satellite)
    desired_fspl = free_space_path_loss_db(scenario.downlink.frequency_hz, desired_geom.slant_range_km)
    adjacent_fspl = free_space_path_loss_db(scenario.downlink.frequency_hz, adjacent_geom.slant_range_km)

    # C/I = (EIRP_des + G_main - L_des) - (EIRP_adj + G_off - L_adj)
    return (
        -scenario.interference.adjacent_downlink_eirp_relative_db
        + scenario.interference.adjacent_activity_factor_db * -1.0
        + (g_main - g_off)
        + (adjacent_fspl - desired_fspl)
    )


def _single_adjacent_ci_uplink_db(
    scenario: ScenarioConfig,
    adjacent_satellite: GeoSatellite,
    desired_satellite: GeoSatellite,
) -> Optional[float]:
    """Estimate uplink C/I at the desired satellite from adjacent-system leakage.

    Without actual adjacent earth-station data, the model assumes an adjacent
    carrier of comparable EIRP and uses the GS1 transmit antenna discrimination
    at the apparent adjacent-satellite separation. This gives the correct trend:
    smaller spacing or smaller antenna discrimination reduces C/I.
    """

    gs1 = scenario.uplink.transmitter.location
    tx_ant = scenario.uplink.transmitter.antenna
    if gs1 is None or tx_ant is None:
        return None

    theta = angular_separation_deg(gs1, desired_satellite, adjacent_satellite)
    g_main = resolve_antenna_gain_dbi(tx_ant, scenario.uplink.frequency_hz)
    if g_main is None:
        return None
    g_off = off_axis_gain_dbi(
        tx_ant,
        scenario.uplink.frequency_hz,
        theta,
        scenario.interference.minimum_off_axis_angle_deg,
    )

    # If the adjacent carrier is active only part of the time or with lower power,
    # the interference term is reduced. A negative activity factor improves C/I.
    return (
        (g_main - g_off)
        - scenario.interference.adjacent_uplink_eirp_relative_db
        - scenario.interference.adjacent_activity_factor_db
    )


def calculate_interference(
    scenario: ScenarioConfig,
    desired_satellite: GeoSatellite,
) -> InterferenceResult:
    """Calculate adjacent-satellite and IMD interference terms."""

    cfg = scenario.interference
    if not cfg.enabled:
        return InterferenceResult(None, None, None, "none")

    if cfg.uplink_c_i_override_db is not None:
        uplink_ci = cfg.uplink_c_i_override_db
    else:
        uplink_terms = []
        for lon in cfg.adjacent_satellite_longitudes_deg:
            adj = replace(desired_satellite, name=f"Adjacent GEO {lon:.1f}E", longitude_deg=lon)
            val = _single_adjacent_ci_uplink_db(scenario, adj, desired_satellite)
            if val is not None:
                uplink_terms.append(val)
        uplink_ci = combine_inverse_db(uplink_terms) if uplink_terms else None

    if cfg.downlink_c_i_override_db is not None:
        downlink_ci = cfg.downlink_c_i_override_db
    else:
        downlink_terms = []
        for lon in cfg.adjacent_satellite_longitudes_deg:
            adj = replace(desired_satellite, name=f"Adjacent GEO {lon:.1f}E", longitude_deg=lon)
            val = _single_adjacent_ci_downlink_db(scenario, adj, desired_satellite)
            if val is not None:
                downlink_terms.append(val)
        downlink_ci = combine_inverse_db(downlink_terms) if downlink_terms else None

    dominant = _dominant_interference_name(
        {
            "uplink ASI": uplink_ci,
            "downlink ASI": downlink_ci,
            "IMD": cfg.imd_c_i_db,
        }
    )
    return InterferenceResult(uplink_ci, downlink_ci, cfg.imd_c_i_db, dominant)


def calculate_scenario(
    scenario: ScenarioConfig,
    satellite_override: Optional[GeoSatellite] = None,
    uplink_environment: Optional[LinkEnvironment] = None,
    downlink_environment: Optional[LinkEnvironment] = None,
    use_dynamic_downlink_tsys: bool = False,
) -> ScenarioResult:
    """Calculate the full bent-pipe scenario from uplink to final combined result."""

    satellite = satellite_override or scenario.satellite

    if scenario.uplink.transmitter.location is None:
        raise ValueError("The uplink transmitter must have a ground-station location.")
    if scenario.downlink.receiver.location is None:
        raise ValueError("The downlink receiver must have a ground-station location.")
    if not np.isclose(scenario.uplink.bit_rate_bps, scenario.downlink.bit_rate_bps):
        raise ValueError("Bent-pipe uplink and downlink bit rates must match.")
    if not np.isclose(scenario.uplink.bandwidth_hz, scenario.downlink.bandwidth_hz):
        raise ValueError("Bent-pipe uplink and downlink bandwidths must match.")

    uplink_geometry = calculate_geo_link_geometry(scenario.uplink.transmitter.location, satellite)
    downlink_geometry = calculate_geo_link_geometry(scenario.downlink.receiver.location, satellite)

    uplink_environment = uplink_environment or LinkEnvironment()
    downlink_environment = downlink_environment or LinkEnvironment()

    if use_dynamic_downlink_tsys and scenario.dynamic_noise.enabled:
        tsys = calculate_dynamic_system_noise_temperature_k(
            elevation_deg=downlink_geometry.elevation_deg,
            rain_attenuation_db=downlink_environment.noise_emission_attenuation_db,
            config=scenario.dynamic_noise,
        )
        downlink_environment = replace(downlink_environment, dynamic_tsys_k=tsys)

    uplink = calculate_link_budget(scenario.uplink, uplink_geometry, uplink_environment)
    downlink = calculate_link_budget(scenario.downlink, downlink_geometry, downlink_environment)

    combined_cn0 = combine_inverse_db([uplink.cn0_dbhz, downlink.cn0_dbhz])
    combined_cn = combine_inverse_db([uplink.cn_db, downlink.cn_db])
    combined_ebn0 = combined_cn0 - 10.0 * log10(scenario.downlink.bit_rate_bps)
    combined_margin = combined_ebn0 - scenario.required_end_to_end_ebn0_db

    interference = calculate_interference(scenario, satellite)
    combined_cni = combine_inverse_db(
        [
            uplink.cn_db,
            downlink.cn_db,
            interference.uplink_asi_c_i_db,
            interference.downlink_asi_c_i_db,
            interference.imd_c_i_db,
        ]
    )
    combined_ebn0_ni = cn_to_ebn0_db(
        combined_cni,
        scenario.downlink.bandwidth_hz,
        scenario.downlink.bit_rate_bps,
    )
    combined_margin_ni = combined_ebn0_ni - scenario.required_end_to_end_ebn0_db

    digital_metrics = calculate_digital_metrics(
        scenario,
        combined_ebn0_db=combined_ebn0,
        combined_ebn0_ni_db=combined_ebn0_ni,
        combined_cn_db=combined_cn,
        combined_cni_db=combined_cni,
    )

    return ScenarioResult(
        scenario_name=scenario.name,
        uplink_geometry=uplink_geometry,
        downlink_geometry=downlink_geometry,
        uplink=uplink,
        downlink=downlink,
        combined_cn0_dbhz=combined_cn0,
        combined_cn_db=combined_cn,
        combined_ebn0_db=combined_ebn0,
        combined_margin_db=combined_margin,
        interference=interference,
        combined_cni_db=combined_cni,
        combined_ebn0_ni_db=combined_ebn0_ni,
        combined_margin_ni_db=combined_margin_ni,
        digital=digital_metrics,
    )



# ========================================================================
# 7.                             AVAILABILITY
# ========================================================================
def get_apparent_geo_state(satellite: GeoSatellite, motion: GeoApparentMotion, time_hours: float) -> GeoSatellite:
    """Return the apparent GEO state at a given time sample."""

    if not motion.enabled:
        return satellite

    omega = 2.0 * np.pi / motion.period_hours
    ew_phase = radians(motion.east_west_phase_deg)
    ns_phase = radians(motion.north_south_phase_deg)
    radial_phase = radians(motion.radial_phase_deg)

    longitude = satellite.longitude_deg + motion.east_west_amplitude_deg * sin(omega * time_hours + ew_phase)
    latitude = satellite.latitude_deg + motion.north_south_amplitude_deg * sin(omega * time_hours + ns_phase)
    radius = (satellite.orbit_radius_km or GEO_ORBIT_RADIUS_KM) + motion.radial_amplitude_km * sin(
        omega * time_hours + radial_phase
    )

    return GeoSatellite(
        name=satellite.name,
        longitude_deg=longitude,
        latitude_deg=latitude,
        orbit_radius_km=radius,
    )


def simulate_time_varying_scenario(scenario: ScenarioConfig) -> list[TimeVaryingSample]:
    """Run the deterministic clear-sky GEO motion simulation."""

    motion = scenario.apparent_motion
    times = np.arange(0.0, motion.duration_hours + 0.5 * motion.step_minutes / 60.0, motion.step_minutes / 60.0)

    samples: list[TimeVaryingSample] = []
    for t in times:
        sat_t = get_apparent_geo_state(scenario.satellite, motion, float(t))
        result = calculate_scenario(scenario, satellite_override=sat_t, use_dynamic_downlink_tsys=True)
        samples.append(TimeVaryingSample(time_hours=float(t), satellite=sat_t, result=result))
    return samples


def simulate_monte_carlo_rain_outage(scenario: ScenarioConfig) -> list[TimeVaryingSample]:
    """Run the educational stochastic Monte-Carlo one-year rain-outage simulation.

    This is a teaching weather generator, not a propagation standard. For the
    deterministic standards-based fade analysis use the ITU-R pipeline
    (:func:`calculate_scenario_with_itu`) instead.
    """

    cfg = scenario.rain_outage
    rng = np.random.default_rng(cfg.random_seed)
    samples: list[TimeVaryingSample] = []

    sample_interval_hours = 8760.0 / cfg.samples_per_year
    for i in range(cfg.samples_per_year):
        time_hours = float(i) * sample_interval_hours
        downlink_label, base_downlink_attenuation = _sample_rain_attenuation_base_db(rng, cfg)
        if cfg.correlate_uplink_downlink_weather:
            uplink_label = downlink_label
            base_uplink_attenuation = base_downlink_attenuation
        else:
            uplink_label, base_uplink_attenuation = _sample_rain_attenuation_base_db(rng, cfg)

        downlink_rain = scale_rain_attenuation_for_frequency(
            base_downlink_attenuation,
            scenario.downlink.frequency_hz,
            reference_frequency_hz=12.0e9,
            exponent=cfg.downlink_frequency_scaling_exponent,
        )
        uplink_rain = scale_rain_attenuation_for_frequency(
            base_uplink_attenuation,
            scenario.uplink.frequency_hz,
            reference_frequency_hz=12.0e9,
            exponent=cfg.uplink_frequency_scaling_exponent,
        )
        weather_label = (
            downlink_label
            if cfg.correlate_uplink_downlink_weather
            else f"uplink: {uplink_label}; downlink: {downlink_label}"
        )

        # Add station-keeping motion only when that module is enabled.
        sat_t = (
            get_apparent_geo_state(scenario.satellite, scenario.apparent_motion, time_hours)
            if scenario.apparent_motion.enabled
            else scenario.satellite
        )
        result = calculate_scenario(
            scenario,
            satellite_override=sat_t,
            uplink_environment=LinkEnvironment(rain_attenuation_db=uplink_rain, weather_label=uplink_label),
            downlink_environment=LinkEnvironment(rain_attenuation_db=downlink_rain, weather_label=downlink_label),
            use_dynamic_downlink_tsys=True,
        )
        samples.append(
            TimeVaryingSample(
                time_hours=time_hours,
                satellite=sat_t,
                result=result,
                weather_label=weather_label,
                uplink_rain_attenuation_db=uplink_rain,
                downlink_rain_attenuation_db=downlink_rain,
            )
        )

    return samples


def summarize_time_varying_results(samples: list[TimeVaryingSample]) -> dict[str, float | str]:
    """Summarize the deterministic time-varying simulation output."""

    if not samples:
        return {}

    margins = np.array([s.result.combined_margin_db for s in samples], dtype=float)
    margins_ni = np.array([s.result.combined_margin_ni_db for s in samples], dtype=float)
    elevations_up = np.array([s.result.uplink.elevation_deg for s in samples], dtype=float)
    elevations_down = np.array([s.result.downlink.elevation_deg for s in samples], dtype=float)
    ranges_up = np.array([s.result.uplink.range_km for s in samples], dtype=float)
    ranges_down = np.array([s.result.downlink.range_km for s in samples], dtype=float)
    fspl_down = np.array([s.result.downlink.free_space_loss_db for s in samples], dtype=float)
    longitudes = np.array([s.satellite.longitude_deg for s in samples], dtype=float)
    latitudes = np.array([s.satellite.latitude_deg for s in samples], dtype=float)

    return {
        "sample_count": len(samples),
        "duration_hours": samples[-1].time_hours - samples[0].time_hours,
        "combined_margin_noise_only_min_dB": float(np.min(margins)),
        "combined_margin_noise_only_max_dB": float(np.max(margins)),
        "combined_margin_noise_only_peak_to_peak_dB": float(np.ptp(margins)),
        "combined_margin_with_interference_min_dB": float(np.min(margins_ni)),
        "combined_margin_with_interference_max_dB": float(np.max(margins_ni)),
        "combined_margin_with_interference_peak_to_peak_dB": float(np.ptp(margins_ni)),
        "uplink_elevation_min_deg": float(np.min(elevations_up)),
        "downlink_elevation_min_deg": float(np.min(elevations_down)),
        "uplink_range_peak_to_peak_km": float(np.ptp(ranges_up)),
        "downlink_range_peak_to_peak_km": float(np.ptp(ranges_down)),
        "downlink_FSPL_peak_to_peak_dB": float(np.ptp(fspl_down)),
        "satellite_longitude_peak_to_peak_deg": float(np.ptp(longitudes)),
        "satellite_latitude_peak_to_peak_deg": float(np.ptp(latitudes)),
    }


def summarize_monte_carlo_availability(samples: list[TimeVaryingSample]) -> dict[str, float | str]:
    """Summarize availability and outage statistics from the Monte-Carlo samples."""

    if not samples:
        return {}

    margins = np.array([s.result.combined_margin_ni_db for s in samples], dtype=float)
    rain_down = np.array([s.downlink_rain_attenuation_db for s in samples], dtype=float)
    tsys = np.array([s.result.downlink.system_noise_temperature_k or np.nan for s in samples], dtype=float)
    outage = margins < 0.0
    sample_hours = 8760.0 / len(samples)

    labels = [s.weather_label for s in samples]
    rain_samples = sum("rain" in label for label in labels)

    return {
        "sample_count": len(samples),
        "sample_hours": sample_hours,
        "availability_percent": float(100.0 * (1.0 - np.mean(outage))),
        "outage_probability_percent": float(100.0 * np.mean(outage)),
        "estimated_outage_hours_per_year": float(np.sum(outage) * sample_hours),
        "minimum_margin_dB_with_interference": float(np.min(margins)),
        "p01_margin_dB_with_interference": float(np.percentile(margins, 1.0)),
        "p05_margin_dB_with_interference": float(np.percentile(margins, 5.0)),
        "median_margin_dB_with_interference": float(np.median(margins)),
        "rain_sample_fraction_percent": float(100.0 * rain_samples / len(samples)),
        "maximum_downlink_rain_attenuation_dB": float(np.max(rain_down)),
        "maximum_downlink_Tsys_K": float(np.nanmax(tsys)),
    }


def calculate_asi_ci_grid(
    scenario: ScenarioConfig,
    dish_diameters_m: np.ndarray,
    satellite_spacing_deg: np.ndarray,
    link: str = "downlink",
) -> np.ndarray:
    """Calculate a C/I grid over dish diameter and adjacent-satellite spacing."""

    values = np.zeros((len(satellite_spacing_deg), len(dish_diameters_m)))
    for i, spacing in enumerate(satellite_spacing_deg):
        adjacent = replace(
            scenario.satellite,
            longitude_deg=scenario.satellite.longitude_deg + float(spacing),
        )
        for j, diameter in enumerate(dish_diameters_m):
            if link == "downlink":
                if scenario.downlink.receiver.antenna is None:
                    values[i, j] = np.nan
                    continue
                rx_ant = replace(scenario.downlink.receiver.antenna, diameter_m=float(diameter), gain_dbi=None)
                rx_endpoint = replace(scenario.downlink.receiver, antenna=rx_ant)
                downlink = replace(scenario.downlink, receiver=rx_endpoint)
                test_scenario = replace(scenario, downlink=downlink)
                val = _single_adjacent_ci_downlink_db(test_scenario, adjacent, scenario.satellite)
            else:
                if scenario.uplink.transmitter.antenna is None:
                    values[i, j] = np.nan
                    continue
                tx_ant = replace(scenario.uplink.transmitter.antenna, diameter_m=float(diameter), gain_dbi=None)
                tx_endpoint = replace(scenario.uplink.transmitter, antenna=tx_ant)
                uplink = replace(scenario.uplink, transmitter=tx_endpoint)
                test_scenario = replace(scenario, uplink=uplink)
                val = _single_adjacent_ci_uplink_db(test_scenario, adjacent, scenario.satellite)
            values[i, j] = val if val is not None else np.nan
    return values


# ========================================================================
# 8.            ITU-R PROPAGATION AND DVB-S2 ACM INTEGRATION 
# ========================================================================
def _link_attenuation_breakdown(
    config: ITUPropagationConfig,
    frequency_hz: float,
    geometry: LinkGeometry,
    ground_location: Location,
    ground_antenna: Optional[DishAntenna],
    exceedance_percent: float,
) -> "itu.AttenuationBreakdown":
    """Compute the ITU-R slant-path attenuation breakdown at one ground terminal.

    The geometry is evaluated at the ground-station end of the path (its
    elevation and latitude), because that is where the slant path enters the
    troposphere. The transmit/receive antenna size feeds the scintillation
    aperture-averaging factor.
    """

    diameter_m = ground_antenna.diameter_m if ground_antenna is not None else None
    efficiency = ground_antenna.efficiency if ground_antenna is not None else 0.6
    return itu.total_slant_path_attenuation(
        frequency_ghz=frequency_hz / 1.0e9,
        elevation_deg=geometry.elevation_deg,
        latitude_deg=ground_location.latitude_deg,
        station_height_km=ground_location.altitude_km,
        exceedance_percent=exceedance_percent,
        rain_rate_001_mm_per_h=config.rain_rate_001_mm_per_h,
        polarization_tilt_deg=config.polarization_tilt_deg,
        rain_height_override_km=config.rain_height_h0_override_km,
        pressure_hpa=config.surface_pressure_hpa,
        temperature_c=config.surface_temperature_c,
        water_vapour_density_g_m3=config.water_vapour_density_g_m3,
        relative_humidity_percent=config.relative_humidity_percent,
        columnar_liquid_water_kg_m2=config.columnar_liquid_water_kg_m2,
        antenna_diameter_m=diameter_m,
        antenna_efficiency=efficiency,
        include_gaseous=config.include_gaseous,
        include_cloud=config.include_cloud,
        include_scintillation=config.include_scintillation,
    )


def calculate_itu_attenuation(
    scenario: ScenarioConfig,
    exceedance_percent: float,
    satellite_override: Optional[GeoSatellite] = None,
) -> tuple["itu.AttenuationBreakdown", "itu.AttenuationBreakdown"]:
    """Return ``(uplink_breakdown, downlink_breakdown)`` for one time percentage.

    The uplink breakdown is evaluated at GS1 on the uplink frequency, and the
    downlink breakdown at GS2 on the downlink frequency, using the published
    ITU-R Recommendations in ``itu_propagation.py``.
    """

    satellite = satellite_override or scenario.satellite
    cfg = scenario.itu_propagation

    gs1 = scenario.uplink.transmitter.location
    gs2 = scenario.downlink.receiver.location
    if gs1 is None or gs2 is None:
        raise ValueError("Both ground-station locations are required for the ITU model.")

    uplink_geometry = calculate_geo_link_geometry(gs1, satellite)
    downlink_geometry = calculate_geo_link_geometry(gs2, satellite)

    uplink_breakdown = _link_attenuation_breakdown(
        cfg,
        scenario.uplink.frequency_hz,
        uplink_geometry,
        gs1,
        scenario.uplink.transmitter.antenna,
        exceedance_percent,
    )
    downlink_breakdown = _link_attenuation_breakdown(
        cfg,
        scenario.downlink.frequency_hz,
        downlink_geometry,
        gs2,
        scenario.downlink.receiver.antenna,
        exceedance_percent,
    )
    return uplink_breakdown, downlink_breakdown


def _absorptive_attenuation_db(breakdown: "itu.AttenuationBreakdown") -> float:
    """Return the absorptive attenuation (rain + cloud + gas) that emits sky noise.

    Scintillation is a refractive (focusing/defocusing) effect, so it degrades
    the carrier but does not raise the antenna noise temperature.
    """

    return breakdown.rain_db + breakdown.cloud_db + breakdown.gaseous_db


def select_downlink_modcod(
    scenario: ScenarioConfig,
    faded_result: ScenarioResult,
) -> Optional[ModcodSelection]:
    """Select the best DVB-S2 MODCOD for the (possibly faded) end-to-end downlink.

    The forward-link demodulator at GS2 sees the combined uplink+downlink
    carrier-to-noise-plus-interference ratio. That ratio is converted to a
    symbol-rate Es/N0 for the configured rolloff, then matched against the
    standard MODCOD ladder.
    """

    cfg = scenario.modcod
    if not cfg.enabled:
        return None

    bandwidth = scenario.downlink.bandwidth_hz
    combined_cn0_ni_dbhz = faded_result.combined_cni_db + 10.0 * log10(bandwidth)
    available_esn0_db = esn0_from_cn0_db(combined_cn0_ni_dbhz, bandwidth, cfg.rolloff_factor)
    return select_best_modcod(
        available_esn0_db=available_esn0_db,
        bandwidth_hz=bandwidth,
        rolloff_factor=cfg.rolloff_factor,
        implementation_margin_db=cfg.implementation_margin_db,
    )


def calculate_scenario_with_itu(
    scenario: ScenarioConfig,
    exceedance_percent: Optional[float] = None,
    satellite_override: Optional[GeoSatellite] = None,
    fade_application: str = "both",
    include_atmospheric_emission: bool = True,
) -> ITUPropagationResult:
    """Evaluate the scenario with a per-path ITU-R-informed fade applied.

    The static budget contains a fixed clear-sky atmospheric allowance. For each
    path receiving an ITU attenuation, that allowance is removed and replaced by
    the absolute modeled atmospheric total, preventing double-counting.

    ``fade_application="both"`` applies the same per-path exceedance percentage
    to Rome and Ankara simultaneously. It is deliberately reported as a
    coincident dual-site stress case, not as a statistically derived end-to-end
    availability point.

    Parameters
    ----------
    exceedance_percent:
        Time percentage ``p`` for which the attenuation is exceeded. Defaults to
        ``100 - design_availability_percent`` from the scenario configuration.

    Raises
    ------
    ValueError
        If ITU-R propagation is disabled in the scenario configuration.
    """

    cfg = scenario.itu_propagation
    if not cfg.enabled:
        raise ValueError("ITU-R propagation is disabled in scenario.itu_propagation.enabled.")
    if fade_application not in {"uplink", "downlink", "both"}:
        raise ValueError("fade_application must be 'uplink', 'downlink', or 'both'.")
    p = exceedance_percent if exceedance_percent is not None else cfg.design_exceedance_percent

    uplink_breakdown, downlink_breakdown = calculate_itu_attenuation(
        scenario, p, satellite_override=satellite_override
    )

    apply_uplink = fade_application in {"uplink", "both"}
    apply_downlink = fade_application in {"downlink", "both"}

    budget_scenario = replace(
        scenario,
        uplink=replace(
            scenario.uplink,
            losses=replace(
                scenario.uplink.losses,
                atmospheric_loss_db=0.0 if apply_uplink else scenario.uplink.losses.atmospheric_loss_db,
            ),
        ),
        downlink=replace(
            scenario.downlink,
            losses=replace(
                scenario.downlink.losses,
                atmospheric_loss_db=0.0 if apply_downlink else scenario.downlink.losses.atmospheric_loss_db,
            ),
        ),
    )

    uplink_environment = LinkEnvironment(
        rain_attenuation_db=uplink_breakdown.total_db if apply_uplink else 0.0,
        emission_attenuation_db=(
            _absorptive_attenuation_db(uplink_breakdown)
            if apply_uplink and include_atmospheric_emission
            else 0.0
        ),
        weather_label=f"ITU p={p:g}% ({fade_application})",
    )
    downlink_environment = LinkEnvironment(
        rain_attenuation_db=downlink_breakdown.total_db if apply_downlink else 0.0,
        emission_attenuation_db=(
            _absorptive_attenuation_db(downlink_breakdown)
            if apply_downlink and include_atmospheric_emission
            else 0.0
        ),
        weather_label=f"ITU p={p:g}% ({fade_application})",
    )

    faded_result = calculate_scenario(
        budget_scenario,
        satellite_override=satellite_override,
        uplink_environment=uplink_environment,
        downlink_environment=downlink_environment,
        use_dynamic_downlink_tsys=True,
    )

    downlink_modcod = select_downlink_modcod(budget_scenario, faded_result)

    return ITUPropagationResult(
        design_availability_percent=100.0 - p,
        design_exceedance_percent=p,
        fade_application=fade_application,
        uplink_breakdown=uplink_breakdown,
        downlink_breakdown=downlink_breakdown,
        faded_result=faded_result,
        uplink_modcod=None,
        downlink_modcod=downlink_modcod,
    )


def calculate_itu_availability_curve(
    scenario: ScenarioConfig,
    exceedance_percents: Optional[Sequence[float]] = None,
    fade_application: str = "both",
) -> list[ITUPropagationResult]:
    """Return faded results across per-path exceedance percentages.

    With ``fade_application="both"``, each curve point is a coincident dual-site
    stress case. The x-axis may be expressed as per-path non-exceedance, but it
    is not a joint end-to-end availability distribution.

    Raises
    ------
    ValueError
        If ITU-R propagation is disabled in the scenario configuration.
    """

    cfg = scenario.itu_propagation
    if not cfg.enabled:
        raise ValueError("ITU-R propagation is disabled in scenario.itu_propagation.enabled.")
    percents = exceedance_percents if exceedance_percents is not None else cfg.availability_curve_percents
    return [
        calculate_scenario_with_itu(
            scenario,
            float(p),
            fade_application=fade_application,
        )
        for p in percents
    ]


def summarize_itu_availability_curve(
    results: list[ITUPropagationResult],
    design_result: ITUPropagationResult,
) -> dict[str, float | str]:
    """Summarize the ITU-R-informed p-point sweep.

    Parameters
    ----------
    results:
        The full per-path non-exceedance sweep.
    design_result:
        The result at the configured per-path exceedance point (already evaluated by
        :func:`calculate_scenario_with_itu`).
    """

    if not results:
        return {}

    closes = [r for r in results if r.faded_result.combined_margin_ni_db >= 0.0]
    best_non_exceedance = max(
        (r.design_availability_percent for r in closes),
        default=float("nan"),
    )

    return {
        "design_per_path_non_exceedance_percent": design_result.design_availability_percent,
        "fade_application": design_result.fade_application,
        "design_downlink_total_attenuation_dB": design_result.downlink_breakdown.total_db,
        "design_uplink_total_attenuation_dB": design_result.uplink_breakdown.total_db,
        "design_combined_margin_with_interference_dB": design_result.faded_result.combined_margin_ni_db,
        "highest_closed_per_path_non_exceedance_percent_in_sweep": best_non_exceedance,
        "design_downlink_MODCOD": (
            design_result.downlink_modcod.selected.name
            if design_result.downlink_modcod is not None and design_result.downlink_modcod.selected is not None
            else "n/a"
        ),
    }


# ========================================================================
# 9.                       SCENARIO VALIDATION
# ========================================================================
def validate_scenario_config(scenario: ScenarioConfig) -> tuple[list[str], list[str]]:
    """Validate a scenario configuration and return ``(warnings, errors)``.

    ``errors`` describe conditions that would make the analysis invalid or crash;
    ``warnings`` flag values that are merely unusual. Longitudes follow the
    project convention of east-positive degrees and may be given either signed
    in [-180, 180] or unsigned in [0, 360]; both are accepted.

    Checks against a disabled module are skipped: e.g. interference longitudes
    are only validated when ``scenario.interference.enabled`` is True.
    """

    warnings: list[str] = []
    errors: list[str] = []

    def check_location(label: str, loc: Optional[Location]) -> None:
        if loc is None:
            errors.append(f"{label} location is missing.")
            return
        if not (-90.0 <= loc.latitude_deg <= 90.0):
            errors.append(f"{label} latitude {loc.latitude_deg} deg is outside [-90, 90].")
        if not (-180.0 <= loc.longitude_deg <= 360.0):
            errors.append(f"{label} longitude {loc.longitude_deg} deg is outside [-180, 360] (east-positive).")

    def check_antenna(label: str, ant: Optional[DishAntenna]) -> None:
        if ant is None:
            return
        if ant.diameter_m is not None and ant.diameter_m <= 0.0:
            errors.append(f"{label} antenna diameter must be > 0 m.")
        if not (0.0 < ant.efficiency <= 1.0):
            errors.append(f"{label} antenna efficiency {ant.efficiency} must be in (0, 1].")

    def has_antenna_gain(ant: Optional[DishAntenna]) -> bool:
        return ant is not None and (ant.gain_dbi is not None or ant.diameter_m is not None)

    def check_link(label: str, link: LinkConfig) -> None:
        if link.frequency_hz <= 0.0:
            errors.append(f"{label} frequency must be > 0 Hz.")
        if link.bandwidth_hz <= 0.0:
            errors.append(f"{label} bandwidth must be > 0 Hz.")
        if link.bit_rate_bps <= 0.0:
            errors.append(f"{label} bit rate must be > 0 bit/s.")
        if link.bandwidth_hz > 0.0 and link.bit_rate_bps > 5.0 * link.bandwidth_hz:
            warnings.append(
                f"{label} bit rate ({link.bit_rate_bps / 1e6:.1f} Mbit/s) exceeds 5x the "
                f"bandwidth ({link.bandwidth_hz / 1e6:.1f} MHz); spectral efficiency is unusually high."
            )

    # Ground-station geometry.
    check_location("GS1 (uplink Tx)", scenario.uplink.transmitter.location)
    check_location("GS2 (downlink Rx)", scenario.downlink.receiver.location)
    if not (-180.0 <= scenario.satellite.longitude_deg <= 360.0):
        errors.append(f"Satellite longitude {scenario.satellite.longitude_deg} deg is outside [-180, 360].")

    # Links and antennas.
    check_link("Uplink", scenario.uplink)
    check_link("Downlink", scenario.downlink)
    if not np.isclose(scenario.uplink.bit_rate_bps, scenario.downlink.bit_rate_bps):
        errors.append("Bent-pipe uplink and downlink bit rates must match.")
    if not np.isclose(scenario.uplink.bandwidth_hz, scenario.downlink.bandwidth_hz):
        errors.append("Bent-pipe uplink and downlink bandwidths must match.")
    check_antenna("GS1 transmit", scenario.uplink.transmitter.antenna)
    check_antenna("GS2 receive", scenario.downlink.receiver.antenna)

    # GS1 uplink transmit capability.
    tx = scenario.uplink.transmitter
    if tx.eirp_dbw_override is None:
        if tx.tx_power_dbw is None:
            errors.append("Uplink transmitter needs tx_power_dbw or eirp_dbw_override.")
        if not has_antenna_gain(tx.antenna):
            errors.append("Uplink transmitter needs an antenna gain/diameter (or an EIRP override).")

    # Satellite downlink EIRP (no antenna model on the satellite side).
    sat_tx = scenario.downlink.transmitter
    if sat_tx.eirp_dbw_override is None and sat_tx.tx_power_dbw is None:
        errors.append("Satellite downlink transmitter needs eirp_dbw_override.")

    # Satellite uplink receive G/T (no antenna/Tsys model on the satellite side).
    sat_rx = scenario.uplink.receiver
    if sat_rx.g_over_t_db_per_k_override is None and (
        not has_antenna_gain(sat_rx.antenna) or sat_rx.system_noise_temperature_k is None
    ):
        errors.append("Satellite uplink receiver needs g_over_t_db_per_k_override (or antenna + Tsys).")

    # GS2 downlink receiver.
    gs2_rx = scenario.downlink.receiver
    if gs2_rx.g_over_t_db_per_k_override is None:
        if gs2_rx.system_noise_temperature_k is None:
            errors.append("GS2 receiver needs system_noise_temperature_k or g_over_t_db_per_k_override.")
        elif gs2_rx.system_noise_temperature_k <= 0.0:
            errors.append("GS2 receiver system noise temperature must be > 0 K.")
        if not has_antenna_gain(gs2_rx.antenna):
            errors.append("GS2 receiver needs an antenna gain/diameter (or a G/T override).")

    # Interference (advanced).
    if scenario.interference.enabled:
        for lon in scenario.interference.adjacent_satellite_longitudes_deg:
            if not (-180.0 <= lon <= 360.0):
                errors.append(f"Adjacent satellite longitude {lon} deg is outside [-180, 360].")
        imd = scenario.interference.imd_c_i_db
        if imd is not None and imd <= 0.0:
            errors.append("Interference IMD C/I must be > 0 dB or None.")

    # Apparent GEO motion (advanced).
    if scenario.apparent_motion.enabled:
        if scenario.apparent_motion.duration_hours <= 0.0:
            errors.append("Apparent motion duration_hours must be > 0.")
        if scenario.apparent_motion.step_minutes <= 0.0:
            errors.append("Apparent motion step_minutes must be > 0.")

    # Dynamic receiver noise (advanced).
    if scenario.dynamic_noise.enabled:
        dynamic_values = {
            "receiver_internal_noise_k": scenario.dynamic_noise.receiver_internal_noise_k,
            "spillover_noise_k": scenario.dynamic_noise.spillover_noise_k,
            "clear_sky_base_noise_k": scenario.dynamic_noise.clear_sky_base_noise_k,
            "low_elevation_extra_noise_k": scenario.dynamic_noise.low_elevation_extra_noise_k,
            "rain_emission_temperature_k": scenario.dynamic_noise.rain_emission_temperature_k,
        }
        for name, value in dynamic_values.items():
            if value < 0.0:
                errors.append(f"Dynamic-noise {name} must be >= 0.")
        if scenario.dynamic_noise.minimum_elevation_deg <= 0.0:
            errors.append("Dynamic-noise minimum_elevation_deg must be > 0.")

    # Monte-Carlo rain outage (advanced).
    if scenario.rain_outage.enabled:
        rain_cfg = scenario.rain_outage
        if rain_cfg.samples_per_year <= 0:
            errors.append("Monte-Carlo rain outage samples_per_year must be > 0.")
        probabilities = {
            "light_rain_probability": rain_cfg.light_rain_probability,
            "moderate_rain_probability": rain_cfg.moderate_rain_probability,
            "heavy_rain_probability": rain_cfg.heavy_rain_probability,
        }
        for name, value in probabilities.items():
            if not (0.0 <= value <= 1.0):
                errors.append(f"Monte-Carlo {name} must be in [0, 1].")
        if sum(probabilities.values()) > 1.0:
            errors.append("Monte-Carlo rain-state probabilities must sum to <= 1.")
        if rain_cfg.clear_attenuation_max_db < 0.0:
            errors.append("Monte-Carlo clear_attenuation_max_db must be >= 0.")
        for name, bounds in (
            ("light_rain_attenuation_range_db", rain_cfg.light_rain_attenuation_range_db),
            ("moderate_rain_attenuation_range_db", rain_cfg.moderate_rain_attenuation_range_db),
            ("heavy_rain_attenuation_range_db", rain_cfg.heavy_rain_attenuation_range_db),
        ):
            lo, hi = bounds
            if lo < 0.0 or hi < 0.0 or lo > hi:
                errors.append(f"Monte-Carlo {name} must be non-negative and ordered low <= high.")
        if rain_cfg.uplink_frequency_scaling_exponent < 0.0:
            errors.append("Monte-Carlo uplink_frequency_scaling_exponent must be >= 0.")
        if rain_cfg.downlink_frequency_scaling_exponent < 0.0:
            errors.append("Monte-Carlo downlink_frequency_scaling_exponent must be >= 0.")

    # ITU-R propagation (advanced).
    if scenario.itu_propagation.enabled:
        availability = scenario.itu_propagation.design_availability_percent
        if not (0.0 < availability < 100.0):
            errors.append("ITU design_availability_percent must be in (0, 100).")
        if scenario.itu_propagation.rain_rate_001_mm_per_h < 0.0:
            errors.append("ITU rain_rate_001_mm_per_h must be >= 0.")
        if scenario.itu_propagation.rain_height_h0_override_km is not None and (
            scenario.itu_propagation.rain_height_h0_override_km < 0.0
        ):
            errors.append("ITU rain_height_h0_override_km must be >= 0 or None.")
        if scenario.itu_propagation.surface_pressure_hpa <= 0.0:
            errors.append("ITU surface_pressure_hpa must be > 0.")
        if scenario.itu_propagation.water_vapour_density_g_m3 < 0.0:
            errors.append("ITU water_vapour_density_g_m3 must be >= 0.")
        if not (0.0 <= scenario.itu_propagation.relative_humidity_percent <= 100.0):
            errors.append("ITU relative_humidity_percent must be in [0, 100].")
        if scenario.itu_propagation.columnar_liquid_water_kg_m2 < 0.0:
            errors.append("ITU columnar_liquid_water_kg_m2 must be >= 0.")
        p = scenario.itu_propagation.design_exceedance_percent
        if not (0.001 <= p <= 5.0):
            warnings.append(
                f"ITU design exceedance p={p:g}% is outside the ITU-R P.618 scaling range 0.001%-5%."
            )
        curve = tuple(float(value) for value in scenario.itu_propagation.availability_curve_percents)
        if not curve:
            errors.append("ITU availability_curve_percents must not be empty.")
        for curve_p in curve:
            if not (0.001 <= curve_p <= 5.0):
                errors.append(
                    f"ITU availability-curve exceedance p={curve_p:g}% must be in [0.001, 5]."
                )
        if scenario.itu_propagation.include_scintillation and any(value < 0.01 for value in curve):
            warnings.append(
                "Scintillation is held at its p=0.01% endpoint for curve points below "
                "the P.618 submodel's stated range."
            )

    # DVB-S2 ACM (advanced).
    if scenario.modcod.enabled and scenario.modcod.rolloff_factor < 0.0:
        errors.append("MODCOD rolloff_factor must be >= 0.")

    # Digital metrics.
    if scenario.digital.enabled:
        if not (0.0 < scenario.digital.code_rate <= 1.0):
            errors.append("Digital code_rate must be in (0, 1].")
        if scenario.digital.rolloff_factor < 0.0:
            errors.append("Digital rolloff_factor must be >= 0.")

    return warnings, errors
