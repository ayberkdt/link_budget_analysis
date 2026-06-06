# constants.py
"""Projede kullanılan fiziksel sabitler ve birim dönüştürücüler.

Hesaplamaların doğruluğunu garanti altına almak için tüm temel sabitler tek bir 
yerde tanımlanmış ve projenin geri kalanında buradan çağırılmıştır.
"""

# ========================================================================
# 0.                             IMPORTS 
# ========================================================================
from __future__ import annotations

from math import log10, pi



# ========================================================================
# 1.                         UNIVERSAL CONSTANTS 
# ========================================================================
SPEED_OF_LIGHT_M_PER_S: float = 299_792_458.0
BOLTZMANN_J_PER_K: float = 1.380_649e-23

# -10*log10(k), where k is Boltzmann's constant in J/K.
# Used in: C/N0 [dB-Hz] = EIRP + G/T - losses - 10log10(k)
BOLTZMANN_DB_CONSTANT: float = -10.0 * log10(BOLTZMANN_J_PER_K)  # ~228.6 dB



# ========================================================================
# 2.                         EARTH/GEO CONSTANTS 
# ========================================================================
EARTH_EQUATORIAL_RADIUS_KM: float = 6_378.137
GEO_ORBIT_RADIUS_KM: float = 42_164.0
GEO_ALTITUDE_KM: float = GEO_ORBIT_RADIUS_KM - EARTH_EQUATORIAL_RADIUS_KM
SIDEREAL_DAY_HOURS: float = 23.934_469_6


# ========================================================================
# 3.                         THERMAL ENV. Constants 
# ========================================================================
COSMIC_BACKGROUND_TEMPERATURE_K: float = 2.725
ATMOSPHERIC_EFFECTIVE_TEMPERATURE_K: float = 275.0
STANDARD_AMBIENT_TEMPERATURE_K: float = 290.0



# ========================================================================
# 4.                       UNIT CONVERSION HELPERS
# ========================================================================
DEG_TO_RAD: float = pi / 180.0
RAD_TO_DEG: float = 180.0 / pi
GHZ: float = 1.0e9
MHZ: float = 1.0e6
KHZ: float = 1.0e3


# ========================================================================
# 5.                  PROPAGATION & ENGINEERING CONSTANTS
# ========================================================================
EFFECTIVE_EARTH_RADIUS_KM: float = 8_500.0
MINIMUM_VALID_ELEVATION_DEG: float = 5.0
FSPL_CONSTANT: float = 92.45
PARABOLIC_BEAMWIDTH_FACTOR: float = 70.0
SIDELOBE_ENVELOPE_CONSTANT_A: float = 32.0
SIDELOBE_ENVELOPE_CONSTANT_B: float = 25.0
SCINTILLATION_TURBULENT_LAYER_HEIGHT_M: float = 1000.0

