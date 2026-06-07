# itu_propagation.py
"""ITU-R atmosferik yayılım (sönümleme) modelleri.

Not: Bu modül, UZB451 ödevindeki zorunlu statik hat bütçesine ekstra olarak
gerçekçilik katmak amacıyla eklenmiştir (MATLAB'deki "Include P.618 Losses" 
özelliğinin açık haline denk gelir). Statik açık hava ödevi için bu modülün 
kapatılması gerekir.

İçerdiği standartlar:
*   ITU-R P.838 / P.839: Spesifik yağış zayıflama katsayıları ve yağış yüksekliği
*   ITU-R P.618: İstenen kesinti (outage) süresine göre eğik yol yağış sönümlemesi ve sintilasyon
*   ITU-R P.676: Oksijen ve su buharından kaynaklanan gaz sönümlemesi
*   ITU-R P.840: Bulut ve sis kaynaklı sinyal zayıflaması
"""

# ========================================================================
# 0.                             IMPORTS
# ========================================================================
from __future__ import annotations

from dataclasses import dataclass
from math import atan, atan2, cos, exp, log, log10, radians, sin, sqrt
from typing import Sequence

try:
    from .constants import (
        DEG_TO_RAD,
        EFFECTIVE_EARTH_RADIUS_KM,
        MINIMUM_VALID_ELEVATION_DEG,
        RAD_TO_DEG,
        SCINTILLATION_TURBULENT_LAYER_HEIGHT_M,
    )
except ImportError:  # Support direct execution with ``python src/main.py``.
    from constants import (
        DEG_TO_RAD,
        EFFECTIVE_EARTH_RADIUS_KM,
        MINIMUM_VALID_ELEVATION_DEG,
        RAD_TO_DEG,
        SCINTILLATION_TURBULENT_LAYER_HEIGHT_M,
    )



# ========================================================================
# ========================================================================
# 1. YAĞIŞ SÖNÜMLEME MODELİ (Temel Müfredat Yağış Katsayıları Adımı)
#    ITU-R P.838-3  SPECIFIC RAIN ATTENUATION (k, alpha)
# ========================================================================
# Each coefficient (kH, kV, alphaH, alphaV) is modeled as a sum of Gaussian
# terms in log-frequency plus a linear term, exactly as tabulated in the
# Recommendation. The frequency f is in GHz and must lie in 1-1000 GHz.
#
#   log10(k)  = sum_j a_j * exp(-((log10 f - b_j) / c_j)^2) + m * log10 f + c
#   alpha     = sum_j a_j * exp(-((log10 f - b_j) / c_j)^2) + m * log10 f + c
#
# Tables are quoted verbatim from ITU-R P.838-3.

_P838_KH = {
    "a": (-5.33980, -0.35351, -0.23789, -0.94158),
    "b": (-0.10008, 1.26970, 0.86036, 0.64552),
    "c": (1.13098, 0.45400, 0.15354, 0.16817),
    "m": -0.18961,
    "k": 0.71147,
}
_P838_KV = {
    "a": (-3.80595, -3.44965, -0.39902, 0.50167),
    "b": (0.56934, -0.22911, 0.73042, 1.07319),
    "c": (0.81061, 0.51059, 0.11899, 0.27195),
    "m": -0.16398,
    "k": 0.63297,
}
_P838_AH = {
    "a": (-0.14318, 0.29591, 0.32177, -5.37610, 16.1721),
    "b": (1.82442, 0.77564, 0.63773, -0.96230, -3.29980),
    "c": (-0.55187, 0.19822, 0.13164, 1.47828, 3.43990),
    "m": 0.67849,
    "k": -1.95537,
}
_P838_AV = {
    "a": (-0.07771, 0.56727, -0.20238, -48.2991, 48.5833),
    "b": (2.33840, 0.95545, 1.14520, 0.791669, 0.791459),
    "c": (-0.76284, 0.54039, 0.26809, 0.116226, 0.116479),
    "m": -0.053739,
    "k": 0.83433,
}


def _p838_sum(table: dict[str, object], log_f: float) -> float:
    """Evaluate one ITU-R P.838-3 Gaussian-plus-linear coefficient series."""

    a = table["a"]  # type: ignore[assignment]
    b = table["b"]  # type: ignore[assignment]
    c = table["c"]  # type: ignore[assignment]
    total = 0.0
    for a_j, b_j, c_j in zip(a, b, c):  # type: ignore[arg-type]
        total += a_j * exp(-(((log_f - b_j) / c_j) ** 2))
    total += float(table["m"]) * log_f + float(table["k"])
    return total


def rain_coefficients_p838(
    frequency_ghz: float,
    elevation_deg: float,
    polarization_tilt_deg: float = 90.0,
) -> tuple[float, float]:
    """Return the rain power-law coefficients ``(k, alpha)`` per ITU-R P.838-3.

    The horizontal and vertical base coefficients are first evaluated from the
    tabulated frequency series, then rotated to the actual path geometry using
    the elevation angle ``theta`` and the polarization tilt angle ``tau``:

        k     = [kH + kV + (kH - kV) cos^2(theta) cos(2 tau)] / 2
        alpha = [kH*aH + kV*aV + (kH*aH - kV*aV) cos^2(theta) cos(2 tau)] / (2k)

    Parameters
    ----------
    frequency_ghz:
        Carrier frequency in GHz (valid 1-1000 GHz).
    elevation_deg:
        Path elevation angle in degrees.
    polarization_tilt_deg:
        Polarization tilt angle relative to the horizontal. Use 0 deg for
        horizontal, and 90 deg for vertical linear polarization assumption.
        Most VSAT/DTH Ku links are linearly polarized; defaulting to 90 deg (vertical).

    Returns
    -------
    tuple
        ``(k, alpha)`` for the slant path, ready for ``gamma = k * R**alpha``.
    """

    if not (1.0 <= frequency_ghz <= 1000.0):
        raise ValueError("ITU-R P.838-3 is defined for 1-1000 GHz.")

    log_f = log10(frequency_ghz)
    k_h = 10.0 ** _p838_sum(_P838_KH, log_f)
    k_v = 10.0 ** _p838_sum(_P838_KV, log_f)
    a_h = _p838_sum(_P838_AH, log_f)
    a_v = _p838_sum(_P838_AV, log_f)

    cos2_theta = cos(radians(elevation_deg)) ** 2
    cos_2tau = cos(2.0 * radians(polarization_tilt_deg))

    k = (k_h + k_v + (k_h - k_v) * cos2_theta * cos_2tau) / 2.0
    alpha = (
        k_h * a_h + k_v * a_v + (k_h * a_h - k_v * a_v) * cos2_theta * cos_2tau
    ) / (2.0 * k)
    return k, alpha


def rain_specific_attenuation_db_per_km(rain_rate_mm_per_h: float, k: float, alpha: float) -> float:
    """Return specific rain attenuation ``gamma_R = k * R**alpha`` in dB/km."""

    if rain_rate_mm_per_h <= 0.0:
        return 0.0
    return k * rain_rate_mm_per_h ** alpha


# ========================================================================
# 2. YAĞIŞ SÖNÜMLEME MODELİ (Temel Müfredat Yağış Yüksekliği Adımı)
#    ITU-R P.839-4  RAIN HEIGHT MODEL
# ========================================================================
def rain_height_km(latitude_deg: float, rain_height_override_km: float | None = None) -> float:
    """Return an approximate mean rain height ``h_R`` in km.

    The rain height is the mean annual 0 deg C isotherm height plus 0.36 km. The
    P.839-4 Recommendation distributes ``h0`` on a global digital map. This
    self-contained fallback uses a legacy piecewise latitude approximation and
    must not be described as a direct P.839 map extraction. Pass the mapped or
    measured ``h0`` through ``rain_height_override_km`` when available.

    Parameters
    ----------
    latitude_deg:
        Ground-station latitude in degrees (sign-aware; south is negative).
    rain_height_override_km:
        Optional measured/mapped 0 deg C isotherm height ``h0`` in km. When
        provided, ``h_R = h0 + 0.36`` is returned directly.
    """

    if rain_height_override_km is not None:
        return rain_height_override_km + 0.36

    phi = latitude_deg
    if phi > 23.0:
        h0 = 5.0 - 0.075 * (phi - 23.0)
    elif 0.0 <= phi <= 23.0:
        h0 = 5.0
    elif -21.0 <= phi < 0.0:
        h0 = 5.0
    elif -71.0 < phi < -21.0:
        h0 = 5.0 + 0.1 * (phi + 21.0)
    else:
        h0 = 0.0
    return max(h0, 0.0) + 0.36


# ========================================================================
# 3. YAĞIŞ SÖNÜMLEME MODELİ (Temel Müfredat Kullanılabilirlik/Kesinti Hesabı)
#    ITU-R P.618-13  SLANT-PATH RAIN ATTENUATION A(p)
# ========================================================================
def rain_attenuation_001_db(
    frequency_ghz: float,
    elevation_deg: float,
    latitude_deg: float,
    station_height_km: float,
    rain_rate_001_mm_per_h: float,
    polarization_tilt_deg: float = 90.0,
    rain_height_override_km: float | None = None,
) -> float:
    """Return rain attenuation exceeded 0.01% of an average year, ``A_0.01`` [dB].

    This is the core long-term statistic of ITU-R P.618-13 Section 2.2.1.1.
    Every other exceedance percentage is derived from it by :func:`rain_attenuation_db`.

    Parameters
    ----------
    frequency_ghz:
        Carrier frequency in GHz.
    elevation_deg:
        Path elevation angle in degrees.
    latitude_deg:
        Station latitude in degrees (sign-aware).
    station_height_km:
        Station height above mean sea level in km.
    rain_rate_001_mm_per_h:
        Point rainfall rate exceeded 0.01% of the average year, ``R_0.01``
        (mm/h). Take this from ITU-R P.837 maps for the site, or use a regional
        value (e.g. ~30-50 mm/h for temperate climates).
    polarization_tilt_deg:
        Polarization tilt angle (90 deg for vertical linear polarization).
    rain_height_override_km:
        Optional 0 deg C isotherm height ``h0`` override (see :func:`rain_height_km`).
    """

    if rain_rate_001_mm_per_h <= 0.0:
        return 0.0

    theta = elevation_deg
    theta_rad = radians(theta)
    sin_theta = sin(theta_rad)
    cos_theta = cos(theta_rad)

    h_r = rain_height_km(latitude_deg, rain_height_override_km)
    delta_h = h_r - station_height_km
    if delta_h <= 0.0:
        return 0.0  # Station is at or above the rain layer.

    # Step 2: slant-path length below the rain height.
    if theta >= MINIMUM_VALID_ELEVATION_DEG:
        slant_length = delta_h / sin_theta
    else:
        slant_length = (
            2.0 * delta_h
            / (sqrt(sin_theta ** 2 + 2.0 * delta_h / EFFECTIVE_EARTH_RADIUS_KM) + sin_theta)
        )

    # Step 3: horizontal projection of the slant path.
    horizontal_proj = slant_length * cos_theta

    # Step 4: specific attenuation at the 0.01% rain rate.
    k, alpha = rain_coefficients_p838(frequency_ghz, theta, polarization_tilt_deg)
    gamma_r = rain_specific_attenuation_db_per_km(rain_rate_001_mm_per_h, k, alpha)

    # Step 5: horizontal reduction factor for 0.01% of the time.
    r_001 = 1.0 / (
        1.0
        + 0.78 * sqrt(horizontal_proj * gamma_r / frequency_ghz)
        - 0.38 * (1.0 - exp(-2.0 * horizontal_proj))
    )

    # Step 6: vertical adjustment factor for 0.01% of the time.
    zeta = atan2(delta_h, horizontal_proj * r_001)  # radians
    zeta_deg = zeta * RAD_TO_DEG
    if zeta_deg > theta:
        rain_path = horizontal_proj * r_001 / cos_theta
    else:
        rain_path = delta_h / sin_theta

    abs_lat = abs(latitude_deg)
    chi = 36.0 - abs_lat if abs_lat < 36.0 else 0.0
    v_001 = 1.0 / (
        1.0
        + sqrt(sin_theta)
        * (31.0 * (1.0 - exp(-(theta / (1.0 + chi)))) * sqrt(rain_path * gamma_r) / frequency_ghz ** 2 - 0.45)
    )

    # Step 7-8: effective path length and 0.01% attenuation.
    effective_path = rain_path * v_001
    return gamma_r * effective_path


def rain_attenuation_db(
    frequency_ghz: float,
    elevation_deg: float,
    latitude_deg: float,
    station_height_km: float,
    rain_rate_001_mm_per_h: float,
    exceedance_percent: float,
    polarization_tilt_deg: float = 90.0,
    rain_height_override_km: float | None = None,
) -> float:
    """Return rain attenuation exceeded ``exceedance_percent`` % of the year [dB].

    Implements the full ITU-R P.618-13 Section 2.2.1.1 procedure: first compute
    ``A_0.01`` and then extrapolate to the requested time percentage ``p`` using
    the published power-law scaling (valid for 0.001% <= p <= 5%).

    Parameters
    ----------
    exceedance_percent:
        Percentage of an average year for which the returned attenuation is
        exceeded. For example, 0.01 corresponds to 99.99% availability and 1.0
        to 99% availability.
    (others)
        See :func:`rain_attenuation_001_db`.
    """

    p = exceedance_percent
    if not (0.001 <= p <= 5.0):
        raise ValueError("ITU-R P.618-13 rain scaling is valid for 0.001% <= p <= 5%.")

    a_001 = rain_attenuation_001_db(
        frequency_ghz,
        elevation_deg,
        latitude_deg,
        station_height_km,
        rain_rate_001_mm_per_h,
        polarization_tilt_deg,
        rain_height_override_km,
    )
    if a_001 <= 0.0:
        return 0.0
    if p == 0.01:
        return a_001

    abs_lat = abs(latitude_deg)
    theta = elevation_deg
    if p >= 1.0 or abs_lat >= 36.0:
        beta = 0.0
    elif theta >= 25.0:
        beta = -0.005 * (abs_lat - 36.0)
    else:
        beta = -0.005 * (abs_lat - 36.0) + 1.8 - 4.25 * sin(radians(theta))

    exponent = (
        0.655
        + 0.033 * log(p)
        - 0.045 * log(a_001)
        - beta * (1.0 - p) * sin(radians(theta))
    )
    return a_001 * (p / 0.01) ** (-exponent)


# ========================================================================
# 4. [EXTRA - OPSİYONEL] GAZ SÖNÜMLEME MODELİ (Oksijen ve Su Buharı)
#    ITU-R P.676-12  GASEOUS (OXYGEN + WATER VAPOUR) ATTENUATION
# ========================================================================
def _water_vapour_partial_pressure_hpa(water_vapour_density_g_m3: float, temperature_c: float) -> float:
    """Return water-vapour partial pressure ``e`` in hPa from density and temperature."""

    temperature_k = 273.15 + temperature_c
    return water_vapour_density_g_m3 * temperature_k / 216.7


def gaseous_specific_attenuation_db_per_km(
    frequency_ghz: float,
    pressure_hpa: float,
    temperature_c: float,
    water_vapour_density_g_m3: float,
) -> tuple[float, float]:
    """Return ``(gamma_oxygen, gamma_water_vapour)`` in dB/km (ITU-R P.676-12 Annex 2).

    The oxygen branch is the f <= 54 GHz approximation, which covers every
    practical satellite-communications band up to Ka (L, S, C, X, Ku, and the
    lower Ka segment). The water-vapour branch includes the full resonance-line
    sum and is valid up to 350 GHz.

    Parameters
    ----------
    frequency_ghz:
        Carrier frequency in GHz.
    pressure_hpa:
        Total barometric (dry + wet) pressure in hPa. Sea-level standard is
        about 1013.25 hPa.
    temperature_c:
        Surface air temperature in degrees Celsius.
    water_vapour_density_g_m3:
        Surface water-vapour density (absolute humidity) in g/m^3. A global
        reference value is 7.5 g/m^3.
    """

    if frequency_ghz > 54.0:
        raise ValueError(
            "The oxygen branch implemented here is valid up to 54 GHz, which "
            "covers all standard SatCom bands through lower Ka."
        )

    f = frequency_ghz
    rho = water_vapour_density_g_m3
    r_p = pressure_hpa / 1013.0
    r_t = 288.0 / (273.0 + temperature_c)

    # --- Oxygen (dry air), P.676-12 Annex 2 eq. (1) for f <= 54 GHz ---
    def phi(a: float, b: float, c: float, d: float) -> float:
        return r_p ** a * r_t ** b * exp(c * (1.0 - r_p) + d * (1.0 - r_t))

    xi1 = phi(0.0717, -1.8132, 0.0156, -1.6515)
    xi2 = phi(0.5146, -4.6368, -0.1921, -5.7416)
    xi3 = phi(0.3414, -6.5851, 0.2130, -8.5854)

    gamma_o = (
        7.2 * r_t ** 2.8 / (f ** 2 + 0.34 * r_p ** 2 * r_t ** 1.6)
        + 0.62 * xi3 / ((54.0 - f) ** (1.16 * xi1) + 0.83 * xi2)
    ) * f ** 2 * r_p ** 2 * 1.0e-3

    # --- Water vapour, P.676-12 Annex 2 eq. (3) ---
    eta1 = 0.955 * r_p * r_t ** 0.68 + 0.006 * rho
    eta2 = 0.735 * r_p * r_t ** 0.5 + 0.0353 * r_t ** 4 * rho

    def g(fi: float) -> float:
        return 1.0 + ((f - fi) / (f + fi)) ** 2

    gamma_w = (
        3.98 * eta1 * exp(2.23 * (1.0 - r_t)) / ((f - 22.235) ** 2 + 9.42 * eta1 ** 2) * g(22.0)
        + 11.96 * eta1 * exp(0.70 * (1.0 - r_t)) / ((f - 183.31) ** 2 + 11.14 * eta1 ** 2)
        + 0.081 * eta1 * exp(6.44 * (1.0 - r_t)) / ((f - 321.226) ** 2 + 6.29 * eta1 ** 2)
        + 3.660 * eta1 * exp(1.60 * (1.0 - r_t)) / ((f - 325.153) ** 2 + 9.22 * eta1 ** 2)
        + 25.37 * eta1 * exp(1.09 * (1.0 - r_t)) / ((f - 380.0) ** 2)
        + 17.40 * eta1 * exp(1.46 * (1.0 - r_t)) / ((f - 448.0) ** 2)
        + 844.6 * eta1 * exp(0.17 * (1.0 - r_t)) / ((f - 557.0) ** 2) * g(557.0)
        + 290.0 * eta1 * exp(0.41 * (1.0 - r_t)) / ((f - 752.0) ** 2) * g(752.0)
        + 8.3328e4 * eta2 * exp(0.99 * (1.0 - r_t)) / ((f - 1780.0) ** 2) * g(1780.0)
    ) * f ** 2 * r_t ** 2.5 * rho * 1.0e-4

    return gamma_o, gamma_w


def _gas_equivalent_heights_km(
    frequency_ghz: float,
    pressure_hpa: float,
) -> tuple[float, float]:
    """Return ``(h_oxygen, h_water_vapour)`` equivalent heights in km (P.676-12 Annex 2)."""

    f = frequency_ghz
    r_p = pressure_hpa / 1013.0

    t1 = 4.64 / (1.0 + 0.066 * r_p ** -2.3) * exp(-(((f - 59.7) / (2.87 + 12.4 * exp(-7.9 * r_p))) ** 2))
    t2 = 0.14 * exp(2.12 * r_p) / ((f - 118.75) ** 2 + 0.031 * exp(2.2 * r_p))
    t3 = (
        0.0114 / (1.0 + 0.14 * r_p ** -2.6)
        * f
        * (-0.0247 + 0.0001 * f + 1.61e-6 * f ** 2)
        / (1.0 - 0.0169 * f + 4.1e-5 * f ** 2 + 3.2e-7 * f ** 3)
    )
    h_o = 6.1 / (1.0 + 0.17 * r_p ** -1.1) * (1.0 + t1 + t2 + t3)
    if f < 70.0:
        h_o = min(h_o, 10.7 * r_p ** 0.3)

    sigma_w = 1.013 / (1.0 + exp(-8.6 * (r_p - 0.57)))
    h_w = 1.66 * (
        1.0
        + 1.39 * sigma_w / ((f - 22.235) ** 2 + 2.56 * sigma_w)
        + 3.37 * sigma_w / ((f - 183.31) ** 2 + 4.69 * sigma_w)
        + 1.58 * sigma_w / ((f - 325.1) ** 2 + 2.89 * sigma_w)
    )
    return h_o, h_w


def gaseous_attenuation_db(
    frequency_ghz: float,
    elevation_deg: float,
    pressure_hpa: float = 1013.25,
    temperature_c: float = 15.0,
    water_vapour_density_g_m3: float = 7.5,
) -> float:
    """Return total slant-path gaseous attenuation in dB (ITU-R P.676-12 Annex 2).

    The zenith attenuation is built from the specific attenuations and their
    equivalent heights, then projected onto the slant path with the cosecant
    law for elevation angles >= 5 degrees.
    """

    gamma_o, gamma_w = gaseous_specific_attenuation_db_per_km(
        frequency_ghz, pressure_hpa, temperature_c, water_vapour_density_g_m3
    )
    h_o, h_w = _gas_equivalent_heights_km(frequency_ghz, pressure_hpa)
    zenith_attenuation = gamma_o * h_o + gamma_w * h_w

    sin_theta = sin(radians(max(elevation_deg, MINIMUM_VALID_ELEVATION_DEG)))
    return zenith_attenuation / sin_theta


# ========================================================================
# 5. [EXTRA - OPSİYONEL] BULUT VE SİS SÖNÜMLEME MODELİ
#    ITU-R P.840-8  CLOUD / FOG LIQUID-WATER ATTENUATION
# ========================================================================
def cloud_specific_attenuation_coefficient(frequency_ghz: float, temperature_c: float = 0.0) -> float:
    """Return the cloud specific attenuation coefficient ``K_l`` [(dB/km)/(g/m^3)].

    Uses the Rayleigh scattering approximation with the double-Debye model for
    the complex permittivity of water, as specified in ITU-R P.840-8. Valid up
    to ~200 GHz.
    """

    f = frequency_ghz
    temperature_k = 273.15 + temperature_c
    theta = 300.0 / temperature_k

    eps0 = 77.66 + 103.3 * (theta - 1.0)
    eps1 = 0.0671 * eps0
    eps2 = 3.52
    fp = 20.20 - 146.0 * (theta - 1.0) + 316.0 * (theta - 1.0) ** 2  # primary relaxation, GHz
    fs = 39.8 * fp  # secondary relaxation, GHz

    eps_imag = (
        f * (eps0 - eps1) / (fp * (1.0 + (f / fp) ** 2))
        + f * (eps1 - eps2) / (fs * (1.0 + (f / fs) ** 2))
    )
    eps_real = (
        (eps0 - eps1) / (1.0 + (f / fp) ** 2)
        + (eps1 - eps2) / (1.0 + (f / fs) ** 2)
        + eps2
    )

    eta = (2.0 + eps_real) / eps_imag
    return 0.819 * f / (eps_imag * (1.0 + eta ** 2))


def cloud_attenuation_db(
    frequency_ghz: float,
    elevation_deg: float,
    columnar_liquid_water_kg_m2: float,
    cloud_temperature_c: float = 0.0,
) -> float:
    """Return slant-path cloud attenuation in dB (ITU-R P.840-8).

    Parameters
    ----------
    columnar_liquid_water_kg_m2:
        Total columnar content of cloud liquid water exceeded for the desired
        percentage of time, in kg/m^2 (equivalently mm). ITU-R P.840 maps give
        roughly 0.4-2 kg/m^2 at the 1%-0.1% levels for temperate climates.
    cloud_temperature_c:
        Representative liquid-water temperature; 0 deg C is the standard choice.
    """

    if columnar_liquid_water_kg_m2 <= 0.0:
        return 0.0
    k_l = cloud_specific_attenuation_coefficient(frequency_ghz, cloud_temperature_c)
    sin_theta = sin(radians(max(elevation_deg, MINIMUM_VALID_ELEVATION_DEG)))
    return columnar_liquid_water_kg_m2 * k_l / sin_theta


# ========================================================================
# 6. [EXTRA - OPSİYONEL] TROPOSFERİK SİNTİLASYON MODELİ (Hızlı Sinyal Dalgalanması)
#    ITU-R P.453 / P.618-13  TROPOSPHERIC SCINTILLATION
# ========================================================================
def wet_term_refractivity_n_wet(temperature_c: float, relative_humidity_percent: float) -> float:
    """Return the wet term of radio refractivity ``N_wet`` (ITU-R P.453-14).

    The saturation vapour pressure follows the standard Magnus relation; the
    wet refractivity is dominated by the ``3.732e5 * e / T^2`` term.
    """

    temperature_k = 273.15 + temperature_c
    e_sat = 6.1121 * exp(17.502 * temperature_c / (temperature_c + 240.97))
    e = (relative_humidity_percent / 100.0) * e_sat
    return 3.732e5 * e / temperature_k ** 2


def _scintillation_aperture_factor(x: float) -> float:
    """Return the antenna aperture-averaging factor ``g(x)`` (ITU-R P.618-13)."""

    if x >= 1.0e6:
        return 0.0
    value = 3.86 * (x ** 2 + 1.0) ** (11.0 / 12.0) * sin(11.0 / 6.0 * atan(1.0 / x)) - 7.08 * x ** (5.0 / 6.0)
    return sqrt(value) if value > 0.0 else 0.0


def scintillation_fade_db(
    frequency_ghz: float,
    elevation_deg: float,
    antenna_diameter_m: float,
    antenna_efficiency: float,
    temperature_c: float,
    relative_humidity_percent: float,
    exceedance_percent: float,
) -> float:
    """Return tropospheric scintillation fade depth in dB (ITU-R P.618-13 Sec. 2.4.1).

    Parameters
    ----------
    antenna_diameter_m:
        Physical antenna diameter in metres.
    antenna_efficiency:
        Antenna aperture efficiency (0-1). The Recommendation suggests 0.5 when
        the true value is unknown.
    temperature_c, relative_humidity_percent:
        Average surface conditions used to derive ``N_wet`` and the reference
        standard deviation of signal amplitude.
    exceedance_percent:
        Percentage of time the fade depth is exceeded (valid 0.01% <= p <= 50%).
    """

    if not (0.01 <= exceedance_percent <= 50.0):
        raise ValueError("Scintillation exceedance_percent must be in [0.01, 50].")
    p = exceedance_percent
    theta = max(elevation_deg, 4.0)
    sin_theta = sin(radians(theta))

    n_wet = wet_term_refractivity_n_wet(temperature_c, relative_humidity_percent)
    sigma_ref = 3.6e-3 + 1.0e-4 * n_wet  # dB

    # Effective turbulent path length (turbulent-layer height h_L = 1000 m).
    h_l = SCINTILLATION_TURBULENT_LAYER_HEIGHT_M
    re_m = EFFECTIVE_EARTH_RADIUS_KM * SCINTILLATION_TURBULENT_LAYER_HEIGHT_M
    path_length_m = 2.0 * h_l / (sqrt(sin_theta ** 2 + 2.0 * h_l / re_m) + sin_theta)

    d_eff = sqrt(max(antenna_efficiency, 0.0)) * antenna_diameter_m
    x = 1.22 * d_eff ** 2 * (frequency_ghz / path_length_m)
    g_x = _scintillation_aperture_factor(x)

    sigma = sigma_ref * frequency_ghz ** (7.0 / 12.0) * g_x / sin_theta ** 1.2

    log_p = log10(p)
    a_p = -0.061 * log_p ** 3 + 0.072 * log_p ** 2 - 1.71 * log_p + 3.0
    return a_p * sigma


# ========================================================================
# 7. [EXTRA - OPSİYONEL] TOPLAM ATMOSFERİK SÖNÜMLEME BİRLEŞTİRME MODELİ
#    COMBINED SLANT-PATH ATTENUATION  (P.618-13 Sec. 2.5)
# ========================================================================
@dataclass(frozen=True)
class AttenuationBreakdown:
    """Per-mechanism slant-path attenuation and their P.618 combination [dB]."""

    exceedance_percent: float
    rain_db: float
    gaseous_db: float
    cloud_db: float
    scintillation_db: float
    total_db: float

    def to_dict(self) -> dict[str, float]:
        """Return the breakdown as a CSV-friendly mapping."""

        return {
            "exceedance_percent": self.exceedance_percent,
            "availability_percent": 100.0 - self.exceedance_percent,
            "rain_attenuation_dB": self.rain_db,
            "gaseous_attenuation_dB": self.gaseous_db,
            "cloud_attenuation_dB": self.cloud_db,
            "scintillation_dB": self.scintillation_db,
            "total_atmospheric_attenuation_dB": self.total_db,
        }


def combine_total_attenuation_db(
    rain_db: float,
    gaseous_db: float,
    cloud_db: float,
    scintillation_db: float,
) -> float:
    """Combine attenuation mechanisms per ITU-R P.618-13 Section 2.5.

    Rain and cloud are correlated and add directly; scintillation is added in
    an RSS sense because it is statistically independent of the slow fades:

        A_total = A_gas + sqrt((A_rain + A_cloud)^2 + A_scint^2)
    """

    return gaseous_db + sqrt((rain_db + cloud_db) ** 2 + scintillation_db ** 2)


def total_slant_path_attenuation(
    frequency_ghz: float,
    elevation_deg: float,
    latitude_deg: float,
    station_height_km: float,
    exceedance_percent: float,
    rain_rate_001_mm_per_h: float,
    polarization_tilt_deg: float = 90.0,
    rain_height_override_km: float | None = None,
    pressure_hpa: float = 1013.25,
    temperature_c: float = 15.0,
    water_vapour_density_g_m3: float = 7.5,
    relative_humidity_percent: float = 60.0,
    columnar_liquid_water_kg_m2: float = 0.0,
    antenna_diameter_m: float | None = None,
    antenna_efficiency: float = 0.6,
    include_gaseous: bool = True,
    include_cloud: bool = True,
    include_scintillation: bool = True,
) -> AttenuationBreakdown:
    """Return the combined slant-path attenuation breakdown for one availability.

    This is the high-level entry point that ties together every ITU-R model in
    this module for a single time-percentage ``p``. It is the quantity that
    should be added to the clear-sky link budget as a real fade margin.
    """

    rain_db = rain_attenuation_db(
        frequency_ghz,
        elevation_deg,
        latitude_deg,
        station_height_km,
        rain_rate_001_mm_per_h,
        exceedance_percent,
        polarization_tilt_deg,
        rain_height_override_km,
    )

    gaseous_db = 0.0
    if include_gaseous:
        gaseous_db = gaseous_attenuation_db(
            frequency_ghz,
            elevation_deg,
            pressure_hpa,
            temperature_c,
            water_vapour_density_g_m3,
        )

    cloud_db = 0.0
    if include_cloud and columnar_liquid_water_kg_m2 > 0.0:
        cloud_db = cloud_attenuation_db(
            frequency_ghz, elevation_deg, columnar_liquid_water_kg_m2
        )

    scintillation_db = 0.0
    if include_scintillation and antenna_diameter_m is not None:
        scintillation_db = scintillation_fade_db(
            frequency_ghz,
            elevation_deg,
            antenna_diameter_m,
            antenna_efficiency,
            temperature_c,
            relative_humidity_percent,
            max(exceedance_percent, 0.01),
        )

    total_db = combine_total_attenuation_db(rain_db, gaseous_db, cloud_db, scintillation_db)
    return AttenuationBreakdown(
        exceedance_percent=exceedance_percent,
        rain_db=rain_db,
        gaseous_db=gaseous_db,
        cloud_db=cloud_db,
        scintillation_db=scintillation_db,
        total_db=total_db,
    )


def availability_attenuation_curve(
    frequency_ghz: float,
    elevation_deg: float,
    latitude_deg: float,
    station_height_km: float,
    rain_rate_001_mm_per_h: float,
    exceedance_percents: Sequence[float],
    **kwargs: object,
) -> list[AttenuationBreakdown]:
    """Return the combined attenuation breakdown for a series of time percentages.

    Useful for plotting the classic "attenuation vs percentage of time" (or,
    equivalently, vs availability) curve used to choose a design fade margin.
    """

    curve: list[AttenuationBreakdown] = []
    for p in exceedance_percents:
        curve.append(
            total_slant_path_attenuation(
                frequency_ghz,
                elevation_deg,
                latitude_deg,
                station_height_km,
                float(p),
                rain_rate_001_mm_per_h,
                **kwargs,  # type: ignore[arg-type]
            )
        )
    return curve
