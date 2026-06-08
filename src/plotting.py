# plotting.py
"""Grafik ve görselleştirme fonksiyonları (Matplotlib).

Bu modül, proje raporunda kullanılacak yüksek kaliteli 2B kontur haritalarını
ve ileri düzey (Monte-Carlo, yörünge hareketi vb.) simülasyon grafiklerini çizer.
Çizimlerin raporlarda uyumlu durması için tek bir ortak format (font, renk vb.) 
kullanılmıştır. Kapalı olan (enabled=False) analizlerin grafikleri çizilmez.
"""

# ========================================================================
# 0.                             IMPORTS
# ========================================================================
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import TwoSlopeNorm
from matplotlib.lines import Line2D

if __package__:
    from . import itu_propagation as itu
    from .calculations import (
        calculate_asi_ci_grid,
        calculate_dynamic_system_noise_temperature_k,
        calculate_geo_link_geometry,
        calculate_scenario,
        calculate_scenario_with_itu,
        modulation_bits_per_symbol,
        shannon_capacity_bps,
        theoretical_ber_awgn,
        watts_to_dbw,
    )
    from .constants import GHZ, MHZ
    from .entities import ITUPropagationResult, ScenarioConfig, TimeVaryingSample
    from .modcod import DVB_S2_MODCODS
else:
    import itu_propagation as itu
    from calculations import (
        calculate_asi_ci_grid,
        calculate_dynamic_system_noise_temperature_k,
        calculate_geo_link_geometry,
        calculate_scenario,
        calculate_scenario_with_itu,
        modulation_bits_per_symbol,
        shannon_capacity_bps,
        theoretical_ber_awgn,
        watts_to_dbw,
    )
    from constants import GHZ, MHZ
    from entities import ITUPropagationResult, ScenarioConfig, TimeVaryingSample
    from modcod import DVB_S2_MODCODS


# ========================================================================
# 1.                       CENTRALIZED PLOT STYLE
# ========================================================================
FIGURE_DPI = 600          # Export resolution for report raster figures.
EXPORT_PDF = True         # Also save a vector PDF with the same basename.

# Typography (points) - sized for report figures
TITLE_FONTSIZE = 14
LABEL_FONTSIZE = 12
TICK_FONTSIZE = 10.5
LEGEND_FONTSIZE = 10.5
ANNOTATION_FONTSIZE = 9.5
CONTOUR_LABEL_SIZE = 9
COLORBAR_LABEL_SIZE = 12

# Lines and markers.
LINE_WIDTH = 2.0
THIN_LINE_WIDTH = 1.2
MARKER_SIZE = 5.0
GRID_ALPHA = 0.45

# Default figure sizes (inches) - Golden ratio inspired where applicable.
FIGSIZE_CONTOUR = (10.0, 7.0)
FIGSIZE_LINE = (8.0, 5.0)
FIGSIZE_BAR = (8.0, 5.0)
FIGSIZE_SQUARE = (6.0, 6.0)
FIGSIZE_WIDE = (9.0, 3.5)

# Colormaps and key colors.
SEQUENTIAL_CMAP = "viridis"
DIVERGING_CMAP = "RdBu_r"
BASELINE_COLOR = "#c0392b"
THRESHOLD_COLOR = "#2c3e50"     # Dark slate for thresholds.
WARNING_COLOR = "#b45f06"
CONTOUR_LINE_COLOR = "#111111"
CONTOUR_LABEL_BOX = {
    "boxstyle": "round,pad=0.14",
    "facecolor": "white",
    "edgecolor": "none",
    "alpha": 0.78,
}

_RC_PARAMS = {
    "figure.facecolor": "white",
    "axes.facecolor": "#fdfdfd",
    "savefig.facecolor": "white",
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.05,
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif", "serif"],
    "mathtext.fontset": "stix",
    "font.size": TICK_FONTSIZE,
    "axes.titlesize": TITLE_FONTSIZE,
    "axes.titleweight": "bold",
    "axes.titlepad": 12,
    "axes.labelsize": LABEL_FONTSIZE,
    "axes.labelpad": 8,
    "axes.edgecolor": "#333333",
    "axes.linewidth": 1.2,
    "axes.axisbelow": True,
    "xtick.labelsize": TICK_FONTSIZE,
    "ytick.labelsize": TICK_FONTSIZE,
    "xtick.major.size": 5,
    "ytick.major.size": 5,
    "xtick.minor.size": 3,
    "ytick.minor.size": 3,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.top": False,
    "ytick.right": False,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "legend.fontsize": LEGEND_FONTSIZE,
    "legend.framealpha": 0.96,
    "legend.edgecolor": "#dddddd",
    "legend.fancybox": False,
    "lines.linewidth": LINE_WIDTH,
    "grid.alpha": GRID_ALPHA,
    "grid.linewidth": 0.7,
    "grid.linestyle": ":",
    "grid.color": "#b0b0b0",
}


def _apply_style() -> None:
    """Apply the centralized Matplotlib style to all subsequent figures."""

    plt.rcParams.update(_RC_PARAMS)


_apply_style()


# ========================================================================
# 2.                       SHARED FIGURE HELPERS
# ========================================================================
def _prepare_output_dir(output_dir: Path) -> None:
    """Create the output directory when it does not already exist."""

    output_dir.mkdir(parents=True, exist_ok=True)


def _save_figure(fig: plt.Figure, png_path: Path) -> Path:
    """Finalize, save (PNG + optional PDF), and close a figure; return the PNG path."""

    fig.tight_layout()
    fig.savefig(png_path, dpi=FIGURE_DPI)
    if EXPORT_PDF:
        fig.savefig(png_path.with_suffix(".pdf"))
    plt.close(fig)
    return png_path


def _mark_baseline(ax: plt.Axes, x: float, y: float, label: str = "Operating point") -> Line2D:
    """Add the consistent baseline operating-point marker, crosshairs, and return its handle."""

    # Add crosshairs extending to the axes
    ax.axvline(x, color="white", linestyle="--", linewidth=1.2, alpha=0.9, zorder=5)
    ax.axhline(y, color="white", linestyle="--", linewidth=1.2, alpha=0.9, zorder=5)

    return ax.scatter(
        [x], [y], marker="X", s=120, c=BASELINE_COLOR,
        edgecolors="white", linewidths=1.2, zorder=6, label=label,
    )


def _filled_contour(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    title: str,
    xlabel: str,
    ylabel: str,
    cbar_label: str,
    path: Path,
    *,
    baseline: tuple[float, float] | None = None,
    baseline_label: str = "Operating point",
    baseline_annotation: str | None = None,
    diverging_zero: bool = False,
    threshold_levels: list[float] | None = None,
    threshold_label: str | None = None,
    threshold_color: str = WARNING_COLOR,
) -> Path:
    """Render a filled contour map with labelled lines, baseline, and thresholds.

    When ``diverging_zero`` is True and the data straddle 0, a diverging colormap
    centered on 0 is used and the 0-level (link-closure) contour is drawn in bold.
    ``threshold_levels`` adds extra dashed iso-lines (e.g. an elevation limit),
    automatically clipped to the data range so empty contours are never drawn.
    """

    fig, ax = plt.subplots(figsize=FIGSIZE_CONTOUR)
    z_min, z_max = float(np.nanmin(z)), float(np.nanmax(z))
    legend_handles: list = []

    if diverging_zero and z_min < 0.0 < z_max:
        norm = TwoSlopeNorm(vmin=z_min, vcenter=0.0, vmax=z_max)
        filled = ax.contourf(x, y, z, levels=np.linspace(z_min, z_max, 26), cmap=DIVERGING_CMAP, norm=norm)
        zero = ax.contour(x, y, z, levels=[0.0], colors=THRESHOLD_COLOR, linewidths=3.0)
        labels = ax.clabel(zero, inline=True, fontsize=CONTOUR_LABEL_SIZE + 1, fmt="0 dB")
        for label in labels:
            label.set_bbox(CONTOUR_LABEL_BOX)
            label.set_clip_on(False)
        legend_handles.append(Line2D([0], [0], color=THRESHOLD_COLOR, lw=3.0, label="0 dB closure"))
    else:
        filled = ax.contourf(x, y, z, levels=24, cmap=SEQUENTIAL_CMAP)
        line_levels = np.linspace(z_min, z_max, 9)
        lines = ax.contour(x, y, z, levels=line_levels, colors=CONTOUR_LINE_COLOR, linewidths=1.05, alpha=0.86)
        labels = ax.clabel(lines, inline=True, fontsize=CONTOUR_LABEL_SIZE + 1, fmt="%.1f")
        for label in labels:
            label.set_bbox(CONTOUR_LABEL_BOX)
            label.set_clip_on(False)

    if threshold_levels:
        usable = [lv for lv in threshold_levels if z_min < lv < z_max]
        if usable:
            extra = ax.contour(x, y, z, levels=usable, colors=threshold_color, linewidths=2.4, linestyles="--")
            labels = ax.clabel(extra, inline=True, fontsize=CONTOUR_LABEL_SIZE + 1, fmt="%.0f")
            for label in labels:
                label.set_bbox(CONTOUR_LABEL_BOX)
                label.set_clip_on(False)
            if threshold_label:
                legend_handles.append(Line2D([0], [0], color=threshold_color, lw=2.4, ls="--", label=threshold_label))

    cbar = fig.colorbar(filled, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(cbar_label, fontsize=COLORBAR_LABEL_SIZE)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=GRID_ALPHA)

    if baseline is not None:
        legend_handles.append(_mark_baseline(ax, baseline[0], baseline[1], baseline_label))
        if baseline_annotation:
            ax.annotate(
                baseline_annotation,
                xy=(baseline[0], baseline[1]),
                xytext=(25, 20),
                textcoords="offset points",
                bbox=dict(boxstyle="round,pad=0.4", fc="#fdfdfd", ec="black", lw=0.8, alpha=0.95),
                arrowprops=dict(arrowstyle="->", color="black", lw=1.2),
                fontsize=ANNOTATION_FONTSIZE,
                zorder=7,
            )

    if legend_handles:
        ax.legend(handles=legend_handles, loc="lower right")

    return _save_figure(fig, path)


def _line_plot(
    x: np.ndarray,
    series: list[tuple[np.ndarray, str]],
    title: str,
    xlabel: str,
    ylabel: str,
    path: Path,
    *,
    hline: float | None = None,
    hline_label: str = "0 dB",
    logy: bool = False,
    markers: bool = False,
) -> Path:
    """Render a clean multi-series line plot and save it (PNG + PDF)."""

    fig, ax = plt.subplots(figsize=FIGSIZE_LINE)
    plot = ax.semilogy if logy else ax.plot
    for y, label in series:
        kwargs = {"linewidth": LINE_WIDTH, "label": label}
        if markers:
            kwargs.update(marker="o", markersize=MARKER_SIZE)
        plot(x, y, **kwargs)
    if hline is not None:
        ax.axhline(hline, linestyle="--", linewidth=THIN_LINE_WIDTH, color=THRESHOLD_COLOR, alpha=0.9, label=hline_label)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, which="both" if logy else "major", alpha=GRID_ALPHA)
    if len(series) > 1 or hline is not None:
        ax.legend(loc="best")
    return _save_figure(fig, path)


def _annotate_value(ax: plt.Axes, x: float, y: float, text: str, *, color: str = THRESHOLD_COLOR) -> None:
    """Place a small offset annotation marker with a label."""

    ax.scatter([x], [y], marker="o", s=30, color=color, zorder=6)
    ax.annotate(
        text, (x, y), textcoords="offset points", xytext=(8, 8),
        fontsize=ANNOTATION_FONTSIZE, color=color,
    )


# ========================================================================
# 3.        CLEAR-SKY STATIC-BASELINE CONTOUR PLOTS (01-06)
# ========================================================================
def plot_downlink_cn0_vs_dish_and_frequency(scenario: ScenarioConfig, output_dir: Path) -> Path:
    """Map downlink carrier-to-noise density against dish diameter and frequency."""

    dish_values = np.linspace(0.45, 2.4, 70)
    freq_values_ghz = np.linspace(10.7, 12.75, 70)
    z = np.zeros((len(freq_values_ghz), len(dish_values)))

    for i, f_ghz in enumerate(freq_values_ghz):
        for j, dish in enumerate(dish_values):
            rx_ant = replace(scenario.downlink.receiver.antenna, diameter_m=float(dish), gain_dbi=None)
            rx = replace(scenario.downlink.receiver, antenna=rx_ant)
            downlink = replace(scenario.downlink, receiver=rx, frequency_hz=float(f_ghz) * GHZ)
            result = calculate_scenario(replace(scenario, downlink=downlink))
            z[i, j] = result.downlink.cn0_dbhz

    baseline_dish = scenario.downlink.receiver.antenna.diameter_m or 0.0
    baseline_freq = scenario.downlink.frequency_hz / GHZ
    base_res = calculate_scenario(scenario)
    baseline_z = base_res.downlink.cn0_dbhz
    ann = rf"Dish = {baseline_dish:.1f} m, Freq = {baseline_freq:.2f} GHz" + "\n" + rf"$C/N_0$ = {baseline_z:.2f} dB-Hz"

    return _filled_contour(
        dish_values,
        freq_values_ghz,
        z,
        r"Downlink $C/N_0$ Map: Receiver Dish and Frequency",
        "GS2 receiver dish diameter [m]",
        "Downlink frequency [GHz]",
        r"Downlink $C/N_0$ [dB-Hz]",
        output_dir / "01_downlink_cn0_dish_vs_frequency.png",
        baseline=(baseline_dish, baseline_freq),
        baseline_annotation=ann,
    )


def plot_downlink_margin_vs_eirp_and_tsys(scenario: ScenarioConfig, output_dir: Path) -> Path:
    """Map the end-to-end margin against satellite EIRP and GS2 noise temperature."""

    eirp_values = np.linspace(42.0, 58.0, 70)
    tsys_values = np.linspace(90.0, 330.0, 70)
    z = np.zeros((len(tsys_values), len(eirp_values)))

    for i, tsys in enumerate(tsys_values):
        for j, eirp in enumerate(eirp_values):
            sat_tx = replace(scenario.downlink.transmitter, eirp_dbw_override=float(eirp))
            gs2_rx = replace(scenario.downlink.receiver, system_noise_temperature_k=float(tsys))
            downlink = replace(scenario.downlink, transmitter=sat_tx, receiver=gs2_rx)
            result = calculate_scenario(replace(scenario, downlink=downlink))
            z[i, j] = result.combined_margin_ni_db

    cbar = (
        r"Combined $E_b/(N_0+I_0)$ margin [dB]" if scenario.interference.enabled
        else r"Combined $E_b/N_0$ margin [dB]"
    )
    baseline_eirp = scenario.downlink.transmitter.eirp_dbw_override or 0.0
    baseline_tsys = scenario.downlink.receiver.system_noise_temperature_k or 0.0
    base_res = calculate_scenario(scenario)
    baseline_z = base_res.combined_margin_ni_db
    ann = rf"EIRP = {baseline_eirp:.1f} dBW, $T_{{sys}}$ = {baseline_tsys:.1f} K" + "\n" + rf"Margin = {baseline_z:.2f} dB"

    return _filled_contour(
        eirp_values,
        tsys_values,
        z,
        "Downlink Design Sensitivity: EIRP and Receiver Noise Temperature",
        "Satellite downlink EIRP [dBW]",
        r"GS2 system noise temperature $T_{\mathrm{sys}}$ [K]",
        cbar,
        output_dir / "02_downlink_margin_eirp_vs_tsys.png",
        baseline=(baseline_eirp, baseline_tsys),
        baseline_annotation=ann,
        diverging_zero=True,
    )


def plot_uplink_cn_vs_power_and_dish(scenario: ScenarioConfig, output_dir: Path) -> Path:
    """Map uplink C/N against GS1 HPA output power and transmit dish diameter."""

    power_w_values = np.linspace(2.0, 80.0, 70)
    dish_values = np.linspace(0.8, 4.5, 70)
    z = np.zeros((len(dish_values), len(power_w_values)))

    for i, dish in enumerate(dish_values):
        for j, power_w in enumerate(power_w_values):
            tx_ant = replace(scenario.uplink.transmitter.antenna, diameter_m=float(dish), gain_dbi=None)
            tx = replace(scenario.uplink.transmitter, antenna=tx_ant, tx_power_dbw=watts_to_dbw(float(power_w)))
            uplink = replace(scenario.uplink, transmitter=tx)
            result = calculate_scenario(replace(scenario, uplink=uplink))
            z[i, j] = result.uplink.cn_db

    baseline_power_w = 10 ** ((scenario.uplink.transmitter.tx_power_dbw or 0.0) / 10.0)
    baseline_dish = scenario.uplink.transmitter.antenna.diameter_m or 0.0
    base_res = calculate_scenario(scenario)
    baseline_z = base_res.uplink.cn_db
    ann = f"Pt = {baseline_power_w:.1f} W, Dt = {baseline_dish:.1f} m\nC/N = {baseline_z:.2f} dB"

    return _filled_contour(
        power_w_values,
        dish_values,
        z,
        r"Uplink $C/N$ Map: HPA Power and Transmit Dish",
        "GS1 RF output power [W]",
        "GS1 transmit dish diameter [m]",
        r"Uplink $C/N$ [dB]",
        output_dir / "03_uplink_cn_power_vs_dish.png",
        baseline=(baseline_power_w, baseline_dish),
        baseline_annotation=ann,
    )


def plot_combined_ebn0_vs_bitrate_and_bandwidth(scenario: ScenarioConfig, output_dir: Path) -> Path:
    """Map end-to-end energy-per-bit ratio against bit rate and bandwidth."""

    bitrate_mbps = np.linspace(2.0, 60.0, 70)
    bandwidth_mhz = np.linspace(6.0, 72.0, 70)
    z = np.zeros((len(bandwidth_mhz), len(bitrate_mbps)))

    for i, bw_mhz in enumerate(bandwidth_mhz):
        for j, rb_mbps in enumerate(bitrate_mbps):
            uplink = replace(scenario.uplink, bandwidth_hz=float(bw_mhz) * MHZ, bit_rate_bps=float(rb_mbps) * 1.0e6)
            downlink = replace(scenario.downlink, bandwidth_hz=float(bw_mhz) * MHZ, bit_rate_bps=float(rb_mbps) * 1.0e6)
            result = calculate_scenario(replace(scenario, uplink=uplink, downlink=downlink))
            z[i, j] = result.combined_ebn0_ni_db

    cbar = (
        r"Combined $E_b/(N_0+I_0)$ [dB]" if scenario.interference.enabled else r"Combined $E_b/N_0$ [dB]"
    )
    required = scenario.uplink.required_ebn0_db
    baseline_rb = scenario.uplink.bit_rate_bps / 1.0e6
    baseline_bw = scenario.uplink.bandwidth_hz / MHZ
    base_res = calculate_scenario(scenario)
    baseline_z = base_res.combined_ebn0_ni_db
    ann = rf"Rb = {baseline_rb:.1f} Mbps, BW = {baseline_bw:.1f} MHz" + "\n" + rf"$E_b/(N_0+I_0)$ = {baseline_z:.2f} dB"

    return _filled_contour(
        bitrate_mbps,
        bandwidth_mhz,
        z,
        "End-to-End Link Closure Map: Bit Rate and Bandwidth",
        "Bit rate [Mbit/s]",
        "Noise bandwidth [MHz]",
        cbar,
        output_dir / "04_total_ebn0_bitrate_vs_bandwidth.png",
        baseline=(baseline_rb, baseline_bw),
        baseline_annotation=ann,
        threshold_levels=[required],
        threshold_label=rf"required $E_b/N_0$ = {required:g} dB",
    )


def plot_gs2_elevation_by_latitude_longitude(scenario: ScenarioConfig, output_dir: Path) -> Path:
    """Map GS2 elevation angle over latitude/longitude, with low-elevation limits."""

    lat_values = np.linspace(30.0, 48.0, 80)
    lon_values = np.linspace(20.0, 45.0, 80)
    z = np.zeros((len(lat_values), len(lon_values)))

    for i, lat in enumerate(lat_values):
        for j, lon in enumerate(lon_values):
            loc = replace(scenario.downlink.receiver.location, latitude_deg=float(lat), longitude_deg=float(lon))
            rx = replace(scenario.downlink.receiver, location=loc)
            downlink = replace(scenario.downlink, receiver=rx)
            result = calculate_scenario(replace(scenario, downlink=downlink))
            z[i, j] = result.downlink.elevation_deg

    baseline_loc = scenario.downlink.receiver.location
    base_res = calculate_scenario(scenario)
    baseline_z = base_res.downlink.elevation_deg
    ann = f"Lon = {baseline_loc.longitude_deg:.1f}°, Lat = {baseline_loc.latitude_deg:.1f}°\nElevation = {baseline_z:.1f}°"

    return _filled_contour(
        lon_values,
        lat_values,
        z,
        "GS2 Elevation Angle Map",
        "GS2 longitude [deg East]",
        "GS2 latitude [deg North]",
        "Elevation angle [deg]",
        output_dir / "05_gs2_elevation_latitude_vs_longitude.png",
        baseline=(baseline_loc.longitude_deg, baseline_loc.latitude_deg),
        baseline_annotation=ann,
        threshold_levels=[5.0, 10.0],
        threshold_label="low-elevation limit [deg]",
    )


def plot_downlink_asi_ci_vs_spacing_and_dish(scenario: ScenarioConfig, output_dir: Path) -> Path:
    """Map downlink adjacent-satellite C/I against GEO spacing and dish diameter.

    This is an engineering trend model (off-axis discrimination), not regulatory
    coordination; a representative 20 dB C/I objective line is shown for context.
    """

    dish_values = np.linspace(0.45, 3.0, 80)
    spacing_values = np.linspace(0.8, 4.0, 80)
    z = calculate_asi_ci_grid(scenario, dish_values, spacing_values, link="downlink")
    baseline_dish = scenario.downlink.receiver.antenna.diameter_m or 0.0
    baseline_spacing = abs(
        scenario.interference.adjacent_satellite_longitudes_deg[0] - scenario.satellite.longitude_deg
    )
    ann = f"Dish = {baseline_dish:.1f} m\nSpacing = {baseline_spacing:.1f}°"

    return _filled_contour(
        dish_values,
        spacing_values,
        z,
        "Adjacent-Satellite C/I Map (Engineering Trend Model)",
        "GS2 receiver dish diameter [m]",
        "Adjacent satellite spacing [deg]",
        "Downlink ASI C/I [dB]",
        output_dir / "06_downlink_asi_ci_spacing_vs_dish.png",
        baseline=(baseline_dish, baseline_spacing),
        baseline_annotation=ann,
        threshold_levels=[20.0],
        threshold_label="20 dB C/I (illustrative objective)",
    )


def generate_contour_plots(scenario: ScenarioConfig, output_dir: Path) -> list[Path]:
    """Generate the clear-sky static-baseline contour plots used in the report.

    The adjacent-satellite C/I contour is only produced when interference is
    enabled, because it has no meaning without the interference model.
    """

    _prepare_output_dir(output_dir)
    paths = [
        plot_downlink_cn0_vs_dish_and_frequency(scenario, output_dir),
        plot_downlink_margin_vs_eirp_and_tsys(scenario, output_dir),
        plot_uplink_cn_vs_power_and_dish(scenario, output_dir),
        plot_combined_ebn0_vs_bitrate_and_bandwidth(scenario, output_dir),
        plot_gs2_elevation_by_latitude_longitude(scenario, output_dir),
    ]
    if scenario.interference.enabled:
        paths.append(plot_downlink_asi_ci_vs_spacing_and_dish(scenario, output_dir))
    return paths


# ========================================================================
# 4.        APPARENT-MOTION TIME-VARYING PLOTS (07-11)
# ========================================================================
def generate_time_varying_plots(samples: list[TimeVaryingSample], output_dir: Path) -> list[Path]:
    """Generate plots for the deterministic apparent GEO station-keeping motion."""

    _prepare_output_dir(output_dir)
    t = np.array([s.time_hours for s in samples], dtype=float)
    margin_noise = np.array([s.result.combined_margin_db for s in samples], dtype=float)
    margin_ni = np.array([s.result.combined_margin_ni_db for s in samples], dtype=float)
    el_up = np.array([s.result.uplink.elevation_deg for s in samples], dtype=float)
    el_down = np.array([s.result.downlink.elevation_deg for s in samples], dtype=float)
    range_up = np.array([s.result.uplink.range_km for s in samples], dtype=float)
    range_down = np.array([s.result.downlink.range_km for s in samples], dtype=float)
    fspl_down = np.array([s.result.downlink.free_space_loss_db for s in samples], dtype=float)
    lon = np.array([s.satellite.longitude_deg for s in samples], dtype=float)
    lat = np.array([s.satellite.latitude_deg for s in samples], dtype=float)

    paths: list[Path] = []

    # 07 - combined margin over time, with mean line and worst-case annotation.
    fig, ax = plt.subplots(figsize=FIGSIZE_LINE)
    ax.plot(t, margin_noise, linewidth=THIN_LINE_WIDTH, label="noise-only")
    ax.plot(t, margin_ni, linewidth=LINE_WIDTH, label="with ASI + IMD")
    ax.axhline(0.0, linestyle="--", linewidth=THIN_LINE_WIDTH, color=THRESHOLD_COLOR, alpha=0.9, label="0 dB outage threshold")
    mean_ni = float(np.mean(margin_ni))
    ax.axhline(mean_ni, linestyle=":", linewidth=THIN_LINE_WIDTH, color="#1f77b4", alpha=0.9, label=f"mean = {mean_ni:.2f} dB")
    i_min = int(np.argmin(margin_ni))
    _annotate_value(ax, t[i_min], margin_ni[i_min], f"min {margin_ni[i_min]:.2f} dB", color=BASELINE_COLOR)

    ax.set_xlabel("Time [h]")
    ax.set_ylabel(r"Combined $E_b/N_0$ margin [dB]")
    ax.grid(True, alpha=GRID_ALPHA)
    ax.legend(loc="best")
    paths.append(_save_figure(fig, output_dir / "07_time_varying_combined_margin.png"))

    # 08 - elevation angles.
    paths.append(
        _line_plot(
            t,
            [(el_up, "GS1 uplink elevation"), (el_down, "GS2 downlink elevation")],
            "Elevation Angle Variation From Apparent GEO Motion",
            "Time [h]",
            "Elevation angle [deg]",
            output_dir / "08_time_varying_elevation_angles.png",
        )
    )

    # 09 - slant-range delta.
    paths.append(
        _line_plot(
            t,
            [(range_up - range_up[0], "uplink"), (range_down - range_down[0], "downlink")],
            "Slant-Range Variation Relative to First Sample",
            "Time [h]",
            "Slant-range change [km]",
            output_dir / "09_time_varying_slant_range_delta.png",
        )
    )

    # 10 - downlink FSPL delta.
    paths.append(
        _line_plot(
            t,
            [(fspl_down - fspl_down[0], "downlink FSPL change")],
            "Downlink Free-Space Loss Variation",
            "Time [h]",
            "FSPL change [dB]",
            output_dir / "10_time_varying_fspl_delta.png",
        )
    )

    # 11 - sub-satellite track.
    fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
    ax.plot(lon, lat, marker="o", markersize=2.6, linewidth=1.2, color="#1f77b4")
    _mark_baseline(ax, lon[0], lat[0], "start")

    ax.set_xlabel("Sub-satellite longitude [deg East]")
    ax.set_ylabel("Sub-satellite latitude [deg North]")
    ax.grid(True, alpha=GRID_ALPHA)
    ax.legend(loc="best")
    paths.append(_save_figure(fig, output_dir / "11_subsatellite_apparent_motion.png"))

    return paths


# ========================================================================
# 5.        DYNAMIC TSYS AND INTERFERENCE PLOTS (12-13)
# ========================================================================
def plot_dynamic_tsys_by_elevation(scenario: ScenarioConfig, output_dir: Path) -> Path:
    """Plot the dynamic receive system noise temperature against elevation angle."""

    elevations = np.linspace(5.0, 90.0, 200)
    clear = np.array([calculate_dynamic_system_noise_temperature_k(el, 0.0, scenario.dynamic_noise) for el in elevations])
    rain_3db = np.array([calculate_dynamic_system_noise_temperature_k(el, 3.0, scenario.dynamic_noise) for el in elevations])
    rain_8db = np.array([calculate_dynamic_system_noise_temperature_k(el, 8.0, scenario.dynamic_noise) for el in elevations])

    return _line_plot(
        elevations,
        [(clear, "clear sky"), (rain_3db, "rain, A = 3 dB"), (rain_8db, "heavy rain, A = 8 dB")],
        "Receive System Noise Temperature vs Elevation",
        "Elevation angle [deg]",
        r"GS2 system noise temperature $T_{\mathrm{sys}}$ [K]",
        output_dir / "12_dynamic_tsys_vs_elevation.png",
    )


def plot_interference_comparison(scenario: ScenarioConfig, output_dir: Path) -> Path:
    """Bar comparison of noise-only vs interference-included energy-per-bit ratio."""

    result = calculate_scenario(scenario, use_dynamic_downlink_tsys=True)
    labels = ["Noise only\n$E_b/N_0$", "With ASI + IMD\n$E_b/(N_0+I_0)$"]
    values = [result.combined_ebn0_db, result.combined_ebn0_ni_db]

    fig, ax = plt.subplots(figsize=(7.0, 5.0))
    bars = ax.bar(labels, values, color=["#4c9f70", "#1f77b4"], width=0.55, edgecolor="white")
    ax.axhline(result.uplink.required_ebn0_db, linestyle="--", color=THRESHOLD_COLOR,
               linewidth=THIN_LINE_WIDTH, label=rf"required $E_b/N_0$ = {result.uplink.required_ebn0_db:g} dB")
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2.0, value + 0.15, f"{value:.2f} dB", ha="center", va="bottom",
                fontsize=ANNOTATION_FONTSIZE)

    ax.set_ylabel("End-to-end energy ratio [dB]")
    ax.grid(True, axis="y", alpha=GRID_ALPHA)
    ax.legend(loc="best")
    return _save_figure(fig, output_dir / "13_noise_only_vs_interference_bar.png")


# ========================================================================
# 6.        MONTE-CARLO RAIN-OUTAGE PLOTS (14-17)
# ========================================================================
def generate_availability_plots(samples: list[TimeVaryingSample], output_dir: Path) -> list[Path]:
    """Generate figures for the Monte-Carlo rain-outage simulation."""

    _prepare_output_dir(output_dir)
    t = np.array([s.time_hours for s in samples], dtype=float)
    margin = np.array([s.result.combined_margin_ni_db for s in samples], dtype=float)
    rain = np.array([s.downlink_rain_attenuation_db for s in samples], dtype=float)
    tsys = np.array([s.result.downlink.system_noise_temperature_k or np.nan for s in samples], dtype=float)

    paths: list[Path] = []
    n_window = min(len(samples), 240)  # First 240 h keeps the dynamics readable.

    # 14 - illustrative independent-site weather samples.
    paths.append(
        _line_plot(
            t[:n_window],
            [(margin[:n_window], "combined margin"), (rain[:n_window], "downlink rain attenuation")],
            "Illustrative Weather Samples: Downlink Attenuation and Margin",
            "Time [h]",
            "Level [dB]",
            output_dir / "14_rain_double_hit_margin_timeseries.png",
            hline=0.0,
            hline_label="0 dB outage threshold",
        )
    )

    # 15 - dynamic system-noise-temperature time series.
    paths.append(
        _line_plot(
            t[:n_window],
            [(tsys[:n_window], r"dynamic GS2 $T_{\mathrm{sys}}$")],
            "Rain Emission Effect on Receive Noise Temperature",
            "Time [h]",
            r"GS2 system noise temperature $T_{\mathrm{sys}}$ [K]",
            output_dir / "15_dynamic_tsys_weather_timeseries.png",
        )
    )

    # 16 - annual margin distribution and empirical outage tail.
    availability = 100.0 * float(np.mean(margin >= 0.0))
    outage_probability = 100.0 - availability
    outage_hours = float(np.sum(margin < 0.0))
    p01, p05, median_margin = np.percentile(margin, [1.0, 5.0, 50.0])
    x_min = float(np.floor(np.min(margin) - 0.5))
    x_max = float(np.ceil(np.max(margin) + 0.5))
    bins = np.linspace(x_min, x_max, 72)

    fig, (ax_hist, ax_cdf) = plt.subplots(
        1,
        2,
        figsize=(10.0, 4.8),
        gridspec_kw={"width_ratios": [1.35, 1.0]},
    )

    ax_hist.hist(
        margin,
        bins=bins,
        density=True,
        color="#2f78b7",
        alpha=0.78,
        edgecolor="white",
        linewidth=0.45,
        log=True,
    )
    ax_hist.axvline(0.0, linestyle="--", color="#c0392b", linewidth=2.0, label="0 dB outage threshold")
    ax_hist.axvline(median_margin, linestyle="-", color="#2c3e50", linewidth=1.4, label="median margin")
    ax_hist.axvline(p01, linestyle=":", color=WARNING_COLOR, linewidth=1.8, label="1st percentile")
    ax_hist.set_xlabel(r"Combined $E_b/N_0$ margin [dB]")
    ax_hist.set_ylabel("Probability density [1/dB], log scale")
    ax_hist.grid(True, axis="both", alpha=GRID_ALPHA)
    ax_hist.legend(loc="upper left")

    sorted_margin = np.sort(margin)
    empirical_cdf = 100.0 * (np.arange(1, sorted_margin.size + 1) / sorted_margin.size)
    ax_cdf.plot(sorted_margin, empirical_cdf, color="#2c3e50", linewidth=2.1)
    ax_cdf.axvline(0.0, linestyle="--", color="#c0392b", linewidth=1.8)
    ax_cdf.axhline(outage_probability, linestyle=":", color="#c0392b", linewidth=1.3)
    ax_cdf.axhline(1.0, linestyle=":", color=WARNING_COLOR, linewidth=1.2)
    ax_cdf.axhline(5.0, linestyle=":", color="#7f8c8d", linewidth=1.1)
    ax_cdf.fill_betweenx([0.0, 8.0], x_min, 0.0, color="#c0392b", alpha=0.08)
    ax_cdf.set_xlim(x_min, x_max)
    ax_cdf.set_ylim(0.0, 8.0)
    ax_cdf.set_xlabel(r"Combined $E_b/N_0$ margin [dB]")
    ax_cdf.set_ylabel("Lower-tail empirical CDF [%]")
    ax_cdf.grid(True, axis="both", alpha=GRID_ALPHA)
    ax_cdf.text(
        0.05,
        0.95,
        "\n".join([
            f"availability = {availability:.3f}%",
            f"outage samples = {outage_hours:.0f} h",
            f"1% margin = {p01:.2f} dB",
            f"5% margin = {p05:.2f} dB",
        ]),
        transform=ax_cdf.transAxes,
        fontsize=ANNOTATION_FONTSIZE,
        va="top",
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": "#bbbbbb", "alpha": 0.94},
    )

    paths.append(_save_figure(fig, output_dir / "16_availability_margin_histogram.png"))

    # 17 - outage timeline.
    outage = margin < 0.0
    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    ax.fill_between(t, 0.0, outage.astype(float), step="post", color=BASELINE_COLOR, alpha=0.7)
    ax.set_ylim(-0.1, 1.1)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["available", "outage"])

    ax.set_xlabel("Time [h] over one simulated year")
    ax.grid(True, axis="x", alpha=GRID_ALPHA)
    paths.append(_save_figure(fig, output_dir / "17_availability_outage_timeline.png"))

    return paths


# ========================================================================
# 7.        DIGITAL BER / FEC / SHANNON PLOTS (18-22)
# ========================================================================
def plot_ber_curves_vs_ebn0(scenario: ScenarioConfig, output_dir: Path) -> Path:
    """Plot uncoded and coding-gain-shifted BER with the operating point."""

    cfg = scenario.digital
    result = calculate_scenario(scenario, use_dynamic_downlink_tsys=True)
    ebn0_grid = np.linspace(0.0, 15.0, 240)
    uncoded = np.array([max(theoretical_ber_awgn(float(x), cfg.modulation), 1.0e-300) for x in ebn0_grid])
    coded = np.array([max(theoretical_ber_awgn(float(x + cfg.coding_gain_db), cfg.modulation), 1.0e-300) for x in ebn0_grid])

    fig, ax = plt.subplots(figsize=(8.4, 5.3))
    ax.semilogy(ebn0_grid, uncoded, linewidth=LINE_WIDTH, label=f"{cfg.modulation} uncoded AWGN")
    ax.semilogy(ebn0_grid, coded, linewidth=LINE_WIDTH, label=f"{cfg.modulation} + {cfg.coding_gain_db:.1f} dB coding gain")
    ax.axhline(cfg.target_ber, linestyle="--", linewidth=THIN_LINE_WIDTH, color=THRESHOLD_COLOR, label=f"target BER = {cfg.target_ber:g}")
    ax.axvline(result.combined_ebn0_ni_db, linestyle=":", linewidth=1.6, color=BASELINE_COLOR,
               label=rf"operating $E_b/N_0$ = {result.combined_ebn0_ni_db:.2f} dB")

    ax.set_xlabel(r"$E_b/N_0$ [dB]")
    ax.set_ylabel("Bit error rate")
    ax.set_ylim(1.0e-12, 1.0)
    ax.grid(True, which="both", alpha=GRID_ALPHA)
    ax.legend(loc="best")
    return _save_figure(fig, output_dir / "18_ber_vs_ebn0_with_fec.png")


def plot_time_varying_ber(samples: list[TimeVaryingSample], output_dir: Path) -> Path:
    """Plot time-varying BER for the apparent-motion case (log scale)."""

    t = np.array([s.time_hours for s in samples], dtype=float)
    ber_uncoded = np.array([
        max(s.result.digital.interference_ber_uncoded if s.result.digital is not None else np.nan, 1.0e-300)
        for s in samples
    ])
    ber_coded = np.array([
        max(s.result.digital.interference_ber_with_coding_gain if s.result.digital is not None else np.nan, 1.0e-300)
        for s in samples
    ])

    return _line_plot(
        t,
        [(ber_uncoded, "uncoded, with ASI + IMD"), (ber_coded, "FEC coding-gain approximation")],
        "Time-Varying BER Under Apparent GEO Motion",
        "Time [h]",
        "Bit error rate",
        output_dir / "19_time_varying_ber.png",
        logy=True,
    )


def plot_shannon_capacity_vs_cn(scenario: ScenarioConfig, output_dir: Path) -> Path:
    """Plot Shannon-Hartley capacity vs C/N, with the operating point marked."""

    bandwidth = scenario.uplink.bandwidth_hz
    bit_rate = scenario.uplink.bit_rate_bps
    cn_grid = np.linspace(-6.0, 20.0, 240)
    capacity_mbps = np.array([shannon_capacity_bps(bandwidth, float(cn)) / 1.0e6 for cn in cn_grid])
    result = calculate_scenario(scenario, use_dynamic_downlink_tsys=True)

    fig, ax = plt.subplots(figsize=(8.4, 5.3))
    ax.plot(cn_grid, capacity_mbps, linewidth=LINE_WIDTH, label="Shannon capacity")
    ax.axhline(bit_rate / 1.0e6, linestyle="--", linewidth=THIN_LINE_WIDTH, color=THRESHOLD_COLOR,
               label=f"information rate = {bit_rate / 1.0e6:g} Mbit/s")
    ax.axvline(result.combined_cni_db, linestyle=":", linewidth=1.6, color=BASELINE_COLOR,
               label=f"operating C/(N+I) = {result.combined_cni_db:.2f} dB")

    ax.set_xlabel("C/N or C/(N+I) over bandwidth [dB]")
    ax.set_ylabel("Capacity [Mbit/s]")
    ax.grid(True, alpha=GRID_ALPHA)
    ax.legend(loc="best")
    return _save_figure(fig, output_dir / "20_shannon_capacity_vs_cn.png")


def plot_capacity_comparison(scenario: ScenarioConfig, output_dir: Path) -> Path:
    """Bar comparison of information rate vs Shannon capacity estimates."""

    result = calculate_scenario(scenario, use_dynamic_downlink_tsys=True)
    if result.digital is None:
        raise ValueError("Digital metrics are disabled.")

    labels = ["Information\nbit rate", "Capacity\nnoise only", "Capacity\nwith ASI + IMD"]
    values = [
        result.digital.information_bit_rate_bps / 1.0e6,
        result.digital.shannon_capacity_noise_only_bps / 1.0e6,
        result.digital.shannon_capacity_with_interference_bps / 1.0e6,
    ]

    fig, ax = plt.subplots(figsize=(7.4, 5.0))
    bars = ax.bar(labels, values, color=["#d62728", "#4c9f70", "#1f77b4"], width=0.6, edgecolor="white")
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2.0, value + 0.5, f"{value:.1f}", ha="center", va="bottom",
                fontsize=ANNOTATION_FONTSIZE)

    ax.set_ylabel("Rate [Mbit/s]")
    ax.grid(True, axis="y", alpha=GRID_ALPHA)
    return _save_figure(fig, output_dir / "21_capacity_margin_bar.png")


def plot_occupied_bandwidth_vs_code_rate(scenario: ScenarioConfig, output_dir: Path) -> Path:
    """Plot the FEC tradeoff between code rate and required occupied bandwidth."""

    cfg = scenario.digital
    bits_per_symbol = modulation_bits_per_symbol(cfg.modulation)
    rates = np.linspace(0.45, 1.0, 160)
    occupied_mhz = (scenario.uplink.bit_rate_bps / rates / bits_per_symbol) * (1.0 + cfg.rolloff_factor) / 1.0e6
    baseline_bw = (scenario.uplink.bit_rate_bps / cfg.code_rate / bits_per_symbol) * (1.0 + cfg.rolloff_factor) / 1.0e6

    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    ax.plot(rates, occupied_mhz, linewidth=LINE_WIDTH, color="#1f77b4")
    ax.axhline(scenario.uplink.bandwidth_hz / 1.0e6, linestyle="--", linewidth=THIN_LINE_WIDTH, color=THRESHOLD_COLOR,
               label=f"allocated bandwidth = {scenario.uplink.bandwidth_hz / 1.0e6:g} MHz")
    _mark_baseline(ax, cfg.code_rate, baseline_bw, "baseline code rate")

    ax.set_xlabel("FEC code rate [-]")
    ax.set_ylabel("Estimated occupied bandwidth [MHz]")
    ax.grid(True, alpha=GRID_ALPHA)
    ax.legend(loc="best")
    return _save_figure(fig, output_dir / "22_occupied_bandwidth_vs_code_rate.png")


def generate_digital_plots(
    scenario: ScenarioConfig,
    time_samples: list[TimeVaryingSample],
    output_dir: Path,
) -> list[Path]:
    """Generate BER, FEC, and Shannon-capacity figures (only when DIGITAL enabled).

    The time-varying BER figure is only produced when apparent-motion time
    samples are available; the other figures depend only on the static budget.
    """

    if not scenario.digital.enabled:
        return []
    paths = [plot_ber_curves_vs_ebn0(scenario, output_dir)]
    if time_samples:
        paths.append(plot_time_varying_ber(time_samples, output_dir))
    paths.append(plot_shannon_capacity_vs_cn(scenario, output_dir))
    paths.append(plot_capacity_comparison(scenario, output_dir))
    paths.append(plot_occupied_bandwidth_vs_code_rate(scenario, output_dir))
    return paths


def generate_advanced_plots(
    scenario: ScenarioConfig,
    time_samples: list[TimeVaryingSample],
    monte_carlo_samples: list[TimeVaryingSample],
    output_dir: Path,
) -> list[Path]:
    """Generate the advanced plot bundle, skipping every disabled section.

    Each block is gated by its own enabled flag (and by the presence of the
    data it needs), so no figure is ever drawn from placeholder data.
    """

    _prepare_output_dir(output_dir)
    paths: list[Path] = []
    if scenario.apparent_motion.enabled and time_samples:
        paths += generate_time_varying_plots(time_samples, output_dir)
    if scenario.dynamic_noise.enabled:
        paths.append(plot_dynamic_tsys_by_elevation(scenario, output_dir))
    if scenario.interference.enabled:
        paths.append(plot_interference_comparison(scenario, output_dir))
    if scenario.rain_outage.enabled and monte_carlo_samples:
        paths += generate_availability_plots(monte_carlo_samples, output_dir)
    paths += generate_digital_plots(scenario, time_samples, output_dir)
    return paths


# ========================================================================
# 8.        ITU-R PROPAGATION AND DVB-S2 ACM PLOTS (23-29)
# ========================================================================
def plot_itu_attenuation_vs_availability(
    itu_curve: list[ITUPropagationResult],
    output_dir: Path,
    design_exceedance_percent: float | None = None,
) -> Path:
    """Plot ITU-R downlink attenuation against the unavailability percentage p.

    The x-axis is the percentage of an average year the attenuation is exceeded
    (unavailability p); it is plotted on a log scale and inverted so that higher
    availability (smaller p) is to the right. The optional design point is marked.
    """

    p = np.array([r.design_exceedance_percent for r in itu_curve], dtype=float)
    rain = np.array([r.downlink_breakdown.rain_db for r in itu_curve], dtype=float)
    gas = np.array([r.downlink_breakdown.gaseous_db for r in itu_curve], dtype=float)
    cloud = np.array([r.downlink_breakdown.cloud_db for r in itu_curve], dtype=float)
    scint = np.array([r.downlink_breakdown.scintillation_db for r in itu_curve], dtype=float)
    total = np.array([r.downlink_breakdown.total_db for r in itu_curve], dtype=float)

    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    ax.fill_between(p, total, color="#e0e0e0", alpha=0.5, label="_nolegend_")
    ax.semilogx(p, total, linewidth=2.5, marker="o", markersize=MARKER_SIZE, color="#2c3e50", label="total (P.618 Sec. 2.5)")
    ax.semilogx(p, rain, linewidth=LINE_WIDTH, linestyle="--", color="#2980b9", label="rain (P.618 / P.838)")
    ax.semilogx(p, gas, linewidth=LINE_WIDTH, linestyle="-.", color="#27ae60", label="gaseous (P.676)")
    ax.semilogx(p, cloud, linewidth=LINE_WIDTH, linestyle=":", color="#f39c12", label="cloud (P.840)")
    ax.semilogx(p, scint, linewidth=LINE_WIDTH, linestyle="--", color="#8e44ad", label="scintillation (P.618)")
    ax.invert_xaxis()
    if design_exceedance_percent is not None:
        ax.axvline(design_exceedance_percent, linestyle="--", linewidth=THIN_LINE_WIDTH, color=BASELINE_COLOR,
                   label=f"design point p = {design_exceedance_percent:g}%")

    ax.set_xlabel("Per-path exceedance p [% of average year]  (right = rarer fade)")
    ax.set_ylabel("Attenuation [dB]")
    ax.grid(True, which="both", alpha=GRID_ALPHA)
    ax.legend(loc="best")
    return _save_figure(fig, output_dir / "23_itu_attenuation_vs_availability.png")


def plot_itu_margin_vs_availability(
    itu_curve: list[ITUPropagationResult],
    output_dir: Path,
    design_availability_percent: float | None = None,
) -> Path:
    """Plot coincident dual-site stress margin against per-path non-exceedance."""

    availability = np.array([r.design_availability_percent for r in itu_curve], dtype=float)
    margin_ni = np.array([r.faded_result.combined_margin_ni_db for r in itu_curve], dtype=float)
    margin_noise = np.array([r.faded_result.combined_margin_db for r in itu_curve], dtype=float)

    fig, ax = plt.subplots(figsize=FIGSIZE_LINE)
    ax.fill_between(availability, margin_ni, 0, where=(margin_ni >= 0), color="#27ae60", alpha=0.15, label="_nolegend_", interpolate=True)
    ax.fill_between(availability, margin_ni, 0, where=(margin_ni < 0), color="#e74c3c", alpha=0.15, label="_nolegend_", interpolate=True)
    ax.plot(availability, margin_noise, linewidth=THIN_LINE_WIDTH, linestyle="--", marker="s", markersize=MARKER_SIZE, color="#7f8c8d", label="noise-only")
    ax.plot(availability, margin_ni, linewidth=2.5, marker="o", markersize=MARKER_SIZE+1, color="#2c3e50", label="with ASI + IMD")
    ax.axhline(0.0, linestyle="-", linewidth=1.5, color="#e74c3c", label="0 dB closure")
    if design_availability_percent is not None:
        design = [r for r in itu_curve if abs(r.design_availability_percent - design_availability_percent) < 1e-9]
        ax.axvline(design_availability_percent, linestyle=":", linewidth=1.6, color=BASELINE_COLOR,
                   label=f"design = {design_availability_percent:g}%")
        if design:
            _annotate_value(ax, design_availability_percent, design[0].faded_result.combined_margin_ni_db,
                            f"{design[0].faded_result.combined_margin_ni_db:.2f} dB", color=BASELINE_COLOR)

    ax.set_xlabel("Per-path non-exceedance [%]; coincident dual-site stress")
    ax.set_ylabel(r"Combined $E_b/N_0$ margin [dB]")
    ax.grid(True, alpha=GRID_ALPHA)
    ax.legend(loc="best")
    return _save_figure(fig, output_dir / "24_itu_margin_vs_availability.png")


def plot_itu_attenuation_breakdown_bar(scenario: ScenarioConfig, output_dir: Path) -> Path:
    """Grouped bar chart of per-mechanism attenuation at the design availability."""

    design = calculate_scenario_with_itu(scenario)
    mechanisms = ["rain", "gaseous", "cloud", "scintillation", "total"]
    up = [design.uplink_breakdown.rain_db, design.uplink_breakdown.gaseous_db, design.uplink_breakdown.cloud_db,
          design.uplink_breakdown.scintillation_db, design.uplink_breakdown.total_db]
    down = [design.downlink_breakdown.rain_db, design.downlink_breakdown.gaseous_db, design.downlink_breakdown.cloud_db,
            design.downlink_breakdown.scintillation_db, design.downlink_breakdown.total_db]

    x = np.arange(len(mechanisms))
    width = 0.38
    fig, ax = plt.subplots(figsize=FIGSIZE_BAR)
    bars_up = ax.bar(x - width / 2 - 0.02, up, width, color="#27ae60", edgecolor="#1e8449", hatch="////", alpha=0.85,
                     label=f"uplink {scenario.uplink.frequency_hz / GHZ:.1f} GHz")
    bars_down = ax.bar(x + width / 2 + 0.02, down, width, color="#2980b9", edgecolor="#1a5276", hatch="\\\\\\\\", alpha=0.85,
                       label=f"downlink {scenario.downlink.frequency_hz / GHZ:.1f} GHz")
    for bars in (bars_up, bars_down):
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width() / 2.0, bar.get_height() + 0.03, f"{bar.get_height():.2f}",
                    ha="center", va="bottom", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels(mechanisms)

    ax.set_ylabel("Attenuation [dB]")
    ax.grid(True, axis="y", alpha=GRID_ALPHA)
    ax.legend(loc="best")
    return _save_figure(fig, output_dir / "25_itu_attenuation_breakdown_bar.png")


def plot_rain_attenuation_vs_frequency(scenario: ScenarioConfig, output_dir: Path) -> Path:
    """Plot rain attenuation A_0.01 vs frequency for the downlink geometry."""

    cfg = scenario.itu_propagation
    gs2 = scenario.downlink.receiver.location
    geom = calculate_geo_link_geometry(gs2, scenario.satellite)
    freqs = np.linspace(4.0, 50.0, 140)
    a001 = np.array([
        itu.rain_attenuation_001_db(
            float(f), geom.elevation_deg, gs2.latitude_deg, gs2.altitude_km,
            cfg.rain_rate_001_mm_per_h, cfg.polarization_tilt_deg, cfg.rain_height_h0_override_km,
        )
        for f in freqs
    ])
    design_freq = scenario.downlink.frequency_hz / GHZ
    design_a001 = itu.rain_attenuation_001_db(
        design_freq, geom.elevation_deg, gs2.latitude_deg, gs2.altitude_km,
        cfg.rain_rate_001_mm_per_h, cfg.polarization_tilt_deg, cfg.rain_height_h0_override_km,
    )

    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.fill_between(freqs, a001, color="#3498db", alpha=0.2)
    ax.plot(freqs, a001, linewidth=2.5, color="#2980b9")
    for band, f0 in (("C", 4.0), ("X", 8.0), ("Ku", 12.0), ("Ka", 20.0)):
        ax.axvline(f0, linestyle=":", linewidth=0.9, color="#999999", alpha=0.7)
        ax.text(f0, ax.get_ylim()[1] * 0.93, band, fontsize=ANNOTATION_FONTSIZE, ha="center", color="#666666")
    _mark_baseline(ax, design_freq, design_a001, "downlink design frequency")

    ax.set_xlabel("Frequency [GHz]")
    ax.set_ylabel("Rain attenuation exceeded 0.01% of year [dB]")
    ax.grid(True, alpha=GRID_ALPHA)
    ax.legend(loc="best")
    return _save_figure(fig, output_dir / "26_itu_rain_attenuation_vs_frequency.png")


def plot_specific_rain_attenuation(scenario: ScenarioConfig, output_dir: Path) -> Path:
    """Plot ITU-R P.838 specific rain attenuation gamma_R vs rain rate."""

    cfg = scenario.itu_propagation
    gs1 = scenario.uplink.transmitter.location
    gs2 = scenario.downlink.receiver.location
    uplink_geom = calculate_geo_link_geometry(gs1, scenario.satellite)
    downlink_geom = calculate_geo_link_geometry(gs2, scenario.satellite)
    rates = np.linspace(1.0, 100.0, 160)

    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    for label, f_hz, elevation_deg in (
        (
            f"uplink {scenario.uplink.frequency_hz / GHZ:.1f} GHz",
            scenario.uplink.frequency_hz,
            uplink_geom.elevation_deg,
        ),
        (
            f"downlink {scenario.downlink.frequency_hz / GHZ:.1f} GHz",
            scenario.downlink.frequency_hz,
            downlink_geom.elevation_deg,
        ),
    ):
        k, alpha = itu.rain_coefficients_p838(
            f_hz / GHZ,
            elevation_deg,
            cfg.polarization_tilt_deg,
        )
        gamma = np.array([itu.rain_specific_attenuation_db_per_km(float(r), k, alpha) for r in rates])
        ax.plot(rates, gamma, linewidth=LINE_WIDTH, label=f"{label}  (k = {k:.4f}, alpha = {alpha:.3f})")
    ax.axvline(cfg.rain_rate_001_mm_per_h, linestyle="--", linewidth=THIN_LINE_WIDTH, color=THRESHOLD_COLOR,
               label=f"R0.01 = {cfg.rain_rate_001_mm_per_h:g} mm/h")

    ax.set_xlabel("Rain rate R [mm/h]")
    ax.set_ylabel("Specific attenuation gamma_R [dB/km]")
    ax.grid(True, alpha=GRID_ALPHA)
    ax.legend(loc="best")
    return _save_figure(fig, output_dir / "27_itu_specific_rain_attenuation.png")


def plot_dvbs2_modcod_ladder(scenario: ScenarioConfig, output_dir: Path) -> Path:
    """Plot the DVB-S2 MODCOD ladder and mark the selected ACM operating point."""

    design = calculate_scenario_with_itu(scenario)
    ordered_modcods = sorted(DVB_S2_MODCODS, key=lambda item: item.required_esn0_db)
    esn0 = np.array([m.required_esn0_db for m in ordered_modcods], dtype=float)
    eff = np.array([m.spectral_efficiency_bps_hz for m in ordered_modcods], dtype=float)

    fig, ax = plt.subplots(figsize=(8.8, 5.4))
    ax.fill_between(esn0, eff, step="post", color="#3498db", alpha=0.2)
    ax.step(esn0, eff, where="post", linewidth=2.0, color="#2980b9", alpha=0.9)
    ax.scatter(esn0, eff, s=30, color="#2c3e50", zorder=4, label="DVB-S2 MODCODs")

    sel = design.downlink_modcod
    if sel is not None and sel.selected is not None:
        ax.axvline(sel.available_esn0_db, linestyle="--", linewidth=1.5, color="#27ae60",
                   label=rf"available $E_s/N_0$ = {sel.available_esn0_db:.2f} dB")
        ax.scatter([sel.selected.required_esn0_db], [sel.spectral_efficiency_bps_hz], marker="*", s=350,
                   color="#e74c3c", edgecolors="#c0392b", linewidths=1.2, zorder=6,
                   label=f"selected {sel.selected.name} ({sel.spectral_efficiency_bps_hz:.2f} bit/s/Hz)")

    ax.set_xlabel(r"Required $E_s/N_0$ for QEF on AWGN [dB]")
    ax.set_ylabel("Spectral efficiency [bit/s/Hz]")
    ax.grid(True, alpha=GRID_ALPHA)
    ax.legend(loc="best")
    return _save_figure(fig, output_dir / "28_dvbs2_modcod_ladder.png")


def plot_dvbs2_acm_vs_availability(
    itu_curve: list[ITUPropagationResult],
    output_dir: Path,
    design_availability_percent: float | None = None,
) -> Path:
    """Plot ACM response for the coincident dual-site stress sweep.

    As the availability target increases, the deeper ITU-R fade forces the ACM
    selector to a more robust (lower-efficiency) MODCOD, reducing net throughput.
    Points where no MODCOD closes appear as zero throughput.
    """

    availability = np.array([r.design_availability_percent for r in itu_curve], dtype=float)

    def _eff(result: ITUPropagationResult) -> float:
        sel = result.downlink_modcod
        return sel.spectral_efficiency_bps_hz if (sel is not None and sel.selected is not None) else 0.0

    def _throughput(result: ITUPropagationResult) -> float:
        sel = result.downlink_modcod
        return (sel.net_throughput_bps / 1.0e6) if (sel is not None and sel.selected is not None) else 0.0

    throughput = np.array([_throughput(r) for r in itu_curve], dtype=float)
    efficiency = np.array([_eff(r) for r in itu_curve], dtype=float)

    fig, ax = plt.subplots(figsize=FIGSIZE_LINE)
    ax.fill_between(availability, throughput, color="#3498db", alpha=0.15, label="_nolegend_")
    ax.plot(availability, throughput, linewidth=2.5, marker="o", markersize=MARKER_SIZE+1,
            color="#2980b9", label="net throughput")
    ax.set_xlabel("Per-path non-exceedance [%]; coincident dual-site stress")
    ax.set_ylabel("Net throughput [Mbit/s]", color="#2980b9", fontweight="bold")
    ax.tick_params(axis="y", labelcolor="#2980b9")

    ax2 = ax.twinx()
    ax2.plot(availability, efficiency, linewidth=2.0, linestyle="--", marker="s", markersize=MARKER_SIZE,
             color="#27ae60", label="spectral efficiency")
    ax2.set_ylabel("Spectral efficiency [bit/s/Hz]", color="#27ae60", fontweight="bold")
    ax2.tick_params(axis="y", labelcolor="#27ae60")
    ax2.spines["right"].set_visible(True)
    ax2.spines["right"].set_color("#27ae60")

    if design_availability_percent is not None:
        ax.axvline(design_availability_percent, linestyle=":", linewidth=1.6, color=BASELINE_COLOR,
                   label=f"design = {design_availability_percent:g}%")


    ax.grid(True, alpha=GRID_ALPHA)
    handles1, labels1 = ax.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(handles1 + handles2, labels1 + labels2, loc="best")
    return _save_figure(fig, output_dir / "29_dvbs2_acm_vs_availability.png")


def generate_itu_plots(
    scenario: ScenarioConfig,
    itu_curve: list[ITUPropagationResult],
    output_dir: Path,
) -> list[Path]:
    """Generate the ITU-R propagation and DVB-S2 ACM figures.

    Returns an empty list when ITU-R propagation is disabled. The DVB-S2 figures
    mark the operating point of the ITU-faded downlink, so they are only drawn
    when both ITU-R propagation and the ACM layer are enabled.
    """

    if not scenario.itu_propagation.enabled or not itu_curve:
        return []

    _prepare_output_dir(output_dir)
    design_p = scenario.itu_propagation.design_exceedance_percent
    design_av = scenario.itu_propagation.design_availability_percent
    paths = [
        plot_itu_attenuation_vs_availability(itu_curve, output_dir, design_p),
        plot_itu_margin_vs_availability(itu_curve, output_dir, design_av),
        plot_itu_attenuation_breakdown_bar(scenario, output_dir),
        plot_rain_attenuation_vs_frequency(scenario, output_dir),
        plot_specific_rain_attenuation(scenario, output_dir),
    ]
    if scenario.modcod.enabled:
        paths.append(plot_dvbs2_modcod_ladder(scenario, output_dir))
        paths.append(plot_dvbs2_acm_vs_availability(itu_curve, output_dir, design_av))
    return paths
