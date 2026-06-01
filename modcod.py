# modcod.py
"""DVB-S2 adaptive coding and modulation (ACM) support for the V5 analyzer.

A real broadcast/VSAT bent-pipe link rarely runs a single fixed modulation. The
DVB-S2 standard (ETSI EN 302 307) defines a ladder of modulation-and-coding
points (MODCODs). The receiver continuously reports its measured carrier-to-
noise ratio, and the gateway selects the most spectrally efficient MODCOD that
still closes the link with margin. This module provides:

* the standard DVB-S2 MODCOD table (modulation, code rate, spectral efficiency,
  and the required Es/N0 for quasi-error-free reception on an AWGN channel),
* a selector that picks the best MODCOD for a measured C/N,
* a net-throughput estimate for the selected MODCOD.

The required Es/N0 values are the published EN 302 307 reference figures for the
normal FECFRAME (64 800 bits) at quasi-error-free (QEF) operation, defined as a
post-FEC packet error rate of about 1e-7.

Reference
---------
ETSI EN 302 307-1: Digital Video Broadcasting (DVB); Second generation framing
structure, channel coding and modulation systems (DVB-S2).
"""

# ========================================================================
# 0.                             IMPORTS
# ========================================================================
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ========================================================================
# 1.                       MODCOD DEFINITION
# ========================================================================
@dataclass(frozen=True)
class Modcod:
    """One DVB-S2 modulation-and-coding operating point.

    Attributes
    ----------
    modulation:
        Constellation name (QPSK, 8PSK, 16APSK, 32APSK).
    code_rate:
        LDPC inner code rate as a fraction (e.g. 3/4 = 0.75).
    spectral_efficiency_bps_hz:
        Nominal net spectral efficiency (information bit/s per Hz of symbol
        rate), i.e. ``log2(M) * code_rate`` reduced by framing overhead, as
        tabulated in EN 302 307.
    required_esn0_db:
        Es/N0 (equivalently the symbol-rate C/N) required for quasi-error-free
        reception on an AWGN channel.
    """

    modulation: str
    code_rate: float
    spectral_efficiency_bps_hz: float
    required_esn0_db: float

    @property
    def name(self) -> str:
        """Return a compact human-readable identifier such as ``8PSK 3/4``."""

        # Recover the nearest simple fraction label for display.
        approx = {
            0.25: "1/4", 0.3333: "1/3", 0.4: "2/5", 0.5: "1/2", 0.6: "3/5",
            0.6667: "2/3", 0.75: "3/4", 0.8: "4/5", 0.8333: "5/6",
            0.8889: "8/9", 0.9: "9/10",
        }
        label = min(approx.items(), key=lambda kv: abs(kv[0] - self.code_rate))[1]
        return f"{self.modulation} {label}"


# ========================================================================
# 2.                  STANDARD DVB-S2 MODCOD TABLE
# ========================================================================
# (modulation, code_rate, spectral_efficiency, required Es/N0 dB @ QEF, AWGN)
DVB_S2_MODCODS: tuple[Modcod, ...] = (
    Modcod("QPSK", 1 / 4, 0.490243, -2.35),
    Modcod("QPSK", 1 / 3, 0.656448, -1.24),
    Modcod("QPSK", 2 / 5, 0.789412, -0.30),
    Modcod("QPSK", 1 / 2, 0.988858, 1.00),
    Modcod("QPSK", 3 / 5, 1.188304, 2.23),
    Modcod("QPSK", 2 / 3, 1.322253, 3.10),
    Modcod("QPSK", 3 / 4, 1.487473, 4.03),
    Modcod("QPSK", 4 / 5, 1.587196, 4.68),
    Modcod("QPSK", 5 / 6, 1.654663, 5.18),
    Modcod("QPSK", 8 / 9, 1.766451, 6.20),
    Modcod("QPSK", 9 / 10, 1.788612, 6.42),
    Modcod("8PSK", 3 / 5, 1.779991, 5.50),
    Modcod("8PSK", 2 / 3, 1.980636, 6.62),
    Modcod("8PSK", 3 / 4, 2.228124, 7.91),
    Modcod("8PSK", 5 / 6, 2.478562, 9.35),
    Modcod("8PSK", 8 / 9, 2.646012, 10.69),
    Modcod("8PSK", 9 / 10, 2.679207, 10.98),
    Modcod("16APSK", 2 / 3, 2.637201, 8.97),
    Modcod("16APSK", 3 / 4, 2.966728, 10.21),
    Modcod("16APSK", 4 / 5, 3.165623, 11.03),
    Modcod("16APSK", 5 / 6, 3.300184, 11.61),
    Modcod("16APSK", 8 / 9, 3.523143, 12.89),
    Modcod("16APSK", 9 / 10, 3.567342, 13.13),
    Modcod("32APSK", 3 / 4, 3.703295, 12.73),
    Modcod("32APSK", 4 / 5, 3.951571, 13.64),
    Modcod("32APSK", 5 / 6, 4.119540, 14.28),
    Modcod("32APSK", 8 / 9, 4.397854, 15.69),
    Modcod("32APSK", 9 / 10, 4.453027, 16.05),
)


# ========================================================================
# 3.                   ACM SELECTION AND THROUGHPUT
# ========================================================================
@dataclass(frozen=True)
class ModcodSelection:
    """Result of selecting the best DVB-S2 MODCOD for a measured C/N."""

    available_esn0_db: float
    implementation_margin_db: float
    selected: Optional[Modcod]
    link_margin_db: Optional[float]
    spectral_efficiency_bps_hz: float
    net_throughput_bps: float

    def to_dict(self) -> dict[str, float | str | None]:
        """Return the ACM selection as a CSV-friendly mapping."""

        return {
            "available_Es_N0_dB": self.available_esn0_db,
            "implementation_margin_dB": self.implementation_margin_db,
            "selected_MODCOD": self.selected.name if self.selected else "link closed: none",
            "selected_required_Es_N0_dB": self.selected.required_esn0_db if self.selected else None,
            "selected_spectral_efficiency_bps_per_Hz": self.spectral_efficiency_bps_hz,
            "ACM_link_margin_dB": self.link_margin_db,
            "net_throughput_Mbps": self.net_throughput_bps / 1.0e6,
        }


def symbol_rate_baud(bandwidth_hz: float, rolloff_factor: float) -> float:
    """Return the usable symbol rate for an allocated bandwidth and rolloff.

    ``R_s = B / (1 + rolloff)`` for a root-raised-cosine shaped carrier.
    """

    if bandwidth_hz <= 0.0:
        raise ValueError("Bandwidth must be positive.")
    if rolloff_factor < 0.0:
        raise ValueError("Rolloff factor must be non-negative.")
    return bandwidth_hz / (1.0 + rolloff_factor)


def select_best_modcod(
    available_esn0_db: float,
    bandwidth_hz: float,
    rolloff_factor: float,
    implementation_margin_db: float = 1.0,
) -> ModcodSelection:
    """Select the most efficient DVB-S2 MODCOD that closes the link.

    The function walks the standard MODCOD ladder and returns the highest
    spectral-efficiency point whose required Es/N0 (plus an implementation
    margin) is met by the available Es/N0. The corresponding net throughput is
    ``spectral_efficiency * symbol_rate``.

    Parameters
    ----------
    available_esn0_db:
        Measured/computed Es/N0 (symbol-rate C/N) at the receiver in dB.
    bandwidth_hz:
        Allocated transponder/carrier bandwidth in Hz.
    rolloff_factor:
        Root-raised-cosine rolloff (e.g. 0.20, 0.25, 0.35).
    implementation_margin_db:
        Extra dB required above the theoretical AWGN threshold to account for
        modem implementation losses (typically ~0.8-1.5 dB).
    """

    r_s = symbol_rate_baud(bandwidth_hz, rolloff_factor)
    usable = available_esn0_db - implementation_margin_db

    selected: Optional[Modcod] = None
    for modcod in DVB_S2_MODCODS:
        if modcod.required_esn0_db <= usable:
            if selected is None or modcod.spectral_efficiency_bps_hz > selected.spectral_efficiency_bps_hz:
                selected = modcod

    if selected is None:
        return ModcodSelection(
            available_esn0_db=available_esn0_db,
            implementation_margin_db=implementation_margin_db,
            selected=None,
            link_margin_db=None,
            spectral_efficiency_bps_hz=0.0,
            net_throughput_bps=0.0,
        )

    return ModcodSelection(
        available_esn0_db=available_esn0_db,
        implementation_margin_db=implementation_margin_db,
        selected=selected,
        link_margin_db=available_esn0_db - implementation_margin_db - selected.required_esn0_db,
        spectral_efficiency_bps_hz=selected.spectral_efficiency_bps_hz,
        net_throughput_bps=selected.spectral_efficiency_bps_hz * r_s,
    )


def esn0_from_cn0_db(cn0_dbhz: float, bandwidth_hz: float, rolloff_factor: float) -> float:
    """Convert C/N0 [dB-Hz] to symbol-rate Es/N0 [dB] for the usable symbol rate.

    ``Es/N0 = C/N0 - 10 log10(R_s)``, where ``R_s = B / (1 + rolloff)``.
    """

    from math import log10

    r_s = symbol_rate_baud(bandwidth_hz, rolloff_factor)
    return cn0_dbhz - 10.0 * log10(r_s)
