
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QFont, QPen
import webbrowser
import threading
from ..theme import THEME_DARK
from ..widgets import LoadingOverlay, CardWidget, AirQualityRing, GradientSlider, AnimatedButton
from ..signals import WorkerSignals
from ...services.cloud import XiaomiCloudEngine
from ...core.config import load_credentials, save_credentials, delete_credentials

class DeviceControl(QWidget):
    def __init__(self, widget, text, theme, parent=None):
        super().__init__(parent)
        self.setFixedSize(100, 120) 
        self.widget = widget
        self.text = text
        self.theme = theme
        
        # Setup Widget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Container for widget to ensure it's centered
        w_container = QWidget()
        w_container.setFixedSize(100, 80)
        w_layout = QVBoxLayout(w_container)
        w_layout.setContentsMargins(0, 0, 0, 0)
        w_layout.addWidget(widget, 0, Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(w_container)
        layout.addStretch() # Space for text
        
    def paintEvent(self, event):
        if not self.isVisible(): return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor(self.theme['text_sec']))
        font = QFont("Helvetica Neue", 11)
        painter.setFont(font)
        
        rect = self.rect()
        # Draw text at bottom area (y=90 to end)
        text_rect = rect.adjusted(0, 85, 0, 0) 
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, self.text)
        painter.end()

    def set_theme(self, theme):
        self.theme = theme
        self.update()

class AirPurifierTab(QWidget):
    def __init__(self):
        super().__init__()
        self.device = None
        self.theme = THEME_DARK
        self.engine = XiaomiCloudEngine() 
        self.signals = WorkerSignals()
        self.signals.result.connect(self.update_ui)
        self.signals.error.connect(self.show_error)
        
        # Overlay
        self.overlay = LoadingOverlay(self)
        self.overlay.hide()

        # Layouts
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Login Widget
        self.login_widget = QWidget()
        login_layout = QVBoxLayout(self.login_widget)
        
        lbl = QLabel("Connect Xiaomi Account")
        lbl.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {self.theme['text']};")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        login_layout.addWidget(lbl)
        
        self.lbl_qr = QLabel()
        self.lbl_qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_qr.setFixedSize(220, 220)
        self.lbl_qr.setStyleSheet(f"background: {self.theme['card']}; border-radius: 12px;")
        login_layout.addWidget(self.lbl_qr, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_login_status = QLabel("Ready to connect")
        self.lbl_login_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        login_layout.addWidget(self.lbl_login_status)
        
        btn_row = QHBoxLayout()
        self.btn_gen_qr = AnimatedButton("Generate QR", color=self.theme["accent"])
        self.btn_gen_qr.clicked.connect(self.start_login)
        btn_row.addWidget(self.btn_gen_qr)
        
        self.btn_browser = AnimatedButton("Open Browser Login", color=self.theme["card"])
        self.btn_browser.clicked.connect(lambda: webbrowser.open(self.engine.login_url) if self.engine.login_url else None)
        self.btn_browser.setEnabled(False) 
        btn_row.addWidget(self.btn_browser)
        
        login_layout.addLayout(btn_row)
        
        self.layout.addWidget(self.login_widget)

        # Dashboard
        self.dashboard_widget = QWidget()
        dash_layout = QHBoxLayout(self.dashboard_widget)
        dash_layout.setContentsMargins(30, 30, 30, 30)
        dash_layout.setSpacing(30)
        
        # Left Panel: Status Ring & Fan Slider
        self.left_panel_widget = CardWidget() # Use CardWidget for background
        left_panel_layout = QVBoxLayout(self.left_panel_widget)
        left_panel_layout.setContentsMargins(0, 0, 0, 0)
        left_panel_layout.setSpacing(20)
        
        # Ring Container (Centered)
        self.ring_container = QWidget()
        ring_layout = QVBoxLayout(self.ring_container)
        ring_layout.setContentsMargins(0, 0, 0, 0)
        ring_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.aqi_ring = AirQualityRing()
        self.aqi_ring.clicked.connect(self.sync_once) # allow click to refresh
        ring_layout.addWidget(self.aqi_ring)
        
        left_panel_layout.addWidget(self.ring_container, 1) # Expand to push slider down/keep ring centered
        
        # Fan Speed Slider
        self.fan_container = QWidget()
        self.fan_container.setFixedHeight(80) # Fixed height to prevent layout jumps
        fan_layout = QVBoxLayout(self.fan_container)
        fan_layout.setContentsMargins(0, 0, 0, 0) # Zero margins for container
        
        # Inner wrapper for content to hide/show
        self.fan_inner = QWidget()
        inner_layout = QVBoxLayout(self.fan_inner)
        inner_layout.setContentsMargins(20, 0, 20, 0)
        inner_layout.setSpacing(10)
        
        fan_row = QHBoxLayout()
        fan_row.addWidget(QLabel("Fan Speed"))
        self.lbl_fan_val = QLabel("1")
        self.lbl_fan_val.setStyleSheet(f"color: {self.theme['text_sec']}; font-weight: bold;")
        fan_row.addWidget(self.lbl_fan_val, 0, Qt.AlignmentFlag.AlignRight)
        inner_layout.addLayout(fan_row)
        
        self.sl_fan = GradientSlider(colors=[QColor("#4CD964"), QColor("#FFCC00"), QColor("#FF3B30")])
        self.sl_fan.setRange(1, 14)
        self.sl_fan.sliderReleased.connect(self.set_speed)
        self.sl_fan.valueChanged.connect(lambda v: self.lbl_fan_val.setText(str(v)))
        inner_layout.addWidget(self.sl_fan)
        
        fan_layout.addWidget(self.fan_inner)
        left_panel_layout.addWidget(self.fan_container)
        self.fan_inner.hide() # Initially hidden, but container stays visible taking space
        
        dash_layout.addWidget(self.left_panel_widget, 1) # Expand

        # Right Panel: Controls
        self.controls_card = CardWidget()
        self.controls_card.setFixedWidth(320)
        controls_layout = QVBoxLayout(self.controls_card)
        controls_layout.setContentsMargins(24, 24, 24, 24)
        controls_layout.setSpacing(24)
        
        # Power & Filter (Custom Prainted Control)
        # Replaces Grid/Label approach to strictly enforce spacing via painting
        
        controls_row = QHBoxLayout()
        controls_row.addStretch()
        controls_row.setSpacing(40) # Spacing between the two controls
        
        # Power Control
        self.btn_air_power = AnimatedButton(icon_name="fa5s.power-off", size=(80, 80), radius=40, checked_color=self.theme["green"])
        self.btn_air_power.setCheckable(True)
        self.btn_air_power.clicked.connect(self.toggle_air)
        
        self.power_ctrl = DeviceControl(self.btn_air_power, "Power", self.theme)
        controls_row.addWidget(self.power_ctrl)

        # Filter Control
        from ..components.circular_progress import CircularProgress
        self.filter_progress = CircularProgress()
        self.filter_progress.setFixedSize(80, 80)
        
        self.filter_ctrl = DeviceControl(self.filter_progress, "Filter Life", self.theme)
        controls_row.addWidget(self.filter_ctrl)

        controls_row.addStretch()
        
        controls_layout.addLayout(controls_row)
        
        
        # Mode Buttons
        self.btn_auto = AnimatedButton("Auto")
        self.btn_silent = AnimatedButton("Silent")
        self.btn_manual = AnimatedButton("Manual")
        
        for btn in [self.btn_auto, self.btn_silent, self.btn_manual]:
            btn.setCheckable(True)
            btn.setFixedHeight(50)
            btn.clicked.connect(self.set_mode)
            controls_layout.addWidget(btn)
            
        
        controls_layout.addStretch()
        
        self.btn_logout = AnimatedButton("Logout", color=self.theme['card']) # Transparent-ish
        self.btn_logout.setFixedSize(120, 40)
        self.btn_logout.clicked.connect(self.logout)
        controls_layout.addWidget(self.btn_logout, 0, Qt.AlignmentFlag.AlignCenter)
        
        dash_layout.addWidget(self.controls_card)

        self.layout.addWidget(self.dashboard_widget)
        self.dashboard_widget.hide()

        QTimer.singleShot(800, self.check_saved_login)

    def resizeEvent(self, event):
        self.overlay.resize(self.size())
        super().resizeEvent(event)

    def set_theme(self, theme):
        self.theme = theme
        
        # Remove border from cards as requested
        card_style = f"background-color: {theme['card']}; border-radius: 16px; border: none;"
        self.left_panel_widget.setStyleSheet(card_style)
        self.controls_card.setStyleSheet(card_style)

        self.aqi_ring.set_theme(theme)
        self.sl_fan.set_theme(theme)
        self.btn_air_power.set_theme(theme)
        self.power_ctrl.set_theme(theme)
        self.filter_progress.set_theme(theme)
        self.filter_ctrl.set_theme(theme)
        self.lbl_fan_val.setStyleSheet(f"color: {theme['text_sec']}; font-weight: bold;")
        self.btn_gen_qr.set_theme(theme)
        self.btn_browser.set_theme(theme)
        self.btn_logout.set_theme(theme)
        
        # Update Mode Buttons
        for btn in [self.btn_auto, self.btn_silent, self.btn_manual]:
            btn.set_theme(theme)

    def showEvent(self, event):
        super().showEvent(event)
        # Reset to 0 first to ensure animation is visible
        # Use direct property setters to avoid animation during reset
        self.aqi_ring.animated_aqi = 0
        self.filter_progress.value = 0
        
        # Trigger animation after short delay to allow paint
        QTimer.singleShot(100, self.trigger_entry_animations)

    def trigger_entry_animations(self):
        # If we have data, animate to it. If not, sync will handle it.
        # Ideally, we animate to the LAST known valid value if sync hasn't finished,
        # or wait for sync.
        # For now, let's sync. If we keep last values, we could animate to them.
        
        # Optimistic: Animate to last known if > 0
        if hasattr(self.aqi_ring, '_target_aqi') and self.aqi_ring._target_aqi > 0:
             self.aqi_ring.set_aqi(self.aqi_ring._target_aqi)
        
        self.sync_once()

    def check_saved_login(self):
        ip, token = load_credentials()
        self.lbl_login_status.setText(f"Found saved credentials for {ip}" if ip else "No saved credentials")
        if ip and token:
            self.connect_device(ip, token)

    def start_login(self):
        self.btn_gen_qr.setEnabled(False)
        self.lbl_login_status.setText("Generating QR...")
        self.overlay.show_loading()
        threading.Thread(target=self._login_worker, daemon=True).start()

    def _login_worker(self):
        try:
            img_url, lp_url = self.engine.step_1_get_qr()
            if not img_url: raise RuntimeError("Failed to get QR")
            
            from PyQt6.QtGui import QImage, QPixmap
            
            QTimer.singleShot(0, lambda: self.btn_browser.setEnabled(True))
            img_bytes = self.engine.step_2_download_img(img_url)
            
            qimg = QImage.fromData(img_bytes)
            pixmap = QPixmap.fromImage(qimg).scaled(220, 220, Qt.AspectRatioMode.KeepAspectRatio)
            QTimer.singleShot(0, lambda: self.lbl_qr.setPixmap(pixmap))
            QTimer.singleShot(0, lambda: self.lbl_login_status.setText("Scan with Mi Home App"))
            QTimer.singleShot(0, self.overlay.hide_loading) # Hide overlay after QR is ready

            if self.engine.step_3_poll(lp_url):
                QTimer.singleShot(0, lambda: self.lbl_login_status.setText("Authenticated. Fetching token..."))
                QTimer.singleShot(0, self.overlay.show_loading) # Show again for token fetch
                if self.engine.step_4_service_token():
                    devices = self.engine.get_devices()
                    target = next((d for d in devices if d.get("localip") and d.get("token")), None)
                    if target:
                        save_credentials(target["localip"], target["token"])
                        QTimer.singleShot(0, lambda: self.connect_device(target["localip"], target["token"]))
                    else:
                        QTimer.singleShot(0, lambda: self.lbl_login_status.setText("No supported device found"))
                        QTimer.singleShot(0, self.overlay.hide_loading)
        except Exception as e:
            QTimer.singleShot(0, lambda: self.lbl_login_status.setText(f"Error: {e}"))
            QTimer.singleShot(0, lambda: self.btn_gen_qr.setEnabled(True))
            QTimer.singleShot(0, self.overlay.hide_loading)

    def connect_device(self, ip, token):
        self.lbl_login_status.setText(f"Connecting to {ip}...")
        self.overlay.show_loading()
        threading.Thread(target=self._init_device, args=(ip, token), daemon=True).start()

    def _init_device(self, ip, token):
        try:
            from smart_home_app.services.cloud import Device
            self.device = Device(ip, token)
            # Test connection
            self.device.send("get_properties", [{"siid": 2, "piid": 1}])
            self.signals.result.emit([{"value": True}]) # Dummy success signal to trigger UI switch
        except Exception as e:
            self.signals.error.emit(str(e))

    def update_ui(self, results):
        if not self.dashboard_widget.isVisible():
            self.login_widget.hide()
            self.dashboard_widget.show()
            self.overlay.hide_loading()
            self.sync_once()
            
            # Start polling
            if not hasattr(self, 'timer'):
                self.timer = QTimer(self)
                self.timer.timeout.connect(self.sync_once)
            
            if not self.timer.isActive():
                self.timer.start(5000)
            return

        self.overlay.hide_loading()
        
        if len(results) < 5: return
        
        is_on = results[0].get("value", False)
        self.btn_air_power.setChecked(is_on)

        mode_val = results[1].get("value", 0)
        self.btn_auto.setChecked(mode_val == 0)
        self.btn_silent.setChecked(mode_val == 1)
        self.btn_manual.setChecked(mode_val == 2)
        
        if mode_val == 2:
            self.fan_inner.show()
        else:
            self.fan_inner.hide()
        
        aqi = results[2].get("value", 0)
        self.aqi_ring._target_aqi = aqi # Store for replay
        self.aqi_ring.set_aqi(aqi)

        fan_speed = results[3].get("value", 1)
        self.sl_fan.setValue(fan_speed)
        self.lbl_fan_val.setText(str(fan_speed))

        life = results[4].get("value", 0)
        self.filter_progress._target_value = life # Store for replay
        self.filter_progress.set_value(life)

    def show_error(self, msg):
        self.overlay.hide_loading()
        self.lbl_login_status.setText(msg)

    def toggle_air(self):
        if not self.device: return
        # Checkable button toggles state on click, so we just use the new checked state
        target_state = self.btn_air_power.isChecked()
        threading.Thread(target=self._toggle_task, args=(target_state,), daemon=True).start()

    def _toggle_task(self, target_state):
        try:
            self.device.send("set_properties", [{"siid": 2, "piid": 1, "value": target_state}])
            self.sync_once()
        except: 
            # Revert on failure?
            pass

    def sync_once(self):
        if not self.device or not self.isVisible():
            if hasattr(self, 'timer') and self.timer.isActive() and not self.isVisible():
                self.timer.stop()
            return
            
        if getattr(self, 'is_syncing', False):
            return

        self.is_syncing = True
        # self.overlay.show_loading() # Don't show overlay for background sync
        threading.Thread(target=self._sync_task, daemon=True).start()

    def _sync_task(self):
        try:
            props = [
                {"siid": 2, "piid": 1}, # Power
                {"siid": 2, "piid": 4}, # Mode
                {"siid": 3, "piid": 6}, # AQI (3.6 usually, check constants)
                {"siid": 10, "piid": 10}, # Fan Level (check constants)
                {"siid": 4, "piid": 3}  # Filter Life (check constants)
            ]
            
            from smart_home_app.core.constants import PROP_POWER, PROP_MODE, PROP_AQI, PROP_FAVORITE, PROP_FILTER
            props = [PROP_POWER, PROP_MODE, PROP_AQI, PROP_FAVORITE, PROP_FILTER]
            
            res = self.device.send("get_properties", props)
            self.signals.result.emit(res)
        except Exception as e:
            print(f"Sync error: {e}")
            # self.signals.error.emit(str(e)) # Don't spam errors on sync
        finally:
            self.is_syncing = False

    def set_mode(self):
        sender = self.sender()
        val = 0 if sender == self.btn_auto else 1 if sender == self.btn_silent else 2
        
        # Optimistic Update
        self.btn_auto.setChecked(val == 0)
        self.btn_silent.setChecked(val == 1)
        self.btn_manual.setChecked(val == 2)
        
        if val == 2:
            self.fan_inner.show()
        else:
            self.fan_inner.hide()
            
        threading.Thread(target=self._set_mode_task, args=(val,), daemon=True).start()

    def _set_mode_task(self, val):
        if not self.device: return
        try:
            self.device.send("set_properties", [{"siid": 2, "piid": 4, "value": val}])
            self.sync_once()
        except: pass

    def set_speed(self):
        val = self.sl_fan.value()
        threading.Thread(target=self._set_speed_task, args=(val,), daemon=True).start()

    def _set_speed_task(self, val):
        if not self.device: return
        try:
            self.device.send("set_properties", [{"siid": 9, "piid": 11, "value": val}])
            self.device.send("set_properties", [{"siid": 2, "piid": 4, "value": 2}])
            self.sync_once()
        except: pass

    def logout(self):
        delete_credentials()
        self.device = None
        self.btn_gen_qr.setEnabled(True)
        self.lbl_qr.clear()
