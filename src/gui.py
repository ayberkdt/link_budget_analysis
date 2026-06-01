import sys
import os
import re
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QMessageBox, QFrame,
    QStackedWidget, QListWidget, QDoubleSpinBox, QScrollArea, QAbstractButton
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QRectF, QPropertyAnimation, pyqtProperty
from PyQt6.QtGui import QFont, QColor, QPainter, QCursor, QPen
import subprocess

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
        "id": "APPARENT_MOTION",
        "title": "Apparent Motion",
        "desc": "Simulates the daily drift of the geostationary satellite within its station-keeping box (typically ±0.05° to ±0.1°). This affects slant range, elevation angle, and free-space path loss continuously over the specified duration.",
        "params": [
            {"key": "enabled", "type": "bool", "label": "Enable Module"},
            {"key": "duration_hours", "type": "float", "label": "Duration (hours)", "min": 1, "max": 72},
            {"key": "step_minutes", "type": "float", "label": "Step Size (minutes)", "min": 1, "max": 60},
            {"key": "east_west_amplitude_deg", "type": "float", "label": "East-West Amp (°)", "min": 0, "max": 1},
            {"key": "north_south_amplitude_deg", "type": "float", "label": "North-South Amp (°)", "min": 0, "max": 1},
        ]
    },
    {
        "id": "INTERFERENCE",
        "title": "Interference Model",
        "desc": "Models Adjacent Satellite Interference (ASI) and Intermodulation (IMD) noise. ASI depends on the separation angles to neighboring satellites on the geostationary arc. IMD represents internal transponder non-linearities.",
        "params": [
            {"key": "enabled", "type": "bool", "label": "Enable Module"},
            {"key": "adjacent_activity_factor_db", "type": "float", "label": "Adjacent Activity Factor (dB)", "min": -20, "max": 0},
            {"key": "imd_c_i_db", "type": "float", "label": "Intermodulation C/I (dB)", "min": 0, "max": 40},
        ]
    },
    {
        "id": "DYNAMIC_NOISE",
        "title": "Dynamic Noise",
        "desc": "A refined antenna noise temperature model accounting for low-elevation ground spillover, internal LNB noise, and emission noise from rain clouds. This replaces the static 150K assumption.",
        "params": [
            {"key": "enabled", "type": "bool", "label": "Enable Module"},
            {"key": "receiver_internal_noise_k", "type": "float", "label": "LNB Internal Noise (K)", "min": 10, "max": 300},
            {"key": "clear_sky_base_noise_k", "type": "float", "label": "Clear-Sky Sky Noise (K)", "min": 10, "max": 300},
            {"key": "rain_emission_temperature_k", "type": "float", "label": "Rain Emission Temp (K)", "min": 200, "max": 300},
        ]
    },
    {
        "id": "RAIN_OUTAGE",
        "title": "Rain Outage (Stochastic)",
        "desc": "A basic stochastic model for rain fade events over a year, assigning probability states (Clear, Light, Moderate, Heavy) to randomize the channel. Useful for Monte Carlo availability studies.",
        "params": [
            {"key": "enabled", "type": "bool", "label": "Enable Module"},
            {"key": "light_rain_probability", "type": "float", "label": "Light Rain Prob.", "min": 0, "max": 1},
            {"key": "moderate_rain_probability", "type": "float", "label": "Moderate Rain Prob.", "min": 0, "max": 1},
            {"key": "heavy_rain_probability", "type": "float", "label": "Heavy Rain Prob.", "min": 0, "max": 1},
        ]
    },
    {
        "id": "ITU_PROPAGATION",
        "title": "ITU-R P.618 Propagation",
        "desc": "The rigorous standard for satellite link design. Computes exact gaseous attenuation, cloud attenuation, rain fade, and tropospheric scintillation based on local meteorology and availability targets.",
        "params": [
            {"key": "enabled", "type": "bool", "label": "Enable Module"},
            {"key": "rain_rate_001_mm_per_h", "type": "float", "label": "R0.01 Rain Rate (mm/h)", "min": 0, "max": 150},
            {"key": "design_availability_percent", "type": "float", "label": "Target Availability (%)", "min": 90, "max": 99.999},
            {"key": "surface_temperature_c", "type": "float", "label": "Surface Temp (°C)", "min": -50, "max": 60},
            {"key": "water_vapour_density_g_m3", "type": "float", "label": "Water Vapour (g/m³)", "min": 0, "max": 30},
        ]
    },
    {
        "id": "MODCOD",
        "title": "DVB-S2 ACM",
        "desc": "Adaptive Coding and Modulation (ACM). Dynamically adapts the modulation (QPSK, 8PSK, 16APSK, 32APSK) and FEC rate to maximize throughput without dropping the link during rain fades.",
        "params": [
            {"key": "enabled", "type": "bool", "label": "Enable Module"},
            {"key": "rolloff_factor", "type": "float", "label": "Roll-off Factor", "min": 0, "max": 1},
            {"key": "implementation_margin_db", "type": "float", "label": "Implementation Margin (dB)", "min": 0, "max": 5},
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

class RunThread(QThread):
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    
    def run(self):
        try:
            process = subprocess.Popen(
                ["python", MAIN_SCRIPT],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8"
            )
            for line in process.stdout:
                self.output_signal.emit(line)
            process.wait()
            if process.returncode == 0:
                self.finished_signal.emit(True, "Analysis completed successfully. Check the outputs folder.")
            else:
                self.finished_signal.emit(False, f"Analysis failed:\nExit code {process.returncode}")
        except Exception as e:
            self.finished_signal.emit(False, f"Analysis failed:\n{e}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spacecraft Engineering Dashboard")
        self.resize(1000, 700)
        
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
            print("Error loading:", SCENARIO_FILE)
            return
        with open(SCENARIO_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            
        for page in PAGES:
            mod_id = page["id"]
            pattern = rf"{mod_id}\s*=\s*{{(.*?)\}}"
            match = re.search(pattern, content, re.DOTALL)
            if match:
                mod_body = match.group(1)
                for param in page["params"]:
                    k = param["key"]
                    v_pattern = rf"\"{k}\"\s*:\s*([^,\n]+)"
                    v_match = re.search(v_pattern, mod_body)
                    if v_match:
                        val_str = v_match.group(1).strip()
                        if param["type"] == "bool":
                            self.config_state[f"{mod_id}.{k}"] = (val_str == "True")
                        elif param["type"] == "float":
                            try:
                                self.config_state[f"{mod_id}.{k}"] = float(val_str)
                            except ValueError:
                                pass

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
            
            for param in page["params"]:
                row = QHBoxLayout()
                lbl = QLabel(param["label"])
                lbl.setStyleSheet("font-size: 14px; border: none; background: transparent;")
                row.addWidget(lbl)
                
                row.addStretch()
                
                val = self.config_state.get(f"{page['id']}.{param['key']}", param.get("min", 0))
                
                if param["type"] == "bool":
                    w = ToggleSwitch()
                    w.setChecked(bool(val))
                    w.pos = 1.0 if val else 0.0
                    self.widget_map[f"{page['id']}.{param['key']}"] = w
                    row.addWidget(w)
                elif param["type"] == "float":
                    w = QDoubleSpinBox()
                    w.setRange(param.get("min", -999), param.get("max", 99999))
                    w.setDecimals(4)
                    w.setValue(float(val))
                    w.setStyleSheet(f"""
                        QDoubleSpinBox {{
                            background: {THEME['bg_entry']}; color: {THEME['fg_main']};
                            border: 1px solid {THEME['border']}; border-radius: 6px;
                            padding: 6px 10px; font-size: 11pt; min-width: 120px;
                        }}
                        QDoubleSpinBox:focus {{ border: 1px solid {THEME['accent']}; }}
                        QDoubleSpinBox:hover {{ border: 1px solid {THEME['accent_hov']}; }}
                    """)
                    w.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
                    self.widget_map[f"{page['id']}.{param['key']}"] = w
                    row.addWidget(w)
                
                card_layout.addLayout(row)
                
            vbox.addWidget(card)
            vbox.addStretch()
            container.setLayout(vbox)
            scroll.setWidget(container)
            self.stack.addWidget(scroll)
            
        main_layout.addWidget(self.stack)

    def change_page(self, idx):
        self.stack.setCurrentIndex(idx)

    def save_settings(self):
        if not os.path.exists(SCENARIO_FILE):
            QMessageBox.critical(self, "Error", "Failed to save settings:\nscenario_inputs.py not found.")
            return
            
        with open(SCENARIO_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        for page in PAGES:
            mod_id = page["id"]
            pattern = rf"({mod_id}\s*=\s*{{)(.*?)(\}})"
            match = re.search(pattern, content, re.DOTALL)
            if match:
                mod_body = match.group(2)
                for param in page["params"]:
                    k = param["key"]
                    w = self.widget_map[f"{mod_id}.{k}"]
                    
                    if param["type"] == "bool":
                        val_str = "True" if w.isChecked() else "False"
                    else:
                        val_str = str(w.value())
                    
                    v_pattern = rf"(\"{k}\"\s*:\s*)[^,\n]+"
                    mod_body = re.sub(v_pattern, rf"\g<1>{val_str}", mod_body)
                    
                content = content[:match.start(2)] + mod_body + content[match.end(2):]

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
        
        self.thread = RunThread()
        self.thread.finished_signal.connect(self.on_run_finished)
        self.thread.start()

    def on_run_finished(self, success, msg):
        self.btn_run.setText("Run Analysis")
        self.btn_run.setEnabled(True)
        if success:
            QMessageBox.information(self, "Success", msg)
        else:
            QMessageBox.critical(self, "Error", msg)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())