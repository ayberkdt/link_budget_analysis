import sys
import os
import re
import math
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QMessageBox, QFrame,
    QStackedWidget, QListWidget, QLineEdit, QDoubleSpinBox, QScrollArea, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QCursor

SCENARIO_FILE = os.path.join(os.path.dirname(__file__), "scenario_inputs.py")
MAIN_SCRIPT = os.path.join(os.path.dirname(__file__), "main.py")

PAGES = [
    {
        "page_title": "Network Topology",
        "page_desc": "Configure the geographical locations and primary hardware of the ground stations and satellite.",
        "modules": [
            {
                "id": "GS1",
                "title": "Ground Station 1 (Uplink)",
                "desc": "The transmitting station sending the signal up to the satellite.",
                "params": [
                    {"key": "GS1['terminal_name']", "type": "str", "label": "Terminal Name", "default": "Rome Broadcast TX"},
                    {"key": "GS1['site_name']", "type": "str", "label": "Site Name", "default": "Rome, Italy"},
                    {"key": "GS1['latitude_deg']", "type": "float", "label": "Latitude (deg)", "min": -90.0, "max": 90.0, "default": 41.9028},
                    {"key": "GS1['longitude_deg']", "type": "float", "label": "Longitude (deg)", "min": -180.0, "max": 180.0, "default": 12.4964},
                    {"key": "GS1['antenna_diameter_m']", "type": "float", "label": "Antenna Diameter (m)", "min": 0.5, "max": 15.0, "default": 2.4},
                    {"key": "GS1['tx_power_w']", "type": "float", "label": "HPA TX Power (W)", "min": 1.0, "max": 5000.0, "default": 20.0},
                ]
            },
            {
                "id": "SAT",
                "title": "Geostationary Satellite",
                "desc": "The bent-pipe space segment.",
                "params": [
                    {"key": "SATELLITE['name']", "type": "str", "label": "Satellite Name", "default": "Eutelsat Hotbird 13G"},
                    {"key": "SATELLITE['longitude_deg']", "type": "float", "label": "Longitude (deg)", "min": -180.0, "max": 180.0, "default": 13.0},
                ]
            },
            {
                "id": "GS2",
                "title": "Ground Station 2 (Downlink)",
                "desc": "The receiving earth station.",
                "params": [
                    {"key": "GS2['terminal_name']", "type": "str", "label": "Terminal Name", "default": "Ankara Receive RX"},
                    {"key": "GS2['site_name']", "type": "str", "label": "Site Name", "default": "Ankara, Turkey"},
                    {"key": "GS2['latitude_deg']", "type": "float", "label": "Latitude (deg)", "min": -90.0, "max": 90.0, "default": 39.9334},
                    {"key": "GS2['longitude_deg']", "type": "float", "label": "Longitude (deg)", "min": -180.0, "max": 180.0, "default": 32.8597},
                    {"key": "GS2['antenna_diameter_m']", "type": "float", "label": "Antenna Diameter (m)", "min": 0.3, "max": 10.0, "default": 0.9},
                ]
            }
        ]
    },
    {
        "page_title": "Atmospheric Propagation",
        "page_desc": "Configure ITU-R P.618 rain fading, Monte-Carlo statistics, and adaptive DVB-S2 ACM.",
        "modules": [
            {
                "id": "MODELS",
                "title": "Propagation Models",
                "desc": "Toggle advanced atmospheric modeling features.",
                "params": [
                    {"key": "ITU_PROPAGATION['enabled']", "type": "bool", "label": "Enable ITU-R P.618 Model", "default": True},
                    {"key": "RAIN_OUTAGE['enabled']", "type": "bool", "label": "Enable Monte-Carlo Sim", "default": True},
                    {"key": "MODCOD['enabled']", "type": "bool", "label": "Enable DVB-S2 ACM", "default": True},
                ]
            }
        ]
    },
    {
        "page_title": "Advanced Impairments",
        "page_desc": "Configure interference, orbital drift, and dynamic noise.",
        "modules": [
            {
                "id": "IMPAIR",
                "title": "System Impairments",
                "desc": "Toggle physical layer impairments.",
                "params": [
                    {"key": "INTERFERENCE['enabled']", "type": "bool", "label": "Enable ASI & IMD", "default": True},
                    {"key": "DYNAMIC_NOISE['enabled']", "type": "bool", "label": "Enable Dynamic Tsys", "default": True},
                    {"key": "APPARENT_MOTION['enabled']", "type": "bool", "label": "Enable Orbital Drift", "default": True},
                    {"key": "DIGITAL['enabled']", "type": "bool", "label": "Calculate Digital BER", "default": True},
                ]
            }
        ]
    }
]

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

class ConfigApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spacecraft Link Budget Analyzer")
        self.resize(1050, 750)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F8F9FA;
            }
            QLabel {
                color: #212529;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        
        self.config_state = {}
        self.widget_map = {}
        
        self.load_current_config()
        self.init_ui()

    def load_current_config(self):
        if not os.path.exists(SCENARIO_FILE):
            return
        with open(SCENARIO_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            
        for page in PAGES:
            for mod in page["modules"]:
                for param in mod["params"]:
                    key = param["key"]
                    if "['" in key:
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
                                except:
                                    pass
                            elif param["type"] == "bool":
                                self.config_state[key] = (val_str == "True")
                    else:
                        pattern = rf"^{key}\s*=\s*(.*)"
                        match = re.search(pattern, content, re.MULTILINE)
                        if match:
                            val_str = match.group(1).split("#")[0].strip()
                            if param["type"] == "bool":
                                self.config_state[key] = (val_str == "True")

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # SIDEBAR
        sidebar = QWidget()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-right: 1px solid #DEE2E6;
            }
        """)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(20, 30, 20, 20)
        
        title_lbl = QLabel("Configuration")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #495057; border: none;")
        side_layout.addWidget(title_lbl)
        
        self.nav_list = QListWidget()
        self.nav_list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 12px 15px;
                border-radius: 6px;
                margin-bottom: 5px;
                color: #495057;
                font-size: 14px;
            }
            QListWidget::item:hover {
                background-color: #E9ECEF;
            }
            QListWidget::item:selected {
                background-color: #E7F1FF;
                color: #0D6EFD;
                font-weight: bold;
                border-left: 4px solid #0D6EFD;
            }
        """)
        for page in PAGES:
            self.nav_list.addItem(page["page_title"])
        self.nav_list.setCurrentRow(0)
        self.nav_list.currentRowChanged.connect(self.change_page)
        side_layout.addWidget(self.nav_list)
        
        side_layout.addStretch()
        
        # Ablation Presets
        lbl_presets = QLabel("Ablation Presets")
        lbl_presets.setStyleSheet("font-weight: bold; color: #6C757D; border: none; font-size: 12px; margin-bottom: 5px;")
        side_layout.addWidget(lbl_presets)
        
        btn_static = QPushButton("Static Only")
        btn_static.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_static.setStyleSheet("""
            QPushButton {
                background-color: #F8F9FA; border: 1px solid #CED4DA; color: #495057;
                border-radius: 4px; padding: 8px; font-weight: 500;
            }
            QPushButton:hover { background-color: #E2E6EA; }
        """)
        btn_static.clicked.connect(self.set_preset_static)
        side_layout.addWidget(btn_static)
        
        btn_all = QPushButton("All Enabled")
        btn_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_all.setStyleSheet("""
            QPushButton {
                background-color: #F8F9FA; border: 1px solid #CED4DA; color: #495057;
                border-radius: 4px; padding: 8px; font-weight: 500; margin-top: 5px;
            }
            QPushButton:hover { background-color: #E2E6EA; }
        """)
        btn_all.clicked.connect(self.set_preset_all)
        side_layout.addWidget(btn_all)

        main_layout.addWidget(sidebar)
        
        # MAIN CONTENT AREA
        content_area = QWidget()
        content_area.setStyleSheet("background-color: #F8F9FA;")
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        self.stack = QStackedWidget()
        
        for page in PAGES:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
            
            container = QWidget()
            container.setStyleSheet("background-color: transparent;")
            vbox = QVBoxLayout(container)
            vbox.setContentsMargins(40, 40, 40, 40)
            vbox.setSpacing(25)
            
            header = QLabel(page["page_title"])
            header.setStyleSheet("font-size: 26px; font-weight: bold; color: #212529;")
            vbox.addWidget(header)
            
            desc = QLabel(page["page_desc"])
            desc.setWordWrap(True)
            desc.setStyleSheet("font-size: 15px; color: #6C757D; margin-bottom: 10px;")
            vbox.addWidget(desc)

            if page["page_title"] == "Network Topology":
                # Rome - Ankara reference panel
                ref_frame = QFrame()
                ref_frame.setStyleSheet("""
                    QFrame {
                        background-color: #E7F1FF;
                        border: 1px solid #B6D4FE;
                        border-radius: 8px;
                    }
                    QLabel {
                        color: #084298;
                        font-size: 14px;
                    }
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
                mod_frame = QFrame()
                mod_frame.setStyleSheet("""
                    QFrame {
                        background-color: #FFFFFF;
                        border: 1px solid #DEE2E6;
                        border-radius: 10px;
                    }
                """)
                mod_layout = QVBoxLayout(mod_frame)
                mod_layout.setContentsMargins(25, 25, 25, 25)
                mod_layout.setSpacing(15)
                
                m_title = QLabel(mod["title"])
                m_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #212529; border: none;")
                mod_layout.addWidget(m_title)
                
                for param in mod["params"]:
                    row_layout = QHBoxLayout()
                    
                    lbl_layout = QVBoxLayout()
                    lbl_layout.setSpacing(2)
                    p_lbl = QLabel(param["label"])
                    p_lbl.setStyleSheet("font-size: 14px; font-weight: 500; color: #495057; border: none;")
                    lbl_layout.addWidget(p_lbl)
                    
                    if "help" in param:
                        h_lbl = QLabel(param["help"])
                        h_lbl.setStyleSheet("font-size: 12px; color: #ADB5BD; border: none;")
                        lbl_layout.addWidget(h_lbl)
                        
                    row_layout.addLayout(lbl_layout)
                    row_layout.addStretch()
                    
                    current_val = self.config_state.get(param["key"], param.get("default"))
                    
                    if param["type"] == "bool":
                        w = QCheckBox()
                        w.setChecked(bool(current_val))
                        w.setStyleSheet("""
                            QCheckBox::indicator { width: 20px; height: 20px; }
                        """)
                        self.widget_map[param["key"]] = w
                        row_layout.addWidget(w)
                    elif param["type"] == "float":
                        w = QDoubleSpinBox()
                        w.setRange(param.get("min", -99999), param.get("max", 99999))
                        w.setDecimals(4)
                        w.setValue(float(current_val))
                        w.setMinimumWidth(140)
                        w.setFixedHeight(35)
                        w.setFocusPolicy(Qt.FocusPolicy.StrongFocus) # Disable wheel scrolling accidentally
                        w.setStyleSheet("""
                            QDoubleSpinBox {
                                border: 1px solid #CED4DA; border-radius: 5px; padding: 5px;
                                background-color: #FFFFFF; color: #212529; font-size: 14px;
                            }
                            QDoubleSpinBox:focus { border: 1px solid #86B7FE; }
                        """)
                        self.widget_map[param["key"]] = w
                        row_layout.addWidget(w)
                    elif param["type"] == "str":
                        w = QLineEdit()
                        w.setText(str(current_val))
                        w.setMinimumWidth(250)
                        w.setFixedHeight(35)
                        w.setStyleSheet("""
                            QLineEdit {
                                border: 1px solid #CED4DA; border-radius: 5px; padding: 5px;
                                background-color: #FFFFFF; color: #212529; font-size: 14px;
                            }
                            QLineEdit:focus { border: 1px solid #86B7FE; }
                        """)
                        self.widget_map[param["key"]] = w
                        row_layout.addWidget(w)
                        
                    mod_layout.addLayout(row_layout)
                
                vbox.addWidget(mod_frame)
            
            if page["page_title"] == "Network Topology":
                btn_calc = QPushButton("Calculate Quick Metrics (Slant Range & Elevation)")
                btn_calc.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_calc.setStyleSheet("""
                    QPushButton {
                        background-color: #F8F9FA;
                        border: 2px solid #0D6EFD;
                        color: #0D6EFD;
                        border-radius: 8px;
                        padding: 12px;
                        font-weight: bold;
                        font-size: 14px;
                    }
                    QPushButton:hover {
                        background-color: #E7F1FF;
                    }
                """)
                btn_calc.clicked.connect(self.calculate_quick_metrics)
                vbox.addWidget(btn_calc)
                
            vbox.addStretch()
            container.setLayout(vbox)
            scroll.setWidget(container)
            self.stack.addWidget(scroll)
        
        content_layout.addWidget(self.stack)
        
        # BOTTOM BAR
        bottom_bar = QWidget()
        bottom_bar.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-top: 1px solid #DEE2E6;
            }
        """)
        bot_layout = QHBoxLayout(bottom_bar)
        bot_layout.setContentsMargins(25, 15, 25, 15)
        bot_layout.addStretch()
        
        self.btn_save = QPushButton("Save Settings")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #6C757D; border: none; color: white;
                padding: 10px 20px; border-radius: 6px; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background-color: #5A6268; }
        """)
        self.btn_save.clicked.connect(self.save_settings)
        bot_layout.addWidget(self.btn_save)
        
        self.btn_run = QPushButton("Run Simulation")
        self.btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_run.setStyleSheet("""
            QPushButton {
                background-color: #198754; border: none; color: white;
                padding: 10px 25px; border-radius: 6px; font-weight: bold; font-size: 14px;
                margin-left: 10px;
            }
            QPushButton:hover { background-color: #157347; }
        """)
        self.btn_run.clicked.connect(self.run_simulation)
        bot_layout.addWidget(self.btn_run)
        
        content_layout.addWidget(bottom_bar)
        main_layout.addWidget(content_area)

    def change_page(self, idx):
        self.stack.setCurrentIndex(idx)

    def set_preset_static(self):
        for k, w in self.widget_map.items():
            if isinstance(w, QCheckBox):
                w.setChecked(False)

    def set_preset_all(self):
        for k, w in self.widget_map.items():
            if isinstance(w, QCheckBox):
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
            
            msg = QMessageBox(self)
            msg.setWindowTitle("Quick Metrics Calculation")
            msg.setText(f"<b>GS1 (Uplink)</b><br>Slant Range: {s1:.2f} km<br>Elevation: {e1:.2f}°<br><br>"
                        f"<b>GS2 (Downlink)</b><br>Slant Range: {s2:.2f} km<br>Elevation: {e2:.2f}°")
            msg.setStyleSheet("QLabel { font-size: 14px; }")
            msg.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not calculate metrics: {str(e)}")

    def save_settings(self):
        if not os.path.exists(SCENARIO_FILE):
            QMessageBox.warning(self, "Warning", "scenario_inputs.py not found.")
            return
            
        with open(SCENARIO_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        for key, w in self.widget_map.items():
            if isinstance(w, QCheckBox):
                val = str(w.isChecked())
            elif isinstance(w, QDoubleSpinBox):
                val = str(w.value())
            elif isinstance(w, QLineEdit):
                val = f'"{w.text()}"'
                
            if "['" in key:
                dict_part, key_part = key.split("['")
                key_part = key_part.replace("']", "")
                pattern = rf"({dict_part}\s*\[\s*['\"]{key_part}['\"]\s*\]\s*=\s*)([^,#\n]*)"
                content = re.sub(pattern, rf"\g<1>{val}", content)
            else:
                pattern = rf"^({key}\s*=\s*)([^,#\n]*)"
                content = re.sub(pattern, rf"\g<1>{val}", content, flags=re.MULTILINE)
                
        with open(SCENARIO_FILE, "w", encoding="utf-8") as f:
            f.write(content)
            
        self.btn_save.setText("Saved ✓")
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #0D6EFD; border: none; color: white;
                padding: 10px 20px; border-radius: 6px; font-weight: bold; font-size: 14px;
            }
        """)
        QThread.msleep(1000)
        self.btn_save.setText("Save Settings")
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #6C757D; border: none; color: white;
                padding: 10px 20px; border-radius: 6px; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background-color: #5A6268; }
        """)

    def run_simulation(self):
        self.save_settings()
        self.btn_run.setText("Running...")
        self.btn_run.setEnabled(False)
        
        self.thread = RunnerThread()
        self.thread.finished_signal.connect(self.on_run_finished)
        self.thread.start()

    def on_run_finished(self):
        self.btn_run.setText("Run Simulation")
        self.btn_run.setEnabled(True)
        QMessageBox.information(self, "Success", "Simulation finished! Check the terminal or outputs folder.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ConfigApp()
    window.show()
    sys.exit(app.exec())