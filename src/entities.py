# entities.py
"""Veri yapıları ve sınıf tanımlamaları.

Girdi ve çıktı parametrelerini Dataclass yapısında tutar.
Böylece konfigürasyon girdileri, analiz sonuçları ve opsiyonel modüllerin 
(ITU-R, DVB-S2 ACM vb.) taşıdığı değişkenler düzenli bir şekilde sistem içerisinde aktarılır.
"""

# ========================================================================
# 0.                             IMPORTS
# ========================================================================
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

from constants import SIDEREAL_DAY_HOURS
from itu_propagation import AttenuationBreakdown
from modcod import ModcodSelection


@dataclass(frozen=True)
class Location:
    """Geodetic location of a ground station.

    Parameters
    ----------
    name:
        Human-readable site name.
    latitude_deg:
        Geodetic latitude in degrees. North is positive.
    longitude_deg:
        Longitude in degrees. East is positive.
    altitude_km:
        Site altitude above mean sea level in kilometers.
    """

    name: str
    latitude_deg: float
    longitude_deg: float
    altitude_km: float = 0.0


@dataclass(frozen=True)
class GeoSatellite:
    """Simplified GEO satellite state.

    A perfectly geostationary satellite is located above the equator at a fixed
    longitude. Real GEO spacecraft are held inside a station-keeping box, so the
    apparent longitude, latitude, and radius vary slightly with time.
    """

    name: str
    longitude_deg: float
    latitude_deg: float = 0.0
    orbit_radius_km: Optional[float] = None


@dataclass(frozen=True)
class GeoApparentMotion:
    """Small deterministic apparent-motion model for a controlled GEO satellite.

    This is not a TLE/SGP4 orbit propagator. It is a transparent station-keeping
    box approximation that is useful for showing why a real GEO link is not
    perfectly constant in time.
    """

    enabled: bool = True
    duration_hours: float = 48.0
    step_minutes: float = 10.0
    period_hours: float = SIDEREAL_DAY_HOURS
    east_west_amplitude_deg: float = 0.06
    north_south_amplitude_deg: float = 0.04
    radial_amplitude_km: float = 40.0
    east_west_phase_deg: float = 0.0
    north_south_phase_deg: float = 90.0
    radial_phase_deg: float = 180.0


@dataclass(frozen=True)
class DishAntenna:
    """Parabolic dish antenna model.

    Either ``diameter_m`` or ``gain_dbi`` may be supplied. If ``gain_dbi`` is
    provided, the analyzer uses that datasheet value directly. Otherwise, gain
    is computed from diameter, frequency, and aperture efficiency.
    """

    name: str
    diameter_m: Optional[float] = None
    efficiency: float = 0.62
    gain_dbi: Optional[float] = None


@dataclass(frozen=True)
class LinkEndpoint:
    """Transmitting or receiving terminal used in one link direction.

    For a ground-station transmitter, use ``tx_power_dbw`` and an antenna. For a
    satellite downlink, it is often easier to use ``eirp_dbw_override`` from a
    coverage map. Receiver quality may be defined either with antenna + system
    temperature, or directly with ``G/T``.
    """

    name: str
    location: Optional[Location] = None
    antenna: Optional[DishAntenna] = None

    # Transmit-side parameters
    tx_power_dbw: Optional[float] = None
    eirp_dbw_override: Optional[float] = None
    tx_feeder_loss_db: float = 0.0

    # Receive-side parameters
    system_noise_temperature_k: Optional[float] = None
    g_over_t_db_per_k_override: Optional[float] = None
    rx_feeder_loss_db: float = 0.0

    notes: str = ""


@dataclass(frozen=True)
class LinkLosses:
    """Fixed clear-sky engineering losses, excluding free-space path loss.

    These are constant pointing/polarization/implementation allowances used by
    the clear-sky static link budget. They deliberately do NOT include any
    rain or atmospheric fade: ITU-R P.618/P.676/P.840 attenuation is applied
    only by the separate advanced ITU-R pipeline, never by the static baseline.
    """

    pointing_loss_db: float = 0.5
    polarization_loss_db: float = 0.3
    atmospheric_loss_db: float = 0.5
    implementation_loss_db: float = 0.0
    misc_loss_db: float = 0.0

    @property
    def total_loss_db(self) -> float:
        """Return the total fixed loss contribution in dB."""

        return (
            self.pointing_loss_db
            + self.polarization_loss_db
            + self.atmospheric_loss_db
            + self.implementation_loss_db
            + self.misc_loss_db
        )


@dataclass(frozen=True)
class LinkConfig:
    """Configuration of one one-way RF link."""

    name: str
    transmitter: LinkEndpoint
    receiver: LinkEndpoint
    frequency_hz: float
    bandwidth_hz: float
    bit_rate_bps: float
    losses: LinkLosses = field(default_factory=LinkLosses)
    required_ebn0_db: float = 7.0


@dataclass(frozen=True)
class InterferenceConfig:
    """Adjacent-satellite and intermodulation interference assumptions.

    The adjacent-satellite interference (ASI) model is intentionally simple:
    desired and adjacent carriers are compared through the earth-station antenna
    off-axis discrimination at the angular separation between GEO satellites.

    If a project has actual coordination data, replace the relative EIRP and C/I
    values with the specified numbers. The default values are teaching examples.
    """

    enabled: bool = True
    adjacent_satellite_longitudes_deg: Sequence[float] = (40.0, 44.0)
    adjacent_uplink_eirp_relative_db: float = 0.0
    adjacent_downlink_eirp_relative_db: float = 0.0
    adjacent_activity_factor_db: float = -3.0
    minimum_off_axis_angle_deg: float = 0.05
    uplink_c_i_override_db: Optional[float] = None
    downlink_c_i_override_db: Optional[float] = None
    imd_c_i_db: Optional[float] = 30.0


@dataclass(frozen=True)
class DynamicNoiseConfig:
    """Optional elevation- and rain-dependent receive system temperature model.

    A receive antenna looking at low elevation sees more atmosphere. Rain adds a
    second effect: it attenuates the wanted carrier and emits thermal noise. This
    model is simplified but physically interpretable.
    """

    enabled: bool = True
    receiver_internal_noise_k: float = 90.0
    spillover_noise_k: float = 20.0
    clear_sky_base_noise_k: float = 12.0
    low_elevation_extra_noise_k: float = 35.0
    rain_emission_temperature_k: float = 275.0
    minimum_elevation_deg: float = 3.0


@dataclass(frozen=True)
class RainOutageConfig:
    """Simplified stochastic rain-fade model for availability/outage studies.

    This is not an official ITU-R P.618 implementation. It is an educational
    Monte-Carlo-style weather generator that can demonstrate availability,
    outage hours, rain attenuation, and sky-noise increase.
    """

    enabled: bool = True
    random_seed: int = 451
    samples_per_year: int = 8760
    light_rain_probability: float = 0.020
    moderate_rain_probability: float = 0.006
    heavy_rain_probability: float = 0.001
    clear_attenuation_max_db: float = 0.15
    light_rain_attenuation_range_db: tuple[float, float] = (0.5, 2.5)
    moderate_rain_attenuation_range_db: tuple[float, float] = (2.5, 7.0)
    heavy_rain_attenuation_range_db: tuple[float, float] = (7.0, 18.0)
    uplink_frequency_scaling_exponent: float = 1.15
    downlink_frequency_scaling_exponent: float = 1.00


@dataclass(frozen=True)
class ITUPropagationConfig:
    """Standards-based ITU-R slant-path attenuation inputs .

    Unlike :class:`RainOutageConfig`, which is an educational Monte-Carlo
    weather generator, this configuration drives the deterministic ITU-R
    Recommendations implemented in ``itu_propagation.py``:

    * ITU-R P.618-13 rain attenuation A(p),
    * ITU-R P.676-12 gaseous (oxygen + water-vapour) attenuation,
    * ITU-R P.840-8 cloud-liquid-water attenuation,
    * ITU-R P.618-13 tropospheric scintillation.

    The base course assignment intentionally runs the static MATLAB analyzer
    with P.618 losses disabled. keeps that clean static link budget and adds
    this separate layer so the link can be studied against an availability
    target. It is a self-contained engineering implementation; site-specific
    accuracy requires replacing the example inputs with mapped/measured values.
    """

    enabled: bool = True

    # --- Rain (ITU-R P.618 / P.837 / P.838 / P.839) ---
    rain_rate_001_mm_per_h: float = 42.0  # R_0.01 for the site (ITU-R P.837 map).
    polarization_tilt_deg: float = 90.0  # 90 deg = vertical linear polarization.
    rain_height_h0_override_km: Optional[float] = None  # Measured 0 deg C isotherm.

    # --- Atmosphere (ITU-R P.676 / P.840 / P.453) ---
    surface_pressure_hpa: float = 1013.25
    surface_temperature_c: float = 15.0
    water_vapour_density_g_m3: float = 7.5
    relative_humidity_percent: float = 60.0
    columnar_liquid_water_kg_m2: float = 0.6  # Cloud liquid water for the target p%.

    # --- Mechanism switches ---
    include_gaseous: bool = True
    include_cloud: bool = True
    include_scintillation: bool = True

    # --- Availability targets ---
    design_availability_percent: float = 99.9  # Exceedance p = 100 - this.
    availability_curve_percents: Sequence[float] = (
        0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 5.0,
    )

    @property
    def design_exceedance_percent(self) -> float:
        """Return the design time-percentage ``p`` from the availability target."""

        return 100.0 - self.design_availability_percent


@dataclass(frozen=True)
class ModcodConfig:
    """DVB-S2 adaptive coding-and-modulation (ACM) configuration ."""

    enabled: bool = True
    rolloff_factor: float = 0.20
    implementation_margin_db: float = 1.0


@dataclass(frozen=True)
class DigitalLinkConfig:
    """Digital-layer assumptions for modulation, FEC, BER, and capacity metrics.

    The RF link budget produces Eb/N0. This configuration maps that physical
    energy ratio into bit-error-rate and information-capacity quantities.

    Notes
    -----
    * The default BER model is uncoded coherent BPSK/QPSK in AWGN.
    * FEC is represented by an equivalent coding gain, not by a full decoder
      simulation. This is appropriate for a transparent first engineering pass.
    * ``bit_rate_bps`` in the RF link config is interpreted as information bit
      rate. The coded channel bit rate is therefore information_rate/code_rate.
    """

    enabled: bool = True
    modulation: str = "QPSK"
    code_rate: float = 0.75
    coding_gain_db: float = 3.0
    rolloff_factor: float = 0.35
    target_ber: float = 1.0e-6
    uncoded_required_ebn0_db: float = 7.0

    @property
    def required_coded_ebn0_db(self) -> float:
        """Return the Eb/N0 threshold after applying the coding gain."""

        return self.uncoded_required_ebn0_db - self.coding_gain_db


@dataclass(frozen=True)
class ScenarioConfig:
    """Complete bent-pipe scenario: GS1 -> GEO satellite -> GS2."""

    name: str
    satellite: GeoSatellite
    uplink: LinkConfig
    downlink: LinkConfig
    required_end_to_end_ebn0_db: float = 7.0
    apparent_motion: GeoApparentMotion = field(default_factory=GeoApparentMotion)
    interference: InterferenceConfig = field(default_factory=InterferenceConfig)
    dynamic_noise: DynamicNoiseConfig = field(default_factory=DynamicNoiseConfig)
    rain_outage: RainOutageConfig = field(default_factory=RainOutageConfig)
    digital: DigitalLinkConfig = field(default_factory=DigitalLinkConfig)
    itu_propagation: ITUPropagationConfig = field(default_factory=ITUPropagationConfig)
    modcod: ModcodConfig = field(default_factory=ModcodConfig)


@dataclass(frozen=True)
class LinkEnvironment:
    """Extra time/weather inputs applied to one instantaneous link calculation.

    ``rain_attenuation_db`` is the attenuation that reduces the wanted carrier
    on the path (in this can be the full ITU-R atmospheric total). The
    optional ``emission_attenuation_db`` is the *absorptive* part used to raise
    the receive sky-noise temperature; when ``None`` the model falls back to
    ``rain_attenuation_db``. Separating them lets a refractive impairment such
    as scintillation degrade the carrier without spuriously adding sky noise.
    """

    rain_attenuation_db: float = 0.0
    dynamic_tsys_k: Optional[float] = None
    weather_label: str = "clear"
    emission_attenuation_db: Optional[float] = None

    @property
    def noise_emission_attenuation_db(self) -> float:
        """Return the absorptive attenuation that drives sky-noise emission."""

        if self.emission_attenuation_db is not None:
            return self.emission_attenuation_db
        return self.rain_attenuation_db


@dataclass(frozen=True)
class LinkGeometry:
    """Computed geometry between one ground station and one satellite state."""

    ground_station_name: str
    satellite_name: str
    slant_range_km: float
    elevation_deg: float
    azimuth_deg: float
    central_angle_deg: float
    satellite_longitude_deg: float
    satellite_latitude_deg: float
    satellite_radius_km: float


@dataclass(frozen=True)
class LinkBudgetResult:
    """Computed link-budget result for one one-way link."""

    link_name: str
    frequency_hz: float
    bandwidth_hz: float
    bit_rate_bps: float
    range_km: float
    elevation_deg: float
    tx_gain_dbi: Optional[float]
    rx_gain_dbi: Optional[float]
    eirp_dbw: float
    g_over_t_db_per_k: float
    system_noise_temperature_k: Optional[float]
    free_space_loss_db: float
    fixed_losses_db: float
    rain_attenuation_db: float
    total_losses_db: float
    cn0_dbhz: float
    cn_db: float
    ebn0_db: float
    required_ebn0_db: float
    margin_db: float
    carrier_power_dbw: Optional[float]

    def to_dict(self) -> dict[str, float | str | None]:
        """Return the key link-budget results as a CSV-friendly mapping."""

        return {
            "link": self.link_name,
            "frequency_GHz": self.frequency_hz / 1.0e9,
            "bandwidth_MHz": self.bandwidth_hz / 1.0e6,
            "bit_rate_Mbps": self.bit_rate_bps / 1.0e6,
            "range_km": self.range_km,
            "elevation_deg": self.elevation_deg,
            "tx_gain_dBi": self.tx_gain_dbi,
            "rx_gain_dBi": self.rx_gain_dbi,
            "EIRP_dBW": self.eirp_dbw,
            "G_over_T_dB_per_K": self.g_over_t_db_per_k,
            "Tsys_K": self.system_noise_temperature_k,
            "FSPL_dB": self.free_space_loss_db,
            "fixed_losses_dB": self.fixed_losses_db,
            "rain_attenuation_dB": self.rain_attenuation_db,
            "total_losses_dB": self.total_losses_db,
            "C_N0_dBHz": self.cn0_dbhz,
            "C_N_dB": self.cn_db,
            "Eb_N0_dB": self.ebn0_db,
            "required_Eb_N0_dB": self.required_ebn0_db,
            "margin_dB": self.margin_db,
            "carrier_power_dBW": self.carrier_power_dbw,
        }

@dataclass(frozen=True)
class InterferenceResult:
    """Computed C/I values for ASI and optional intermodulation."""

    uplink_asi_c_i_db: Optional[float]
    downlink_asi_c_i_db: Optional[float]
    imd_c_i_db: Optional[float]
    dominant_interference: str

    def to_dict(self) -> dict[str, float | str | None]:
        """Return interference terms in a compact export-friendly format."""

        return {
            "uplink_ASI_C_I_dB": self.uplink_asi_c_i_db,
            "downlink_ASI_C_I_dB": self.downlink_asi_c_i_db,
            "IMD_C_I_dB": self.imd_c_i_db,
            "dominant_interference": self.dominant_interference,
        }

@dataclass(frozen=True)
class DigitalMetrics:
    """Digital communication metrics derived from final Eb/N0 and C/N.

    These values connect the analog/RF link-budget result to BER, FEC margin,
    spectral efficiency, occupied bandwidth, and Shannon-Hartley capacity.
    """

    modulation: str
    bits_per_symbol: int
    code_rate: float
    coding_gain_db: float
    rolloff_factor: float
    target_ber: float
    information_bit_rate_bps: float
    coded_channel_bit_rate_bps: float
    symbol_rate_baud: float
    estimated_occupied_bandwidth_hz: float
    allocated_bandwidth_hz: float
    information_spectral_efficiency_bps_hz: float
    coded_spectral_efficiency_bps_hz: float
    uncoded_required_ebn0_db: float
    coded_required_ebn0_db: float
    noise_only_ber_uncoded: float
    interference_ber_uncoded: float
    noise_only_ber_with_coding_gain: float
    interference_ber_with_coding_gain: float
    digital_margin_noise_only_db: float
    digital_margin_with_interference_db: float
    shannon_capacity_noise_only_bps: float
    shannon_capacity_with_interference_bps: float
    shannon_capacity_margin_noise_only_bps: float
    shannon_capacity_margin_with_interference_bps: float
    shannon_ebn0_limit_db: float
    gap_to_shannon_noise_only_db: float
    gap_to_shannon_with_interference_db: float

    def to_dict(self) -> dict[str, float | str | None]:
        """Return digital-layer metrics in a CSV-friendly mapping."""

        return {
            "modulation": self.modulation,
            "bits_per_symbol": self.bits_per_symbol,
            "code_rate": self.code_rate,
            "coding_gain_dB": self.coding_gain_db,
            "rolloff_factor": self.rolloff_factor,
            "target_BER": self.target_ber,
            "information_bit_rate_Mbps": self.information_bit_rate_bps / 1.0e6,
            "coded_channel_bit_rate_Mbps": self.coded_channel_bit_rate_bps / 1.0e6,
            "symbol_rate_Mbaud": self.symbol_rate_baud / 1.0e6,
            "estimated_occupied_bandwidth_MHz": self.estimated_occupied_bandwidth_hz / 1.0e6,
            "allocated_bandwidth_MHz": self.allocated_bandwidth_hz / 1.0e6,
            "information_spectral_efficiency_bps_per_Hz": self.information_spectral_efficiency_bps_hz,
            "coded_spectral_efficiency_bps_per_Hz": self.coded_spectral_efficiency_bps_hz,
            "uncoded_required_Eb_N0_dB": self.uncoded_required_ebn0_db,
            "coded_required_Eb_N0_dB": self.coded_required_ebn0_db,
            "BER_noise_only_uncoded": self.noise_only_ber_uncoded,
            "BER_with_interference_uncoded": self.interference_ber_uncoded,
            "BER_noise_only_with_coding_gain": self.noise_only_ber_with_coding_gain,
            "BER_with_interference_with_coding_gain": self.interference_ber_with_coding_gain,
            "digital_margin_noise_only_dB": self.digital_margin_noise_only_db,
            "digital_margin_with_interference_dB": self.digital_margin_with_interference_db,
            "shannon_capacity_noise_only_Mbps": self.shannon_capacity_noise_only_bps / 1.0e6,
            "shannon_capacity_with_interference_Mbps": self.shannon_capacity_with_interference_bps / 1.0e6,
            "shannon_capacity_margin_noise_only_Mbps": self.shannon_capacity_margin_noise_only_bps / 1.0e6,
            "shannon_capacity_margin_with_interference_Mbps": self.shannon_capacity_margin_with_interference_bps / 1.0e6,
            "shannon_Eb_N0_limit_dB": self.shannon_ebn0_limit_db,
            "gap_to_shannon_noise_only_dB": self.gap_to_shannon_noise_only_db,
            "gap_to_shannon_with_interference_dB": self.gap_to_shannon_with_interference_db,
        }

@dataclass(frozen=True)
class ScenarioResult:
    """Combined result of the uplink/downlink budgets and interference budget."""

    scenario_name: str
    uplink_geometry: LinkGeometry
    downlink_geometry: LinkGeometry
    uplink: LinkBudgetResult
    downlink: LinkBudgetResult
    combined_cn0_dbhz: float
    combined_cn_db: float
    combined_ebn0_db: float
    combined_margin_db: float
    interference: InterferenceResult
    combined_cni_db: float
    combined_ebn0_ni_db: float
    combined_margin_ni_db: float
    digital: Optional[DigitalMetrics] = None

    def to_summary_dict(self) -> dict[str, float | str | None]:
        """Return a compact summary of the full scenario result."""

        data: dict[str, float | str | None] = {
            "scenario": self.scenario_name,
            "uplink_CN0_dBHz": self.uplink.cn0_dbhz,
            "downlink_CN0_dBHz": self.downlink.cn0_dbhz,
            "combined_CN0_dBHz_noise_only": self.combined_cn0_dbhz,
            "combined_CN_dB_noise_only": self.combined_cn_db,
            "combined_Eb_N0_dB_noise_only": self.combined_ebn0_db,
            "combined_margin_dB_noise_only": self.combined_margin_db,
            "combined_C_NI_dB": self.combined_cni_db,
            "combined_Eb_NI_dB": self.combined_ebn0_ni_db,
            "combined_margin_dB_with_interference": self.combined_margin_ni_db,
        }
        data.update(self.interference.to_dict())
        if self.digital is not None:
            data.update(self.digital.to_dict())
        return data


@dataclass(frozen=True)
class ITUPropagationResult:
    """Standards-based slant-path attenuation result for one availability point.

    Holds the per-direction ITU-R attenuation breakdowns and the resulting
    scenario link budget after those fades are applied, plus the optional
    DVB-S2 ACM selection for the degraded downlink.
    """

    design_availability_percent: float
    design_exceedance_percent: float
    uplink_breakdown: AttenuationBreakdown
    downlink_breakdown: AttenuationBreakdown
    faded_result: "ScenarioResult"
    uplink_modcod: Optional[ModcodSelection] = None
    downlink_modcod: Optional[ModcodSelection] = None

    def to_dict(self) -> dict[str, float | str | None]:
        """Return a compact CSV-friendly summary of the faded link."""

        data: dict[str, float | str | None] = {
            "design_availability_percent": self.design_availability_percent,
            "design_exceedance_percent": self.design_exceedance_percent,
            "uplink_total_attenuation_dB": self.uplink_breakdown.total_db,
            "uplink_rain_attenuation_dB": self.uplink_breakdown.rain_db,
            "uplink_gaseous_attenuation_dB": self.uplink_breakdown.gaseous_db,
            "uplink_cloud_attenuation_dB": self.uplink_breakdown.cloud_db,
            "uplink_scintillation_dB": self.uplink_breakdown.scintillation_db,
            "downlink_total_attenuation_dB": self.downlink_breakdown.total_db,
            "downlink_rain_attenuation_dB": self.downlink_breakdown.rain_db,
            "downlink_gaseous_attenuation_dB": self.downlink_breakdown.gaseous_db,
            "downlink_cloud_attenuation_dB": self.downlink_breakdown.cloud_db,
            "downlink_scintillation_dB": self.downlink_breakdown.scintillation_db,
            "faded_combined_Eb_N0_dB_noise_only": self.faded_result.combined_ebn0_db,
            "faded_combined_margin_dB_noise_only": self.faded_result.combined_margin_db,
            "faded_combined_Eb_NI_dB": self.faded_result.combined_ebn0_ni_db,
            "faded_combined_margin_dB_with_interference": self.faded_result.combined_margin_ni_db,
        }
        if self.downlink_modcod is not None:
            for key, value in self.downlink_modcod.to_dict().items():
                data[f"downlink_{key}"] = value
        return data


@dataclass(frozen=True)
class TimeVaryingSample:
    """One time sample of apparent GEO motion and link budget."""

    time_hours: float
    satellite: GeoSatellite
    result: ScenarioResult
    weather_label: str = "clear"
    uplink_rain_attenuation_db: float = 0.0
    downlink_rain_attenuation_db: float = 0.0

    def to_dict(self) -> dict[str, float | str | None]:
        """Return one time sample as a CSV-friendly mapping."""

        data: dict[str, float | str | None] = {
            "time_hours": self.time_hours,
            "weather": self.weather_label,
            "satellite_longitude_deg": self.satellite.longitude_deg,
            "satellite_latitude_deg": self.satellite.latitude_deg,
            "satellite_radius_km": self.satellite.orbit_radius_km or 0.0,
            "uplink_range_km": self.result.uplink.range_km,
            "downlink_range_km": self.result.downlink.range_km,
            "uplink_elevation_deg": self.result.uplink.elevation_deg,
            "downlink_elevation_deg": self.result.downlink.elevation_deg,
            "uplink_FSPL_dB": self.result.uplink.free_space_loss_db,
            "downlink_FSPL_dB": self.result.downlink.free_space_loss_db,
            "uplink_rain_attenuation_dB": self.uplink_rain_attenuation_db,
            "downlink_rain_attenuation_dB": self.downlink_rain_attenuation_db,
            "downlink_Tsys_K": self.result.downlink.system_noise_temperature_k,
            "uplink_Eb_N0_dB": self.result.uplink.ebn0_db,
            "downlink_Eb_N0_dB": self.result.downlink.ebn0_db,
            "combined_Eb_N0_dB_noise_only": self.result.combined_ebn0_db,
            "combined_margin_dB_noise_only": self.result.combined_margin_db,
            "combined_Eb_NI_dB": self.result.combined_ebn0_ni_db,
            "combined_margin_dB_with_interference": self.result.combined_margin_ni_db,
            "uplink_ASI_C_I_dB": self.result.interference.uplink_asi_c_i_db,
            "downlink_ASI_C_I_dB": self.result.interference.downlink_asi_c_i_db,
            "IMD_C_I_dB": self.result.interference.imd_c_i_db,
        }
        if self.result.digital is not None:
            data.update({
                "BER_with_interference_uncoded": self.result.digital.interference_ber_uncoded,
                "BER_with_interference_with_coding_gain": self.result.digital.interference_ber_with_coding_gain,
                "shannon_capacity_with_interference_Mbps": self.result.digital.shannon_capacity_with_interference_bps / 1.0e6,
                "shannon_capacity_margin_with_interference_Mbps": self.result.digital.shannon_capacity_margin_with_interference_bps / 1.0e6,
            })
        return data