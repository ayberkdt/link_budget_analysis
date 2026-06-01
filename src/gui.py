import sys
import os
import re
import math
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QMessageBox, QFrame,
    QStackedWidget, QListWidget, QLineEdit, QDoubleSpinBox, QScrollArea, QAbstractButton
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QRectF, QPropertyAnimation, pyqtProperty
from PyQt6.QtGui import QFont, QColor, QPainter, QCursor, QPen

SCENARIO_FILE = os.path.join(os.path.dirname(__file__), "scenario_inputs.py")
MAIN_SCRIPT = os.path.join(os.path.dirname(__file__), "main.py")

THEME = {
    "bg_space":    "#070B14",
    "bg_shell":    "#0B1220",
    "bg_card":     "#101A2B",
    "bg_card_alt": "#17243A",
    "bg_entry":    "#0D1626",
    "fg_main":     "#E6EDF7",
    "fg_soft":     "#BFD2EA",
    "fg_muted":    "#7F91AC",
    "accent":      "#35D0FF",
    "accent_hov":  "#7CE7FF",
    "accent_dim":  "rgba(53,208,255,0.13)",
    "secondary":   "#8B7CFF",
    "secondary_dim": "rgba(139,124,255,0.13)",
    "border":      "#26364F",
    "border_soft": "#1A2940",
    "success":     "#2DD4BF",
    "info":        "#F6C177",
    "text_disabled": "rgba(127,145,172,0.45)"
}

PAGES = [
    {
        "id": "PAGE_TOPOLOGY",
        "title": "Network Topology",
        "desc": "Configure the geographical locations and primary hardware of the ground stations and satellite.",
        "modules": [
            {
                "id": "GS1",
                "title": "Ground Station 1 (Uplink)",
                "desc": "The transmitting station sending the signal up to the satellite.",
                "params": [
                    {"key": "GS1['terminal_name']", "type": "str", "label": "Terminal Name", "help": "Identifier for the uplink site", "default": "Rome Broadcast TX"},
                    {"key": "GS1['site_name']", "type": "str", "label": "Site Name", "help": "City or geographical location", "default": "Rome, Italy"},
                    {"key": "GS1['latitude_deg']", "type": "float", "label": "Latitude (deg)", "help": "North positive, South negative (-90 to 90)", "min": -90.0, "max": 90.0, "default": 41.9028},
                    {"key": "GS1['longitude_deg']", "type": "float", "label": "Longitude (deg)", "help": "East positive, West negative (-180 to 180)", "min": -180.0, "max": 180.0, "default": 12.4964},
                    {"key": "GS1['antenna_diameter_m']", "type": "float", "label": "Antenna Diameter (m)", "help": "Parabolic dish physical diameter", "min": 0.5, "max": 15.0, "default": 2.4},
                    {"key": "GS1['tx_power_w']", "type": "float", "label": "HPA TX Power (W)", "help": "High Power Amplifier output in Watts", "min": 1.0, "max": 5000.0, "default": 20.0},
                ]
            },
            {
                "id": "SAT",
                "title": "Geostationary Satellite",
                "desc": "The bent-pipe space segment.",
                "params": [
                    {"key": "SATELLITE['name']", "type": "str", "label": "Satellite Name", "help": "Common name of the spacecraft", "default": "Eutelsat Hotbird 13G"},
                    {"key": "SATELLITE['longitude_deg']", "type": "float", "label": "Longitude (deg)", "help": "Orbital slot in the GEO arc (East positive)", "min": -180.0, "max": 180.0, "default": 13.0},
                ]
            },
            {
                "id": "GS2",
                "title": "Ground Station 2 (Downlink)",
                "desc": "The receiving earth station.",
                "params": [
                    {"key": "GS2['terminal_name']", "type": "str", "label": "Terminal Name", "help": "Identifier for the downlink site", "default": "Ankara Receive RX"},
                    {"key": "GS2['site_name']", "type": "str", "label": "Site Name", "help": "City or geographical location", "default": "Ankara, Turkey"},
                    {"key": "GS2['latitude_deg']", "type": "float", "label": "Latitude (deg)", "help": "North positive, South negative (-90 to 90)", "min": -90.0, "max": 90.0, "default": 39.9334},
                    {"key": "GS2['longitude_deg']", "type": "float", "label": "Longitude (deg)", "help": "East positive, West negative (-180 to 180)", "min": -180.0, "max": 180.0, "default": 32.8597},
                    {"key": "GS2['antenna_diameter_m']", "type": "float", "label": "Antenna Diameter (m)", "help": "Parabolic dish physical diameter", "min": 0.3, "max": 10.0, "default": 0.9},
                ]
            }
        ]
    },
    {
        "id": "PAGE_PROPAGATION",
        "title": "Atmospheric Propagation",
        "desc": "Configure ITU-R P.618 rain fading, Monte-Carlo statistics, and adaptive DVB-S2 ACM.",
        "modules": [
            {
                "id": "ITU_PROPAGATION",
                "title": "ITU-R P.618 Propagation",
                "desc": "The rigorous standard for satellite link design. Computes exact gaseous attenuation, cloud attenuation, rain fade, and tropospheric scintillation based on local meteorology and availability targets.",
                "params": [
                    {"key": "enabled", "type": "bool", "label": "Enable Module", "help": "Toggle the ITU-R empirical models"},
                    {"key": "rain_rate_001_mm_per_h", "type": "float", "label": "R0.01 Rain Rate (mm/h)", "help": "Rain intensity exceeded 0.01% of an average year", "min": 0, "max": 150},
                    {"key": "design_availability_percent", "type": "float", "label": "Target Availability (%)", "help": "Link availability requirement (e.g., 99.9%)", "min": 90, "max": 99.999},
                    {"key": "surface_temperature_c", "type": "float", "label": "Surface Temp (°C)", "help": "Average ground temperature", "min": -50, "max": 60},
                    {"key": "water_vapour_density_g_m3", "type": "float", "label": "Water Vapour (g/m³)", "help": "Average atmospheric water vapour density", "min": 0, "max": 30},
                ]
            },
            {
                "id": "RAIN_OUTAGE",
                "title": "Rain Outage (Stochastic)",
                "desc": "A basic stochastic model for rain fade events over a year, assigning probability states (Clear, Light, Moderate, Heavy) to randomize the channel. Useful for Monte Carlo availability studies.",
                "params": [
                    {"key": "enabled", "type": "bool", "label": "Enable Module", "help": "Toggle Monte Carlo state simulations"},
                    {"key": "light_rain_probability", "type": "float", "label": "Light Rain Prob.", "help": "Probability of light rain occurrence", "min": 0, "max": 1},
                    {"key": "moderate_rain_probability", "type": "float", "label": "Moderate Rain Prob.", "help": "Probability of moderate rain occurrence", "min": 0, "max": 1},
                    {"key": "heavy_rain_probability", "type": "float", "label": "Heavy Rain Prob.", "help": "Probability of heavy rain occurrence", "min": 0, "max": 1},
                ]
            },
            {
                "id": "MODCOD",
                "title": "DVB-S2 ACM",
                "desc": "Adaptive Coding and Modulation (ACM). Dynamically adapts the modulation (QPSK, 8PSK, 16APSK, 32APSK) and FEC rate to maximize throughput without dropping the link during rain fades.",
                "params": [
                    {"key": "enabled", "type": "bool", "label": "Enable Module", "help": "Enable dynamic MODCOD selection"},
                    {"key": "rolloff_factor", "type": "float", "label": "Roll-off Factor", "help": "Pulse shaping roll-off (e.g., 0.20 or 0.25)", "min": 0, "max": 1},
                    {"key": "implementation_margin_db", "type": "float", "label": "Implementation Margin (dB)", "help": "Hardware non-ideality losses", "min": 0, "max": 5},
                ]
            }
        ]
    },
    {
        "id": "PAGE_IMPAIRMENTS",
        "title": "Advanced Impairments",
        "desc": "Configure interference, orbital drift, and dynamic noise.",
        "modules": [
            {
                "id": "INTERFERENCE",
                "title": "Interference Model",
                "desc": "Models Adjacent Satellite Interference (ASI) and Intermodulation (IMD) noise. ASI depends on the separation angles to neighboring satellites on the geostationary arc. IMD represents internal transponder non-linearities.",
                "params": [
                    {"key": "enabled", "type": "bool", "label": "Enable Module", "help": "Include interference noise in total C/(N+I)"},
                    {"key": "adjacent_activity_factor_db", "type": "float", "label": "Adjacent Activity Factor (dB)", "help": "Back-off due to adjacent satellite usage", "min": -20, "max": 0},
                    {"key": "imd_c_i_db", "type": "float", "label": "Intermodulation C/I (dB)", "help": "Carrier-to-Intermodulation ratio generated inside transponder", "min": 0, "max": 40},
                ]
            },
            {
                "id": "DYNAMIC_NOISE",
                "title": "Dynamic Noise",
                "desc": "A refined antenna noise temperature model accounting for low-elevation ground spillover, internal LNB noise, and emission noise from rain clouds. This replaces the static 150K assumption.",
                "params": [
                    {"key": "enabled", "type": "bool", "label": "Enable Module", "help": "Calculate real-time Tsys based on weather"},
                    {"key": "receiver_internal_noise_k", "type": "float", "label": "LNB Internal Noise (K)", "help": "Noise temperature of the Low Noise Block", "min": 10, "max": 300},
                    {"key": "clear_sky_base_noise_k", "type": "float", "label": "Clear-Sky Sky Noise (K)", "help": "Baseline galactic and atmospheric noise", "min": 10, "max": 300},
                    {"key": "rain_emission_temperature_k", "type": "float", "label": "Rain Emission Temp (K)", "help": "Effective medium temperature during rain", "min": 200, "max": 300},
                ]
            },
            {
                "id": "APPARENT_MOTION",
                "title": "Apparent Motion",
                "desc": "Simulates the daily drift of the geostationary satellite within its station-keeping box (typically ±0.05° to ±0.1°). This affects slant range, elevation angle, and free-space path loss continuously over the specified duration.",
                "params": [
                    {"key": "enabled", "type": "bool", "label": "Enable Module", "help": "Simulate satellite drifting over time"},
                    {"key": "duration_hours", "type": "float", "label": "Duration (hours)", "help": "Length of the orbital simulation", "min": 1, "max": 72},
                    {"key": "step_minutes", "type": "float", "label": "Step Size (minutes)", "help": "Time resolution of the simulation", "min": 1, "max": 60},
                    {"key": "east_west_amplitude_deg", "type": "float", "label": "East-West Amp (°)", "help": "Longitudinal station-keeping limits", "min": 0, "max": 1},
                    {"key": "north_south_amplitude_deg", "type": "float", "label": "North-South Amp (°)", "help": "Latitudinal orbital inclination", "min": 0, "max": 1},
                ]
            }
        ]
    }
]

class ToggleSwitch(QAbstractButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(46, 24)
        self._pos = 0.0
        self.anim = QPropertyAnimation(self, b"pos", self)
        self.anim.setDuration(200)
        self.toggled.connect(self.start_anim)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Modern On/Off Switch adapted from Lunar Simulation.")

    @pyqtProperty(float)
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, value):
        self._pos = value
        self.update()

    def start_anim(self, checked):
        self.anim.setEndValue(1.0 if checked else 0.0)
        self.anim.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        rect = QRectF(0, 0, self.width(), self.height())
        if self.isChecked():
            p.setBrush(QColor(THEME["accent"]))
        else:
            p.setBrush(QColor(THEME["border"]))
        p.drawRoundedRect(rect, 12, 12)
        p.setBrush(QColor(THEME["fg_main"]))
        x = 2 + self._pos * (self.width() - 24)
        p.drawEllipse(QRectF(x, 2, 20, 20))

class RunnerThread(QThread):
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    
    def run(self):
        process = subprocess.Popen(
            [sys.executable, MAIN_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8'
        )
        for line in process.stdout:
            self.output_signal.emit(line)
        process.wait()
        self.finished_signal.emit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spacecraft Engineering Dashboard")
        self.resize(1100, 800)
        
        self.config_state = {}
        self.widget_map = {}
        
        self.setStyleSheet(f"""
            QMainWindow, QWidget#centralRoot {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 {THEME['bg_space']},
                    stop: 0.48 {THEME['bg_shell']},
                    stop: 1 #0F1A2E
                );
                color: {THEME['fg_main']};
                font-family: "Segoe UI", "Inter", sans-serif;
            }}
            QScrollArea, QStackedWidget {{
                background: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{ background: transparent; }}
        """)
        
        self.load_current_config()
        self.init_ui()

    def load_current_config(self):
        if not os.path.exists(SCENARIO_FILE):
            return
        with open(SCENARIO_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            
        for page in PAGES:
            for mod in page["modules"]:
                mod_id = mod["id"]
                # First try matching dictionary pattern: MOD_ID = { ... }
                pattern_dict = rf"{mod_id}\s*=\s*{{(.*?)\}}"
                match_dict = re.search(pattern_dict, content, re.DOTALL)
                
                if match_dict:
                    mod_body = match_dict.group(1)
                    for param in mod["params"]:
                        k = param["key"]
                        if "['enabled']" in k:
                            k_clean = "enabled"
                        else:
                            k_clean = k
                        
                        v_pattern = rf"\"{k_clean}\"\s*:\s*([^,\n]+)"
                        v_match = re.search(v_pattern, mod_body)
                        if v_match:
                            val_str = v_match.group(1).split("#")[0].strip()
                            if param["type"] == "bool":
                                self.config_state[f"{mod_id}.{k_clean}"] = (val_str == "True")
                            elif param["type"] == "float":
                                try:
                                    self.config_state[f"{mod_id}.{k_clean}"] = float(val_str)
                                except: pass
                                
                # Also try matching specific dictionary keys directly for Topology (GS1['name'] = ...)
                for param in mod["params"]:
                    key = param["key"]
                    if "['" in key and mod_id not in ["ITU_PROPAGATION", "RAIN_OUTAGE", "MODCOD", "INTERFERENCE", "DYNAMIC_NOISE", "APPARENT_MOTION"]:
                        dict_part, key_part = key.split("['")
                        key_part = key_part.replace("']", "")
                        
                        pattern = rf"{dict_part}\s*\[\s*['\"]{key_part}['\"]\s*\]\s*=\s*(.*)"
                        match = re.search(pattern, content)
                        if match:
                            val_str = match.group(1).split(",")[0].split("#")[0].strip()
                            if param["type"] == "str":
                                val = val_str.strip("'\"")
                                self.config_state[key] = val
                            elif param["type"] == "float":
                                try:
                                    self.config_state[key] = float(val_str)
                                except: pass
                            elif param["type"] == "bool":
                                self.config_state[key] = (val_str == "True")

    def init_ui(self):
        centralRoot = QWidget()
        centralRoot.setObjectName("centralRoot")
        self.setCentralWidget(centralRoot)
        
        main_layout = QHBoxLayout(centralRoot)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(260)
        sidebar.setStyleSheet(f"background: transparent; border-right: 1px solid {THEME['border_soft']};")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(20, 30, 20, 20)
        
        title_lbl = QLabel("Mission Modules")
        title_lbl.setStyleSheet(f"font-family: 'Segoe UI'; font-size: 14px; font-weight: bold; color: {THEME['fg_soft']}; letter-spacing: 0.5px;")
        side_layout.addWidget(title_lbl)
        
        self.nav_list = QListWidget()
        self.nav_list.setStyleSheet(f"""
            QListWidget {{
                border: none; background: transparent; outline: none;
            }}
            QListWidget::item {{
                padding: 12px 14px;
                margin-bottom: 6px;
                border-radius: 8px;
                color: {THEME['fg_muted']};
            }}
            QListWidget::item:hover {{
                background: {THEME['accent_dim']};
                color: {THEME['fg_main']};
            }}
            QListWidget::item:selected {{
                background: {THEME['secondary_dim']};
                font-weight: 700;
                border-left: 3px solid {THEME['accent']};
                color: {THEME['fg_main']};
            }}
        """)
        for i, page in enumerate(PAGES):
            self.nav_list.addItem(page["title"])
        self.nav_list.setCurrentRow(0)
        self.nav_list.currentRowChanged.connect(self.change_page)
        side_layout.addWidget(self.nav_list)
        
        side_layout.addStretch()
        
        lbl_presets = QLabel("Ablation Presets")
        lbl_presets.setStyleSheet(f"font-weight: bold; color: {THEME['fg_muted']}; border: none; font-size: 12px; margin-bottom: 5px;")
        side_layout.addWidget(lbl_presets)
        
        btn_static = QPushButton("Static Only")
        btn_static.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_static.setStyleSheet(f"""
            QPushButton {{
                background: {THEME['bg_card']}; border: 1px solid {THEME['border']}; color: {THEME['fg_soft']};
                border-radius: 4px; padding: 8px; font-weight: 500;
            }}
            QPushButton:hover {{ background: {THEME['bg_entry']}; }}
        """)
        btn_static.clicked.connect(self.set_preset_static)
        side_layout.addWidget(btn_static)
        
        btn_all = QPushButton("All Enabled")
        btn_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_all.setStyleSheet(f"""
            QPushButton {{
                background: {THEME['bg_card']}; border: 1px solid {THEME['border']}; color: {THEME['fg_soft']};
                border-radius: 4px; padding: 8px; font-weight: 500; margin-top: 5px;
            }}
            QPushButton:hover {{ background: {THEME['bg_entry']}; }}
        """)
        btn_all.clicked.connect(self.set_preset_all)
        side_layout.addWidget(btn_all)
        
        side_layout.addSpacing(20)
        
        self.btn_save = QPushButton("Save Settings")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background: {THEME['bg_card_alt']}; color: {THEME['fg_main']};
                border: 1px solid {THEME['border']}; border-radius: 8px; font-weight: 600; font-size: 11pt; padding: 12px;
            }}
            QPushButton:hover {{ background: {THEME['bg_entry']}; border-color: {THEME['accent_hov']}; }}
        """)
        self.btn_save.clicked.connect(self.save_settings)
        side_layout.addWidget(self.btn_save)
        
        self.btn_run = QPushButton("Run Analysis")
        self.btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_run.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {THEME['accent']}, stop:1 {THEME['secondary']});
                color: #05090F; border: none; border-radius: 8px; font-weight: 700; font-size: 11pt; padding: 12px;
            }}
            QPushButton:hover {{ background: {THEME['accent_hov']}; }}
            QPushButton:disabled {{ background: {THEME['text_disabled']}; }}
        """)
        self.btn_run.clicked.connect(self.run_simulation)
        side_layout.addWidget(self.btn_run)
        
        main_layout.addWidget(sidebar)
        
        # Content Area
        self.stack = QStackedWidget()
        
        for i, page in enumerate(PAGES):
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            container = QWidget()
            vbox = QVBoxLayout(container)
            vbox.setContentsMargins(40, 40, 40, 40)
            vbox.setSpacing(20)
            
            p_title = QLabel(page["title"])
            p_title.setStyleSheet(f"font-family: 'Segoe UI'; font-size: 28px; font-weight: bold; color: {THEME['fg_soft']};")
            vbox.addWidget(p_title)
            
            p_desc = QLabel(page["desc"])
            p_desc.setWordWrap(True)
            p_desc.setStyleSheet(f"font-size: 14px; color: {THEME['fg_muted']}; line-height: 1.4;")
            vbox.addWidget(p_desc)
            
            if page["title"] == "Network Topology":
                # Rome - Ankara reference panel
                ref_frame = QFrame()
                ref_frame.setStyleSheet(f"""
                    QFrame {{
                        background: {THEME['secondary_dim']};
                        border: 1px solid {THEME['secondary']};
                        border-radius: 8px;
                    }}
                    QLabel {{
                        color: {THEME['fg_main']};
                        font-size: 14px;
                    }}
                """)
                ref_layout = QVBoxLayout(ref_frame)
                ref_layout.setContentsMargins(15, 15, 15, 15)
                ref_lbl = QLabel("<b>Önerilen Referans Koordinatlar (Recommended Values)</b><br>"
                                 "Rome (GS1): 41.9028° N, 12.4964° E<br>"
                                 "Ankara (GS2): 39.9334° N, 32.8597° E<br>"
                                 "Eutelsat Hotbird 13G: 13.0° E")
                ref_layout.addWidget(ref_lbl)
                vbox.addWidget(ref_frame)

            for mod in page["modules"]:
                card = QFrame()
                card.setStyleSheet(f"""
                    QFrame {{
                        background: {THEME['bg_card']};
                        border: 1px solid {THEME['border']};
                        border-radius: 12px;
                    }}
                """)
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(25, 25, 25, 25)
                card_layout.setSpacing(15)
                
                m_title = QLabel(mod["title"])
                m_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {THEME['fg_main']}; border: none;")
                card_layout.addWidget(m_title)
                
                m_desc = QLabel(mod["desc"])
                m_desc.setWordWrap(True)
                m_desc.setStyleSheet(f"font-size: 13px; color: {THEME['fg_muted']}; border: none;")
                card_layout.addWidget(m_desc)
                
                for param in mod["params"]:
                    row = QHBoxLayout()
                    
                    # Parameter Label & Help text
                    lbl_box = QVBoxLayout()
                    lbl_box.setSpacing(2)
                    lbl = QLabel(param["label"])
                    lbl.setStyleSheet(f"font-size: 14px; font-weight: 500; color: {THEME['fg_main']}; border: none; background: transparent;")
                    lbl_box.addWidget(lbl)
                    
                    if "help" in param:
                        h_lbl = QLabel(param["help"])
                        h_lbl.setStyleSheet(f"font-size: 12px; color: {THEME['fg_muted']}; border: none; background: transparent;")
                        lbl_box.addWidget(h_lbl)
                        
                    row.addLayout(lbl_box)
                    row.addStretch()
                    
                    k = param["key"]
                    if "['enabled']" in k:
                        k_clean = "enabled"
                    else:
                        k_clean = k
                        
                    if "['" in k and mod["id"] not in ["ITU_PROPAGATION", "RAIN_OUTAGE", "MODCOD", "INTERFERENCE", "DYNAMIC_NOISE", "APPARENT_MOTION"]:
                        val = self.config_state.get(k, param.get("default", 0))
                        widget_key = k
                    else:
                        val = self.config_state.get(f"{mod['id']}.{k_clean}", param.get("min", 0))
                        widget_key = f"{mod['id']}.{k_clean}"
                    
                    if param["type"] == "bool":
                        w = ToggleSwitch()
                        w.setChecked(bool(val))
                        w.pos = 1.0 if val else 0.0
                        self.widget_map[widget_key] = w
                        row.addWidget(w)
                    elif param["type"] == "float":
                        w = QDoubleSpinBox()
                        w.setRange(param.get("min", -99999), param.get("max", 99999))
                        w.setDecimals(4)
                        w.setValue(float(val))
                        w.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
                        w.setStyleSheet(f"""
                            QDoubleSpinBox {{
                                background: {THEME['bg_entry']}; color: {THEME['fg_main']};
                                border: 1px solid {THEME['border']}; border-radius: 6px;
                                padding: 6px 10px; font-size: 11pt; min-width: 120px;
                            }}
                            QDoubleSpinBox:focus {{ border: 1px solid {THEME['accent']}; }}
                            QDoubleSpinBox:hover {{ border: 1px solid {THEME['accent_hov']}; }}
                        """)
                        self.widget_map[widget_key] = w
                        row.addWidget(w)
                    elif param["type"] == "str":
                        w = QLineEdit()
                        w.setText(str(val))
                        w.setMinimumWidth(250)
                        w.setStyleSheet(f"""
                            QLineEdit {{
                                background: {THEME['bg_entry']}; color: {THEME['fg_main']};
                                border: 1px solid {THEME['border']}; border-radius: 6px;
                                padding: 6px 10px; font-size: 11pt;
                            }}
                            QLineEdit:focus {{ border: 1px solid {THEME['accent']}; }}
                            QLineEdit:hover {{ border: 1px solid {THEME['accent_hov']}; }}
                        """)
                        self.widget_map[widget_key] = w
                        row.addWidget(w)
                    
                    card_layout.addLayout(row)
                    
                vbox.addWidget(card)
                
            if page["title"] == "Network Topology":
                btn_calc = QPushButton("Calculate Quick Metrics (Slant Range & Elevation)")
                btn_calc.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_calc.setStyleSheet(f"""
                    QPushButton {{
                        background: {THEME['bg_card_alt']};
                        border: 2px solid {THEME['accent']};
                        color: {THEME['accent']};
                        border-radius: 8px;
                        padding: 12px;
                        font-weight: bold;
                        font-size: 14px;
                    }}
                    QPushButton:hover {{
                        background: {THEME['accent_dim']};
                    }}
                """)
                btn_calc.clicked.connect(self.calculate_quick_metrics)
                vbox.addWidget(btn_calc)
                
                self.metrics_result_lbl = QLabel("")
                self.metrics_result_lbl.setStyleSheet(f"""
                    QLabel {{
                        background: {THEME['bg_card']};
                        border: 1px solid {THEME['border']};
                        border-radius: 8px;
                        padding: 15px;
                        font-size: 14px; 
                        color: {THEME['fg_main']}; 
                        line-height: 1.5;
                    }}
                """)
                self.metrics_result_lbl.hide()
                vbox.addWidget(self.metrics_result_lbl)
                
            vbox.addStretch()
            container.setLayout(vbox)
            scroll.setWidget(container)
            self.stack.addWidget(scroll)
            
        main_layout.addWidget(self.stack)

    def change_page(self, idx):
        self.stack.setCurrentIndex(idx)

    def set_preset_static(self):
        for k, w in self.widget_map.items():
            if isinstance(w, ToggleSwitch) and "enabled" in k:
                w.setChecked(False)

    def set_preset_all(self):
        for k, w in self.widget_map.items():
            if isinstance(w, ToggleSwitch) and "enabled" in k:
                w.setChecked(True)

    def calculate_quick_metrics(self):
        try:
            lat1 = self.widget_map["GS1['latitude_deg']"].value()
            lon1 = self.widget_map["GS1['longitude_deg']"].value()
            lat2 = self.widget_map["GS2['latitude_deg']"].value()
            lon2 = self.widget_map["GS2['longitude_deg']"].value()
            sat_lon = self.widget_map["SATELLITE['longitude_deg']"].value()
            
            def calc_slant(lat, lon, slon):
                lat_r = math.radians(lat)
                lon_r = math.radians(lon)
                slon_r = math.radians(slon)
                
                Re = 6378.137
                Rsat = 42164.0
                
                rx = Re * math.cos(lat_r) * math.cos(lon_r)
                ry = Re * math.cos(lat_r) * math.sin(lon_r)
                rz = Re * math.sin(lat_r)
                
                sx = Rsat * math.cos(slon_r)
                sy = Rsat * math.sin(slon_r)
                sz = 0
                
                dx = sx - rx
                dy = sy - ry
                dz = sz - rz
                slant = math.sqrt(dx*dx + dy*dy + dz*dz)
                
                ux = math.cos(lat_r)*math.cos(lon_r)
                uy = math.cos(lat_r)*math.sin(lon_r)
                uz = math.sin(lat_r)
                
                dot = (dx*ux + dy*uy + dz*uz) / slant
                el = math.degrees(math.asin(max(-1.0, min(1.0, dot))))
                return slant, el
                
            s1, e1 = calc_slant(lat1, lon1, sat_lon)
            s2, e2 = calc_slant(lat2, lon2, sat_lon)
            
            self.metrics_result_lbl.setText(f"<b>GS1 (Uplink)</b> &nbsp;&nbsp;&nbsp; Slant Range: {s1:.2f} km &nbsp;|&nbsp; Elevation: {e1:.2f}°<br>"
                                            f"<b>GS2 (Downlink)</b> &nbsp; Slant Range: {s2:.2f} km &nbsp;|&nbsp; Elevation: {e2:.2f}°")
            self.metrics_result_lbl.show()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not calculate metrics: {str(e)}")

    def save_settings(self):
        if not os.path.exists(SCENARIO_FILE):
            QMessageBox.warning(self, "Warning", "scenario_inputs.py not found.")
            return
            
        with open(SCENARIO_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        # Update dictionary-based modules
        for mod_id in ["ITU_PROPAGATION", "RAIN_OUTAGE", "MODCOD", "INTERFERENCE", "DYNAMIC_NOISE", "APPARENT_MOTION"]:
            pattern = rf"({mod_id}\s*=\s*{{)(.*?)(\}})"
            match = re.search(pattern, content, re.DOTALL)
            if match:
                mod_body = match.group(2)
                
                for k, w in self.widget_map.items():
                    if k.startswith(f"{mod_id}."):
                        param_key = k.split(".")[1]
                        
                        if isinstance(w, ToggleSwitch):
                            val_str = "True" if w.isChecked() else "False"
                        else:
                            val_str = str(w.value())
                        
                        v_pattern = rf"(\"{param_key}\"\s*:\s*)[^,\n]+"
                        mod_body = re.sub(v_pattern, rf"\g<1>{val_str}", mod_body)
                        
                content = content[:match.start(2)] + mod_body + content[match.end(2):]

        # Update Topology parameters
        for k, w in self.widget_map.items():
            if "['" in k and not any(k.startswith(m) for m in ["ITU_PROPAGATION", "RAIN_OUTAGE", "MODCOD", "INTERFERENCE", "DYNAMIC_NOISE", "APPARENT_MOTION"]):
                if isinstance(w, QDoubleSpinBox):
                    val = str(w.value())
                elif isinstance(w, QLineEdit):
                    val = f'"{w.text()}"'
                    
                dict_part, key_part = k.split("['")
                key_part = key_part.replace("']", "")
                pattern = rf"({dict_part}\s*\[\s*['\"]{key_part}['\"]\s*\]\s*=\s*)([^,#\n]*)"
                content = re.sub(pattern, rf"\g<1>{val}", content)

        with open(SCENARIO_FILE, "w", encoding="utf-8") as f:
            f.write(content)
            
        self.btn_save.setText("Saved ✓")
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background: {THEME['success']}; color: #05090F;
                border: none; border-radius: 8px; font-weight: 600; font-size: 11pt; padding: 12px;
            }}
        """)
        QThread.msleep(1000)
        self.btn_save.setText("Save Settings")
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background: {THEME['bg_card_alt']}; color: {THEME['fg_main']};
                border: 1px solid {THEME['border']}; border-radius: 8px; font-weight: 600; font-size: 11pt; padding: 12px;
            }}
            QPushButton:hover {{ background: {THEME['bg_entry']}; border-color: {THEME['accent_hov']}; }}
        """)

    def run_simulation(self):
        self.save_settings()
        self.btn_run.setText("Running...")
        self.btn_run.setEnabled(False)
        
        self.thread = RunnerThread()
        self.thread.finished_signal.connect(self.on_run_finished)
        self.thread.start()

    def on_run_finished(self):
        self.btn_run.setText("Run Analysis")
        self.btn_run.setEnabled(True)
        QMessageBox.information(self, "Success", "Analysis completed successfully. Check the outputs folder.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())