
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QScrollArea, QFrame, QGridLayout, QInputDialog
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, pyqtProperty
from PyQt6.QtGui import QColor, QFont, QTransform
import qtawesome as qta
import json
import os
import threading
from ..theme import THEME_DARK
from ..widgets import CardWidget, GlowingIcon, GradientSlider, DeviceCard
from ...services.wiz import WiZLightClient
from ...core.constants import DEFAULT_TEMP, DEFAULT_DIMMING

ICSEE_CONFIG = os.path.join(os.path.expanduser("~"), ".home_control_config.json")

class WiZTab(QWidget):
    scan_finished = pyqtSignal(list)
    sync_finished = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.client = WiZLightClient()
        self.wiz_state = False
        self.wiz_ip = None
        self.is_syncing = False
        self.theme = THEME_DARK
        self.device_cards = {}  # ip -> card
        self.wiz_names = {}  # ip -> name
        self.load_names()

        self.scan_finished.connect(self._update_scan_results)
        self.sync_finished.connect(self._apply_data)

        # Main Layout (Split View)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(30)

        # --- Left Panel: Controls ---
        self.left_panel = CardWidget()
        self.left_panel.setFixedWidth(320)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(24, 24, 24, 24)
        left_layout.setSpacing(24)
        
        # Header
        self.lbl_status = QLabel("Select a light")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.lbl_status)

        # Power Button
        power_container = QWidget()
        power_layout = QHBoxLayout(power_container)
        self.btn_power = GlowingIcon("fa5s.power-off", size=80)
        self.btn_power.clicked.connect(self.toggle_power)
        power_layout.addWidget(self.btn_power)
        left_layout.addWidget(power_container)

        # Controls
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(20)

        # Temp
        temp_row = QHBoxLayout()
        temp_row.addWidget(QLabel("Temperature"))
        self.lbl_temp_val = QLabel(f"{DEFAULT_TEMP}K")
        temp_row.addWidget(self.lbl_temp_val, 0, Qt.AlignmentFlag.AlignRight)
        controls_layout.addLayout(temp_row)

        self.sl_temp = GradientSlider()
        self.sl_temp.setRange(2700, 6500)
        self.sl_temp.setValue(DEFAULT_TEMP)
        self.sl_temp.valueChanged.connect(self.update_labels)
        self.sl_temp.sliderReleased.connect(self.send_pilot)
        controls_layout.addWidget(self.sl_temp)

        # Dimming
        dim_row = QHBoxLayout()
        dim_row.addWidget(QLabel("Brightness"))
        self.lbl_dim_val = QLabel(f"{DEFAULT_DIMMING}%")
        dim_row.addWidget(self.lbl_dim_val, 0, Qt.AlignmentFlag.AlignRight)
        controls_layout.addLayout(dim_row)

        self.sl_dim = GradientSlider(colors=[QColor("#333333"), QColor("#FFFFFF")])
        self.sl_dim.setRange(10, 100)
        self.sl_dim.setValue(DEFAULT_DIMMING)
        self.sl_dim.valueChanged.connect(self.update_labels)
        self.sl_dim.sliderReleased.connect(self.send_pilot)
        controls_layout.addWidget(self.sl_dim)

        # Sleep Mode Button
        self.btn_sleep = QPushButton("  Sleep Mode")
        self.btn_sleep.setIcon(qta.icon("fa5s.moon", color=self.theme['text']))
        self.btn_sleep.setFixedHeight(40)
        self.btn_sleep.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sleep.clicked.connect(self.set_sleep_mode)
        controls_layout.addWidget(self.btn_sleep)

        left_layout.addLayout(controls_layout)
        left_layout.addStretch()
        
        layout.addWidget(self.left_panel)

        layout.addWidget(self.left_panel)

        # --- Right Panel: Device Grid ---
        self.right_panel = CardWidget()
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(24, 24, 24, 24)
        right_layout.setSpacing(20)
        
        # Toolbar
        toolbar = QHBoxLayout()
        lbl_devices = QLabel("Devices")
        lbl_devices.setFont(QFont("Helvetica Neue", 20, QFont.Weight.Bold))
        toolbar.addWidget(lbl_devices)
        toolbar.addStretch()
        
        self.btn_scan = QPushButton("  Scan Network")
        self.btn_scan.setIcon(qta.icon("fa5s.sync-alt", color="white"))
        self.btn_scan.setFixedHeight(36)
        self.btn_scan.setFixedWidth(140)
        self.btn_scan.clicked.connect(self.scan_lights)
        toolbar.addWidget(self.btn_scan)
        
        right_layout.addLayout(toolbar)
        
        # Scroll Area for Grid
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")
        
        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        self.scroll.setWidget(self.grid_container)
        right_layout.addWidget(self.scroll)
        
        layout.addWidget(self.right_panel, 1)

        # Scan Animation
        self._scan_rotation = 0
        self.scan_anim = QPropertyAnimation(self, b"scan_rotation")
        self.scan_anim.setDuration(1000)
        self.scan_anim.setLoopCount(-1) # Infinite loop

        QTimer.singleShot(500, self.scan_lights)

    @pyqtProperty(int)
    def scan_rotation(self):
        return self._scan_rotation

    @scan_rotation.setter
    def scan_rotation(self, angle):
        self._scan_rotation = angle
        # Rotate icon
        trans = QTransform()
        trans.rotate(angle)
        self.btn_scan.setIcon(qta.icon("fa5s.sync-alt", color="white", animation=qta.Spin(self.btn_scan))) 

    def set_theme(self, theme):
        self.theme = theme
        self.lbl_status.setStyleSheet(f"color: {theme['text_sec']}; font-size: 14px;")
        self.lbl_temp_val.setStyleSheet(f"color: {theme['text_sec']}; font-weight: bold;")
        self.lbl_dim_val.setStyleSheet(f"color: {theme['text_sec']}; font-weight: bold;")
        self.btn_power.set_theme(theme)
        self.sl_temp.set_theme(theme)
        self.btn_power.set_theme(theme)
        self.sl_temp.set_theme(theme)
        self.sl_dim.set_theme(theme)
        
        self.btn_sleep.setIcon(qta.icon("fa5s.moon", color=theme['text']))
        self.btn_sleep.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme['input']};
                color: {theme['text']};
                border-radius: 20px;
                border: 1px solid {theme['border']};
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {theme['sidebar_hover']};
                border-color: {theme['accent']};
            }}
        """)
        
        # Apply Card Style (Borderless)
        card_style = f"background-color: {theme['card']}; border-radius: 16px; border: none;"
        self.left_panel.setStyleSheet(card_style)
        self.right_panel.setStyleSheet(card_style)

        # Apply Custom Scrollbar Style (same as Settings)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 12px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {theme['input']};
                min-height: 20px;
                border-radius: 6px;
                margin: 2px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        self.update_power_ui()
        
        # Update cards
        for card in self.device_cards.values():
            card.set_theme(theme)

    def load_names(self):
        if os.path.exists(ICSEE_CONFIG):
            try:
                with open(ICSEE_CONFIG, "r") as f:
                    data = json.load(f)
                    self.wiz_names = data.get("wiz_names", {})
            except: pass

    def save_names(self):
        data = {}
        if os.path.exists(ICSEE_CONFIG):
            try:
                with open(ICSEE_CONFIG, "r") as f:
                    data = json.load(f)
            except: pass
        
        data["wiz_names"] = self.wiz_names
        try:
            with open(ICSEE_CONFIG, "w") as f:
                json.dump(data, f)
        except: pass

    def rename_light(self, ip, current_name):
        if ip == "ALL": return # Cannot rename group
        name, ok = QInputDialog.getText(self, "Rename Light", "Enter new name:", text=current_name)
        if ok and name:
            self.wiz_names[ip] = name
            self.save_names()
            if ip in self.device_cards:
                self.device_cards[ip].name_lbl.setText(name)
                self.device_cards[ip].name = name

    def prepare_visuals(self):
        # Called by StackedWidget before snapshotting for slide animation
        # Store current values
        self._target_temp = self.sl_temp.value()
        self._target_dim = self.sl_dim.value()
        
        # Reset to min immediately (no animation) to ensure clean snapshot
        self.sl_temp.anim.stop()
        self.sl_temp.setValue(self.sl_temp.minimum())
        
        self.sl_dim.anim.stop()
        self.sl_dim.setValue(self.sl_dim.minimum())

    def showEvent(self, event):
        super().showEvent(event)
        
        # FIX: Ensure grid is sized correctly when tab shows
        QTimer.singleShot(0, self.reflow_grid)
        
        # Determine targets (either from prepare_visuals or current)
        target_temp = getattr(self, '_target_temp', self.sl_temp.value())
        target_dim = getattr(self, '_target_dim', self.sl_dim.value())
        
        if target_temp > self.sl_temp.minimum():
            self.sl_temp.anim.stop()
            self.sl_temp.anim.setStartValue(self.sl_temp.minimum())
            self.sl_temp.anim.setEndValue(target_temp)
            self.sl_temp.anim.start()
            
        if target_dim > self.sl_dim.minimum():
            self.sl_dim.anim.stop()
            self.sl_dim.anim.setStartValue(self.sl_dim.minimum())
            self.sl_dim.anim.setEndValue(target_dim)
            self.sl_dim.anim.start()

    def set_sleep_mode(self):
        # Use Scene 14 (Night Light) as requested
        if not self.wiz_ip: return
        
        # Payload based on user request: sceneId 14 ("Night light")
        payload = {"id": 1, "method": "setPilot", "params": {"sceneId": 14, "dimming": 10}}
        
        if self.wiz_ip == "ALL":
             targets = [ip for ip in self.device_cards.keys() if ip != "ALL"]
             for ip in targets:
                 threading.Thread(target=self.client.send_request, args=(ip, payload), daemon=True).start()
        else:
            threading.Thread(target=self.client.send_request, args=(self.wiz_ip, payload), daemon=True).start()
            
        # Update UI to reflect this special state
        self.sl_temp.blockSignals(True)
        self.sl_dim.blockSignals(True)
        # Scene 14 is usually very warm, let's show that on slider
        self.sl_temp.setValue(2200) 
        self.sl_dim.setValue(10) 
        self.sl_temp.blockSignals(False)
        self.sl_dim.blockSignals(False)
        self.update_labels()
        self.lbl_status.setText("Sleep Mode (Night Light)")

    def scan_lights(self):
        self.lbl_status.setText("Scanning...")
        self.btn_scan.setText("  Scanning...")
        self.btn_scan.setEnabled(False)
        # Pass known IPs for active probing to improve reliability
        known_ips = list(self.wiz_names.keys())
        threading.Thread(target=self._scan_thread, args=(known_ips,), daemon=True).start()

    def _scan_thread(self, known_ips):
        # 1. Broadcast Scan
        found = self.client.scan(broadcast_timeout=2.0)
        
        # 2. Active Probe for known missing devices (Reliability Fix)
        # Often UDP broadcast packets are dropped, so we unicast check known ones.
        missing = [ip for ip in known_ips if ip not in found]
        for ip in missing:
            try:
                # Short timeout for probe
                if self.client.send_request(ip, {"method": "getPilot", "params": {}}, timeout=0.5):
                    found.append(ip)
            except: pass
            
        self.scan_finished.emit(found)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.reflow_grid()

    def reflow_grid(self):
        if not hasattr(self, 'current_ips'): return
        
        # Calculate columns based on Viewport (available visible space)
        # Use fallback if scroll not ready, but usually it is.
        width = self.scroll.viewport().width() if hasattr(self, 'scroll') else self.grid_container.width()
        if width <= 0: width = 600

        # Min width per card (Reduced to 120 + 10 spacing = 130)
        item_width = 130 
        cols = max(1, width // item_width)
        
        # Clear layout (items taken out might be hidden)
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
                
        # Fill grid (Include "ALL" card logic if present)
        row, col = 0, 0
        
        # We need to iterate over device_cards values or keys?
        # current_ips only has real IPs. We added "ALL" to device_cards.
        # Let's iterate self.device_cards values explicitly, but we want order.
        # Order: "ALL", then current_ips.
        
        ordered_keys = []
        if "ALL" in self.device_cards: ordered_keys.append("ALL")
        ordered_keys.extend([ip for ip in self.current_ips if ip in self.device_cards])
        
        for ip in ordered_keys:
            if ip in self.device_cards:
                card = self.device_cards[ip]
                self.grid_layout.addWidget(card, row, col)
                card.show() # Explicitly show to ensure visibility
                col += 1
                if col >= cols:
                    col = 0
                    row += 1

    def _update_scan_results(self, found_ips):
        self.btn_scan.setText("  Scan Network")
        self.btn_scan.setEnabled(True)
        
        found_set = set(found_ips if found_ips else [])
        
        # Ensure discovered devices are in persistent storage
        if found_set:
            changed = False
            for ip in found_set:
                if ip not in self.wiz_names:
                    self.wiz_names[ip] = f"WiZ Light {ip[-3:]}" # Default name
                    changed = True
            if changed:
                self.save_names()

        # Clear existing items
        while self.grid_layout.count():
             self.grid_layout.takeAt(0).widget().deleteLater()
        self.device_cards.clear()
        
        # Display ALL historical devices (Known + Found)
        # This addresses user request to show offline devices
        all_known = set(self.wiz_names.keys()) | found_set
        self.current_ips = sorted(list(all_known))
        
        # Add "All Lights" Card
        if self.current_ips:
            all_card = DeviceCard("All Lights", "fa5s.layer-group", "ALL", size=(120, 120))
            all_card.setToolTip("Control all lights at once")
            all_card.set_status(None) # No online/offline label for group
            all_card.clicked.connect(lambda checked: self.on_card_clicked("ALL"))
            self.device_cards["ALL"] = all_card

        if self.current_ips:
            for ip in self.current_ips:
                name = self.wiz_names.get(ip, "WiZ Light")
                # Smaller size (120, 120)
                card = DeviceCard(name, "fa5s.lightbulb", ip, on_rename=self.rename_light, size=(120, 120))
                
                # Set Status Logic: Found = Online, History only = Offline
                is_online = ip in found_set
                card.set_status(is_online)
                
                card.clicked.connect(lambda checked, i=ip: self.on_card_clicked(i))
                self.device_cards[ip] = card
                
            self.reflow_grid()
            
            # Select ALL if available, else first
            self.on_card_clicked("ALL")
        else:
            self.lbl_status.setText("No lights found")

    def on_card_clicked(self, ip):
        # Uncheck others
        for card_ip, card in self.device_cards.items():
            card.setChecked(card_ip == ip)
            card.update_style()
            
        self.wiz_ip = ip
        if ip == "ALL":
            self.lbl_status.setText("Controlling All Lights")
            self.btn_power.set_active(True)
        else:
            # Only sync if online? Usually yes, but user might want to try connecting to offline one.
            # We'll try syncing regardless.
            self.sync_light()

    def sync_light(self):
        if not self.wiz_ip or self.wiz_ip == "ALL": return
        self.is_syncing = True
        self.lbl_status.setText(f"Syncing {self.wiz_ip}...")
        threading.Thread(target=self._sync_thread, daemon=True).start()

    def _sync_thread(self):
        res = self.client.get_state(self.wiz_ip)
        if res and "result" in res:
            self.sync_finished.emit(res["result"])

    def _apply_data(self, data):
        self.wiz_state = data.get("state", False)
        self.update_power_ui()
        if "temp" in data:
            self.sl_temp.animate_to_value(data["temp"])
        if "dimming" in data:
            self.sl_dim.animate_to_value(data["dimming"])
        self.update_labels()
        self.lbl_status.setText("Connected")
        self.is_syncing = False
        
        # Update card status
        if self.wiz_ip in self.device_cards:
            self.device_cards[self.wiz_ip].set_status(True)

    def toggle_power(self):
        if not self.wiz_ip: return
        
        self.wiz_state = not self.wiz_state
        self.update_power_ui()
        
        if self.wiz_ip == "ALL":
             # Group Control
             targets = [ip for ip in self.device_cards.keys() if ip != "ALL"]
             for ip in targets:
                 threading.Thread(target=self.client.set_power, args=(ip, self.wiz_state), daemon=True).start()
        else:
            threading.Thread(target=self.client.set_power, args=(self.wiz_ip, self.wiz_state), daemon=True).start()

    def update_power_ui(self):
        # Warm white glow for light bulb
        self.btn_power.set_active(self.wiz_state, color="#FFC864")

    def update_labels(self):
        self.lbl_temp_val.setText(f"{self.sl_temp.value()}K")
        self.lbl_dim_val.setText(f"{self.sl_dim.value()}%")

    def send_pilot(self):
        if self.is_syncing or not self.wiz_ip: return
        payload = (self.sl_temp.value(), self.sl_dim.value())
        
        if self.wiz_ip == "ALL":
             targets = [ip for ip in self.device_cards.keys() if ip != "ALL"]
             for ip in targets:
                 threading.Thread(target=self.client.set_pilot, args=(ip, *payload), daemon=True).start()
        else:
            threading.Thread(target=self.client.set_pilot, args=(self.wiz_ip, *payload), daemon=True).start()
