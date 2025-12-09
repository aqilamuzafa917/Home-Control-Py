
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame, 
    QDialog, QSplitter, QListWidget, QLineEdit, QFormLayout, QDialogButtonBox, 
    QSizePolicy, QMessageBox, QGraphicsOpacityEffect, QComboBox, QProgressBar
)

from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot, QSize, QEvent, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QImage, QPixmap, QKeySequence, QFont, QFontMetrics, QShortcut
import cv2
import numpy as np
import time
import json
import os
import qtawesome as qta
import copy
from ..theme import THEME_DARK
from ..widgets import DeviceCard, AnimatedButton, LoadingOverlay
from ...core.constants import ICSEE_CONFIG
import urllib.request
import urllib.parse

class VideoLabel(QLabel):
    """Custom Label for Video Display with Zoom/Pan support"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background-color: black;")
        
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.last_frame = None
        self.last_mouse_pos = None
        
    def reset_zoom(self):
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        if self.last_frame:
            self.update_image(self.last_frame)

    def zoom_in(self, focus_point=None):
        old_zoom = self.zoom_level
        self.zoom_level = min(5.0, self.zoom_level + 0.5)
        self._adjust_pan_for_zoom(old_zoom, self.zoom_level, focus_point)
        if self.last_frame:
            self.update_image(self.last_frame)

    def zoom_out(self, focus_point=None):
        old_zoom = self.zoom_level
        self.zoom_level = max(1.0, self.zoom_level - 0.5)
        self._adjust_pan_for_zoom(old_zoom, self.zoom_level, focus_point)
        
        if self.zoom_level == 1.0:
            self.pan_x = 0
            self.pan_y = 0
            
        if self.last_frame:
            self.update_image(self.last_frame)

    def _adjust_pan_for_zoom(self, old_zoom, new_zoom, focus_point):
        if not focus_point or not self.last_frame:
            return

        lbl_w = self.width()
        lbl_h = self.height()
        
        rel_x = focus_point.x() - lbl_w / 2
        rel_y = focus_point.y() - lbl_h / 2
        
        zoom_factor = new_zoom / old_zoom
        
        if zoom_factor > 1:
            self.pan_x += int(rel_x * (zoom_factor - 1) / new_zoom)
            self.pan_y += int(rel_y * (zoom_factor - 1) / new_zoom)

    @pyqtSlot(QImage)
    def update_image(self, qt_img):
        if qt_img.isNull():
            return
        self.last_frame = qt_img
        
        if self.zoom_level > 1.0:
            w = qt_img.width()
            h = qt_img.height()
            
            view_w = int(w / self.zoom_level)
            view_h = int(h / self.zoom_level)
            
            max_pan_x = (w - view_w) // 2
            max_pan_y = (h - view_h) // 2
            self.pan_x = max(-max_pan_x, min(max_pan_x, self.pan_x))
            self.pan_y = max(-max_pan_y, min(max_pan_y, self.pan_y))
            
            center_x = w // 2 + self.pan_x
            center_y = h // 2 + self.pan_y
            
            x = center_x - (view_w // 2)
            y = center_y - (view_h // 2)
            
            x = max(0, min(w - view_w, x))
            y = max(0, min(h - view_h, y))
            
            qt_img = qt_img.copy(x, y, view_w, view_h)

        scaled_img = qt_img.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.setPixmap(QPixmap.fromImage(scaled_img))

    def wheelEvent(self, event):
        if self.zoom_level > 1.0:
            delta = event.angleDelta()
            speed = 1.0 / self.zoom_level
            # Inverted pan
            self.pan_x -= int(delta.x() * speed)
            self.pan_y -= int(delta.y() * speed)
            
            if self.last_frame:
                self.update_image(self.last_frame)
        
    def event(self, event):
        if event.type() == QEvent.Type.NativeGesture:
            if event.gestureType() == Qt.NativeGestureType.ZoomNativeGesture:
                delta = event.value()
                old_zoom = self.zoom_level
                self.zoom_level += delta
                self.zoom_level = max(1.0, min(5.0, self.zoom_level))
                
                cursor_pos = self.mapFromGlobal(self.cursor().pos())
                self._adjust_pan_for_zoom(old_zoom, self.zoom_level, cursor_pos)

                if self.zoom_level == 1.0:
                    self.pan_x = 0
                    self.pan_y = 0
                if self.last_frame:
                    self.update_image(self.last_frame)
                return True
        return super().event(event)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.last_mouse_pos = event.pos()
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        if self.last_mouse_pos and self.zoom_level > 1.0:
            delta = event.pos() - self.last_mouse_pos
            self.last_mouse_pos = event.pos()
            
            speed = 1.0 / self.zoom_level
            self.pan_x -= int(delta.x() * speed * 2)
            self.pan_y -= int(delta.y() * speed * 2)
            
            if self.last_frame:
                self.update_image(self.last_frame)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.last_mouse_pos = None
        super().mouseReleaseEvent(event)


class VideoFullScreenWindow(QWidget):
    """Fullscreen window for video playback"""
    request_exit = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet("background-color: black;")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.force_close = False
        
        # Exit Button
        self.btn_exit = QPushButton(self)
        self.btn_exit.setIcon(qta.icon("fa5s.compress", color="white"))
        self.btn_exit.setFixedSize(50, 50)
        self.btn_exit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_exit.clicked.connect(self.request_exit.emit)
        self.btn_exit.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 0.5);
                border-radius: 25px;
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.8);
                border-color: white;
            }
        """)
        
        # Shortcut
        self.shortcut_esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self.shortcut_esc.activated.connect(self.request_exit.emit)

    def resizeEvent(self, event):
        self.btn_exit.move(self.width() - 70, 40)
        self.btn_exit.raise_()
        super().resizeEvent(event)

    def closeEvent(self, event):
        if self.force_close:
            event.accept()
        else:
            event.ignore()
            self.request_exit.emit()


# Set RTSP transport and timeout GLOBALLY for the process
# Increased to 15s to handle slow initial handshake/flaky network
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;15000000|timeout;15000000"

class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(QImage)
    status_signal = pyqtSignal(str)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
        self._run_flag = True

    def run(self):
        cap = cv2.VideoCapture(self.url)
        # Attempt to set property if supported (OpenCV 4.x+)
        try:
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 15000)
        except: pass
        
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not cap.isOpened():
            self.status_signal.emit("Connection Failed")
            return

        self.status_signal.emit("Live")
        
        while self._run_flag:
            ret, frame = cap.read()
            if ret:
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy() # CRITICAL: Copy data to prevent Segfault
                self.change_pixmap_signal.emit(convert_to_Qt_format)
            else:
                self.status_signal.emit("Reconnecting...")
                # Reduce CPU spin and allow backend to reset
                time.sleep(2)
                
                # Active Reconnect Logic
                if self._run_flag:
                    cap.release() # CRITICAL: Release broken capture before recreating
                    cap = cv2.VideoCapture(self.url)
                    try:
                        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 15000)
                    except: pass
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    
                    if cap.isOpened():
                        self.status_signal.emit("Live")
                    else:
                        self.status_signal.emit("Connection Failed")
        
        cap.release()

    def stop(self):
        self._run_flag = False
        self.quit()
        self.wait(5000) # Wait up to 5s for thread to finish (matches stimeout)


class SettingsDialog(QDialog):
    def __init__(self, parent=None, cameras=None, theme=THEME_DARK):
        super().__init__(parent)
        self.setWindowTitle("Camera Settings")
        self.setFixedSize(600, 400)
        self.theme = theme
        self.apply_theme()
        
        self.cameras = cameras if cameras else []
        self.current_index = -1

        layout = QVBoxLayout(self)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)
        
        self.list_cams = QListWidget()
        self.list_cams.currentRowChanged.connect(self.on_camera_selected)
        left_layout.addWidget(QLabel("Cameras:"))
        left_layout.addWidget(self.list_cams)
        
        btn_box = QHBoxLayout()
        self.btn_add = QPushButton("+")
        self.btn_add.clicked.connect(self.add_camera)
        self.btn_remove = QPushButton("-")
        self.btn_remove.clicked.connect(self.remove_camera)
        btn_box.addWidget(self.btn_add)
        btn_box.addWidget(self.btn_remove)
        left_layout.addLayout(btn_box)
        
        splitter.addWidget(left_widget)
        
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        self.form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.ip_input = QLineEdit()
        self.port_input = QLineEdit()
        
        self.protocol_input = QComboBox()
        self.protocol_input.addItems(["RTSP (Standard)", "XMeye (Private)"])
        self.protocol_input.currentIndexChanged.connect(self.on_protocol_changed)

        self.user_input = QLineEdit()
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        for w in [self.name_input, self.ip_input, self.port_input, self.user_input, self.pass_input]:
            w.textChanged.connect(self.save_current_edit)

        self.form_layout.addRow("Name:", self.name_input)
        self.form_layout.addRow("Protocol:", self.protocol_input)
        self.form_layout.addRow("IP Address:", self.ip_input)
        self.form_layout.addRow("Port (RTSP):", self.port_input)
        self.form_layout.addRow("Username:", self.user_input)
        self.form_layout.addRow("Password:", self.pass_input)
        
        right_layout.addLayout(self.form_layout)
        right_layout.addStretch()
        
        splitter.addWidget(right_widget)
        splitter.setSizes([200, 400])
        
        layout.addWidget(splitter)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.refresh_list()
        if self.cameras:
            self.list_cams.setCurrentRow(0)

    def apply_theme(self):
        t = self.theme
        self.setStyleSheet(f"""
            QDialog {{ background-color: {t['bg']}; color: {t['text']}; }}
            QListWidget {{ background-color: {t['sidebar']}; border-radius: 8px; border: 1px solid {t['border']}; }}
            QListWidget::item {{ padding: 10px; color: {t['text']}; }}
            QListWidget::item:selected {{ background-color: {t['accent']}; color: white; }}
            QLineEdit {{ background-color: {t['input']}; border: 1px solid {t['border']}; padding: 8px; border-radius: 6px; color: {t['text']}; }}
            QComboBox {{ background-color: {t['input']}; border: 1px solid {t['border']}; padding: 8px; border-radius: 6px; color: {t['text']}; }}
            QComboBox::drop-down {{ border: none; }}
            QPushButton {{ background-color: {t['input']}; border-radius: 6px; padding: 6px; border: none; color: {t['text']}; }}
            QPushButton:hover {{ background-color: {t['border']}; }}
        """)

    def refresh_list(self):
        self.list_cams.blockSignals(True)
        self.list_cams.clear()
        for cam in self.cameras:
            self.list_cams.addItem(cam.get("name", "Unnamed Camera"))
        self.list_cams.blockSignals(False)
        
        if self.current_index >= 0 and self.current_index < len(self.cameras):
            self.list_cams.setCurrentRow(self.current_index)

    def on_camera_selected(self, index):
        if index < 0 or index >= len(self.cameras):
            return
            
        self.current_index = index
        cam = self.cameras[index]
        
        self.name_input.setText(cam.get("name", ""))
        self.ip_input.setText(cam.get("ip", ""))
        self.port_input.setText(cam.get("port", "554"))
        self.user_input.setText(cam.get("user", ""))
        self.pass_input.setText(cam.get("pass", ""))
        
        proto = cam.get("protocol", "rtsp")
        self.protocol_input.setCurrentIndex(1 if proto == "xmeye" else 0)
        self.update_form_visibility()

    def on_protocol_changed(self):
        self.update_form_visibility()
        self.save_current_edit()

    def update_form_visibility(self):
        is_xmeye = self.protocol_input.currentIndex() == 1
        
        # Hide Port for XMeye
        self.port_input.setVisible(not is_xmeye)
        lbl_port = self.form_layout.labelForField(self.port_input)
        if lbl_port: lbl_port.setVisible(not is_xmeye)

    def save_current_edit(self):
        if self.current_index < 0 or self.current_index >= len(self.cameras):
            return
            
        self.cameras[self.current_index] = {
            "name": self.name_input.text(),
            "ip": self.ip_input.text(),
            "port": self.port_input.text(),
            "protocol": "xmeye" if self.protocol_input.currentIndex() == 1 else "rtsp",
            "user": self.user_input.text(),
            "pass": self.pass_input.text()
        }
        
        item = self.list_cams.item(self.current_index)
        if item:
            item.setText(self.name_input.text() or "Unnamed Camera")

    def add_camera(self):
        new_cam = {"name": "New Camera", "ip": "", "port": "554", "protocol": "rtsp", "user": "admin", "pass": ""}
        self.cameras.append(new_cam)
        self.current_index = len(self.cameras) - 1
        self.refresh_list()

    def remove_camera(self):
        if self.current_index < 0 or self.current_index >= len(self.cameras):
            return
            
        self.cameras.pop(self.current_index)
        if self.current_index >= len(self.cameras):
            self.current_index = len(self.cameras) - 1
        self.refresh_list()
        
    def get_cameras(self):
        return self.cameras


class CameraPage(QWidget):
    loading_signal = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.theme = THEME_DARK # CRITICAL: Initialize theme first
        self.video_thread = None # Renamed from self.thread to avoid QObject conflict
        self.is_fullscreen = False
        self.cameras = []
        self.current_cam_index = 0
        self.is_paused = True # Default to paused (No Autoplay)
        self.device_cards = {} # ip -> card
        
        self.load_settings()
        
        # Main Layout (Single View)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # --- Video Player ---
        self.video_container = QWidget()
        self.video_layout = QVBoxLayout(self.video_container)
        self.video_layout.setContentsMargins(0, 0, 0, 0)
        self.video_layout.setSpacing(0)
        
        # Video Label
        self.lbl_video = VideoLabel()
        self.video_layout.addWidget(self.lbl_video, 1)
        
        # Loading Overlay (on top of video)
        self.loading_overlay = LoadingOverlay(self.video_container)
        
        # Video Fade-In Effect
        self.video_opacity = QGraphicsOpacityEffect(self.lbl_video)
        self.video_opacity.setOpacity(0.0)
        self.lbl_video.setGraphicsEffect(self.video_opacity)
        
        self.anim_video = QPropertyAnimation(self.video_opacity, b"opacity")
        self.anim_video.setDuration(1000)
        self.anim_video.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.layout.addWidget(self.video_container, 1) # Expand

        

        
        # --- Bottom Controls & Camera List ---
        self.controls = QWidget()
        self.controls.setFixedHeight(110) # Height for horizontal list
        controls_layout = QHBoxLayout(self.controls)
        controls_layout.setContentsMargins(20, 10, 20, 10)
        controls_layout.setSpacing(20)
        
        # Left Controls Group (Status + Play)
        self.left_controls = QWidget()
        left_layout = QHBoxLayout(self.left_controls)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)
        
        # Status
        self.lbl_cam_status = QLabel("Ready")
        self.lbl_cam_status.setFixedWidth(120) # Fixed width to prevent jitter
        self.lbl_cam_status.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_cam_status.setStyleSheet(f"color: {self.theme['text_sec']}; font-weight: 500;")
        left_layout.addWidget(self.lbl_cam_status)
        
        # Play/Pause Container (to match camera items)
        play_container = QWidget()
        play_container.setFixedWidth(60)
        play_layout = QVBoxLayout(play_container)
        play_layout.setContentsMargins(0, 0, 0, 0)
        play_layout.setSpacing(4)

        self.btn_play = AnimatedButton(icon_name="fa5s.play", color=self.theme['accent'], size=(50, 50), radius=25)
        self.btn_play.clicked.connect(self.toggle_play_pause)
        play_layout.addWidget(self.btn_play, 0, Qt.AlignmentFlag.AlignCenter)
        
        lbl_play = QLabel("Stream")
        lbl_play.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_play.setStyleSheet(f"color: {self.theme['text_sec']}; font-size: 10px;")
        play_layout.addWidget(lbl_play, 0, Qt.AlignmentFlag.AlignCenter)
        
        left_layout.addWidget(play_container)
        
        controls_layout.addWidget(self.left_controls)
        
        # Horizontal Scrollable Camera List
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; }}
            QScrollBar:horizontal {{
                border: none;
                background: {self.theme['card']};
                height: 8px;
                margin: 0px 0px 0px 0px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal {{
                background: {self.theme['border']};
                min-width: 20px;
                border-radius: 4px;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                border: none;
                background: none;
            }}
        """)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.cam_list_container = QWidget()
        self.cam_list_container.setStyleSheet("background: transparent;")
        self.cam_list_layout = QHBoxLayout(self.cam_list_container)
        self.cam_list_layout.setSpacing(15)
        self.cam_list_layout.setContentsMargins(0, 0, 0, 0)
        self.cam_list_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        scroll.setWidget(self.cam_list_container)
        controls_layout.addWidget(scroll, 1) # Expand
        
        # Zoom Controls
        self.btn_zoom_out = AnimatedButton(icon_name="fa5s.search-minus", size=(40, 40), radius=20)
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        controls_layout.addWidget(self.btn_zoom_out)

        self.btn_zoom_in = AnimatedButton(icon_name="fa5s.search-plus", size=(40, 40), radius=20)
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        controls_layout.addWidget(self.btn_zoom_in)

        self.btn_fullscreen = AnimatedButton(icon_name="fa5s.expand", size=(45, 45), radius=22)
        self.btn_fullscreen.clicked.connect(self.toggle_fullscreen)
        controls_layout.addWidget(self.btn_fullscreen)
        
        self.layout.addWidget(self.controls)
        
        self.refresh_camera_list()
        
        # Entry Animation
        self.controls_opacity = QGraphicsOpacityEffect(self.controls)
        self.controls_opacity.setOpacity(1.0)
        self.controls.setGraphicsEffect(self.controls_opacity)

    def resizeEvent(self, event):
        if hasattr(self, 'loading_overlay') and self.loading_overlay.isVisible():
            self.loading_overlay.resize(self.video_container.size())
        super().resizeEvent(event)

    def set_theme(self, theme):
        self.theme = theme
        self.controls.setStyleSheet(f"background-color: {theme['card']}; border-top: none;")
        self.btn_play.set_theme(theme)
        self.btn_zoom_out.set_theme(theme)
        self.btn_zoom_in.set_theme(theme)
        self.btn_fullscreen.set_theme(theme)
        
        for card in self.device_cards.values():
            card.set_theme(theme)

    def load_settings(self):
        self.cameras = []
        if os.path.exists(ICSEE_CONFIG):
            try:
                with open(ICSEE_CONFIG, "r") as f:
                    data = json.load(f)
                    if "cameras" in data:
                        self.cameras = data["cameras"]
                        self.current_cam_index = data.get("last_selected_index", 0)
            except: pass
            
        # Ensure at least one camera or empty list
        if not self.cameras:
             # self.cameras.append({"name": "Demo Camera", "ip": "", "port": "554", "user": "", "pass": ""})
             pass

    def save_settings(self):
        data = {}
        if os.path.exists(ICSEE_CONFIG):
            try:
                with open(ICSEE_CONFIG, "r") as f:
                    data = json.load(f)
            except: pass
            
        data["cameras"] = self.cameras
        data["last_selected_index"] = self.current_cam_index
        
        try:
            with open(ICSEE_CONFIG, "w") as f:
                json.dump(data, f)
        except: pass

    def refresh_camera_list(self):
        # Clear list
        for i in reversed(range(self.cam_list_layout.count())): 
            widget = self.cam_list_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        self.device_cards.clear()
        
        for i, cam in enumerate(self.cameras):
            name = cam.get("name", "Unnamed")
            ip = cam.get("ip", "")
            
            card_id = str(i) 
            
            # Container for Button + Label
            container = QWidget()
            container.setFixedWidth(60)
            c_layout = QVBoxLayout(container)
            c_layout.setContentsMargins(0, 0, 0, 0)
            c_layout.setSpacing(4)
            
            # Compact card for horizontal list (50x50)
            card = DeviceCard(name, "fa5s.video", ip, 
                              on_rename=lambda _, n, idx=i: self.edit_camera(idx), 
                              on_delete=lambda _, idx=i: self.delete_camera(idx),
                              size=(50, 50),
                              bg_color=self.theme['input'])
            
            card.clicked.connect(lambda checked, idx=i: self.on_camera_selected(idx))
            c_layout.addWidget(card, 0, Qt.AlignmentFlag.AlignCenter)
            self.device_cards[card_id] = card
            
            # Label
            lbl = QLabel(name)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color: {self.theme['text_sec']}; font-size: 10px; font-weight: 500;")
            # Truncate if too long
            font_metrics = QFontMetrics(lbl.font())
            elided_text = font_metrics.elidedText(name, Qt.TextElideMode.ElideRight, 60)
            lbl.setText(elided_text)
            
            c_layout.addWidget(lbl, 0, Qt.AlignmentFlag.AlignCenter)
            
            self.cam_list_layout.addWidget(container)
            
        # Add "Add Camera" button
        container_add = QWidget()
        container_add.setFixedWidth(60)
        add_layout = QVBoxLayout(container_add)
        add_layout.setContentsMargins(0, 0, 0, 0)
        add_layout.setSpacing(4)

        btn_add = QPushButton()
        btn_add.setFixedSize(50, 50)
        btn_add.setToolTip("Add Camera")
        btn_add.setIcon(qta.icon("fa5s.plus", color=self.theme['text_sec']))
        btn_add.setIconSize(QSize(24, 24))
        
        btn_add.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['input']};
                border: none;
                border-radius: 25px;
                outline: none;
            }}
            QPushButton:hover {{
                background-color: {self.theme['border']};
            }}
        """)
        btn_add.clicked.connect(self.add_camera)
        add_layout.addWidget(btn_add, 0, Qt.AlignmentFlag.AlignCenter)
        
        lbl_add = QLabel("Add")
        lbl_add.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_add.setStyleSheet(f"color: {self.theme['text_sec']}; font-size: 10px;")
        add_layout.addWidget(lbl_add, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.cam_list_layout.addWidget(container_add)

        # Highlight current
        if self.current_cam_index < len(self.cameras):
            self.on_camera_selected(self.current_cam_index, start_stream=False) # No Autoplay

    def showEvent(self, event):
        super().showEvent(event)
        # self.anim_controls.stop()
        # self.anim_controls.setStartValue(0.0)
        # self.anim_controls.setEndValue(1.0)
        # self.anim_controls.start()
        
        # self.animate_camera_list() # Reverted due to layout scrambling

    def on_camera_selected(self, index, start_stream=True):
        if index < 0 or index >= len(self.cameras): return
        
        self.current_cam_index = index
        
        # Update UI
        for i, card in self.device_cards.items():
            card.setChecked(int(i) == index)
            card.update_style()
            
        if start_stream:
            self.save_settings()
            self.stop_stream()
            self.start_stream()

    def add_camera(self):
        new_cam = {"name": "New Camera", "ip": "", "port": "554", "protocol": "rtsp", "user": "admin", "pass": ""}
        self.cameras.append(new_cam)
        self.save_settings()
        self.refresh_camera_list()
        self.edit_camera(len(self.cameras) - 1)

    def edit_camera(self, index):
        if index < 0 or index >= len(self.cameras): return
        
        dlg = SettingsDialog(self, self.cameras, self.theme)
        dlg.list_cams.setCurrentRow(index)
        if dlg.exec():
            self.cameras = dlg.get_cameras()
            self.save_settings()
            self.update_bridge_config() # Push changes to go2rtc
            self.refresh_camera_list()
            self.stop_stream()
            self.start_stream()

    def delete_camera(self, index):
        if index < 0 or index >= len(self.cameras): return
        
        reply = QMessageBox.question(self, "Delete Camera", 
                                   f"Are you sure you want to delete '{self.cameras[index].get('name')}'?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                                   
        if reply == QMessageBox.StandardButton.Yes:
            # Stop stream FIRST to prevent threading issues/crashes
            self.stop_stream()
            
            self.cameras.pop(index)
            if self.current_cam_index >= len(self.cameras):
                self.current_cam_index = max(0, len(self.cameras) - 1)
            
            self.save_settings()
            self.update_bridge_config() # Push changes (update indices) to go2rtc
            self.refresh_camera_list()
            
            if self.cameras:
                self.start_stream()
    
    
    def show_settings(self):
        self.edit_camera(self.current_cam_index) # Just edit current one or open list

    def update_bridge_config(self):
        """Push configuration updates to go2rtc API for hot-reloading"""
        try:
            for i, cam in enumerate(self.cameras):
                if cam.get("protocol") == "xmeye":
                    user = cam.get("user", "admin")
                    pwd = cam.get("pass", "")
                    ip = cam.get("ip", "")
                    if ip:
                        # 1. Source Stream (raw dvrip)
                        src_raw = f"dvrip://{user}:{pwd}@{ip}"
                        name_raw = f"cam_{i}_raw"
                        self._push_stream_to_bridge(name_raw, src_raw)
                        
                        # 2. Transcoded Stream (ffmpeg)
                        src_ffmpeg = f"ffmpeg:rtsp://127.0.0.1:8554/{name_raw}#video=h264"
                        name_ffmpeg = f"cam_{i}"
                        self._push_stream_to_bridge(name_ffmpeg, src_ffmpeg)

        except Exception as e:
            print(f"Failed to update bridge config: {e}")

    def _push_stream_to_bridge(self, name, src):
        try:
            # enable API in main.py first!
            base_url = "http://127.0.0.1:1984/api/streams"
            params = urllib.parse.urlencode({"src": src, "name": name})
            url = f"{base_url}?{params}"
            
            req = urllib.request.Request(url, method="PUT")
            with urllib.request.urlopen(req) as response:
                pass # Success
        except: 
            pass # Bridge might not be running or API disabled

    def get_current_rtsp_url(self):
        if not self.cameras or self.current_cam_index >= len(self.cameras):
            return None
        
        cam = self.cameras[self.current_cam_index]
        ip = cam.get("ip", "")
        if not ip:
            return None
            
        user = cam.get("user", "")
        pwd = cam.get("pass", "")
        port = cam.get("port", "554")
        
        
        proto = cam.get("protocol", "rtsp")
        if proto == "xmeye":
            # Use go2rtc bridge (stream name matches index in config)
            return f"rtsp://127.0.0.1:8554/cam_{self.current_cam_index}"
            
        return f"rtsp://{user}:{pwd}@{ip}:{port}/live/0/main"

    def start_stream_if_ready(self):
        if self.video_thread is None or not self.video_thread.isRunning():
            self.start_stream()

    def start_stream(self):
        if not self.cameras or self.video_thread and self.video_thread.isRunning():
            return

        url = self.get_current_rtsp_url()
        if not url:
            self.lbl_video.setText("No Camera Configured\nPlease set IP in Settings")
            self.lbl_cam_status.setText("No Config")
            self.lbl_cam_status.setStyleSheet(f"color: {self.theme['text_sec']};")
            self.btn_play.setIcon(qta.icon("fa5s.play", color="white"))
            return

        # Start Progress Animation
        self.loading_signal.emit(0)
        
        # Fake progress up to 80% to indicate "Connecting..."
        self._progress_val = 0
        self._progress_timer = QTimer(self)
        self._progress_timer.timeout.connect(self._animate_progress)
        self._progress_timer.start(50) # Fast updates

        # Show Loading Overlay (spinning circle on video)
        self.loading_overlay.show_loading()
        self.lbl_cam_status.setText("Connecting...")

        self.video_thread = VideoThread(url)
        self.video_thread.change_pixmap_signal.connect(self.update_image) # Connect to wrapper
        self.video_thread.status_signal.connect(self.update_status)
        self.video_thread.start()
        self.btn_play.setIcon(qta.icon("fa5s.pause", color=self.theme['text']))
    
    def update_image(self, qt_img):
        # Wrapper to handle UI updates when frame arrives
        # Check if we were connecting (progress value exists and is not 0)
        if hasattr(self, '_progress_val') and self._progress_val > 0:
             if hasattr(self, '_progress_timer'): self._progress_timer.stop()
             self._progress_val = 0 # Reset internal flag
             
             # Animate to 100% then hide
             self.loading_signal.emit(100)
             self.loading_overlay.hide_loading()
             # Keep at 100% for 500ms so user SEES it done, then hide
             QTimer.singleShot(500, lambda: self.loading_signal.emit(0))
            
        self.lbl_video.update_image(qt_img)

    def _animate_progress(self):
        # Connect animation (stops at 80% until real connection happens)
        if self._progress_val < 80:
            self._progress_val += 1
            self.loading_signal.emit(self._progress_val)
        else:
            # Reached fake limit, wait for real connection
            self._progress_timer.stop()

    @pyqtSlot(str)
    def update_status(self, status):
        self.lbl_cam_status.setText(status)
        if "Failed" in status or "Error" in status:
            self.loading_overlay.hide_loading()
            if hasattr(self, '_progress_timer'): self._progress_timer.stop()
            self.loading_signal.emit(0) # Hide progress bar immediately on failure
        elif status == "Reconnecting...":
            self.loading_overlay.show_loading()
            # Maybe restart progress? 
            # self.loading_signal.emit(10)
            pass
        
        if status == "Live":
            self.lbl_cam_status.setText("🔴 Live")
            self.lbl_cam_status.setStyleSheet(f"color: {self.theme['red']}; font-weight: bold;")
            
            # Hide loading, fade in video
            self.loading_overlay.hide_loading()
            if self.video_opacity.opacity() < 1.0:
                self.anim_video.stop()
                self.anim_video.setStartValue(self.video_opacity.opacity())
                self.anim_video.setEndValue(1.0)
                self.anim_video.start()
                
        elif status == "Connection Failed":
            self.loading_overlay.hide_loading()
            self.lbl_cam_status.setStyleSheet(f"color: {self.theme['red']};")
            self.btn_play.setIcon(qta.icon("fa5s.exclamation-triangle", color="white"))
            self.lbl_video.setText("Connection Failed\nVerify IP or Protocol")
            
        elif status == "Connecting..." or status == "Buffering...":
            self.lbl_cam_status.setStyleSheet(f"color: {self.theme['accent']};")
            self.loading_overlay.show_loading()
            
        else:
            self.loading_overlay.hide_loading()
            self.lbl_cam_status.setStyleSheet(f"color: {self.theme['text_sec']};")


    def stop_stream(self):
        if self.video_thread:
            try:
                self.video_thread.change_pixmap_signal.disconnect()
            except: pass
            self.video_thread.stop()
            self.video_thread.wait() # Ensure thread finishes
            self.video_thread = None
        
        black_pixmap = QPixmap(self.lbl_video.size())
        black_pixmap.fill(Qt.GlobalColor.black)
        self.lbl_video.setPixmap(black_pixmap)
        self.lbl_video.repaint()
        
        self.lbl_video.setText("Paused")
        self.lbl_video.setStyleSheet("background-color: black; color: gray; font-size: 16px;")
        self.btn_play.setIcon(qta.icon("fa5s.play", color="white"))
        self.lbl_cam_status.setText("Paused")
        self.lbl_cam_status.setStyleSheet(f"color: {self.theme['text_sec']};")
        
        # Stop loading visuals
        self.loading_overlay.hide_loading()
        if hasattr(self, '_progress_timer'): self._progress_timer.stop()
        self.loading_signal.emit(0)
        
        # Reset opacity for next fade in
        self.video_opacity.setOpacity(0.0)
        self.loading_overlay.hide_loading()

    def toggle_play_pause(self):
        # Debounce: Prevent spamming (wait 1s between toggles)
        current_time = time.time()
        if hasattr(self, '_last_toggle_time') and current_time - self._last_toggle_time < 1.0:
            return
        self._last_toggle_time = current_time

        self.is_paused = not self.is_paused
        
        if self.is_paused:
            self.stop_stream()
            self.btn_play.setIcon(qta.icon("fa5s.play", color=self.theme['text'])) # White Play (Neutral)
            self.btn_play.setToolTip("Resume Stream")
            self.lbl_cam_status.setText("Paused")
            # Clear video
            self.lbl_video.clear()
            self.lbl_video.setText("Paused")
            self.lbl_video.setStyleSheet("background-color: black; color: gray; font-size: 16px;")
        else:
            self.start_stream()
            self.btn_play.setIcon(qta.icon("fa5s.pause", color=self.theme['text'])) # White Pause (Neutral)
            self.btn_play.setToolTip("Pause Stream")

    def toggle_stream(self):
        self.toggle_play_pause()

    def zoom_in(self):
        self.lbl_video.zoom_in()

    def zoom_out(self):
        self.lbl_video.zoom_out()

    def toggle_fullscreen(self):
        if self.is_fullscreen:
            # Exit Fullscreen
            self.is_fullscreen = False
            
            # Reparent back FIRST
            self.lbl_video.setParent(self.video_container)
            self.video_layout.addWidget(self.lbl_video)
            self.lbl_video.show()
            
            if self.fs_window:
                try:
                    self.fs_window.request_exit.disconnect()
                except: pass
                self.fs_window.force_close = True
                self.fs_window.close()
                self.fs_window = None
            
        else:
            # Enter Fullscreen
            self.is_fullscreen = True
            
            self.fs_window = VideoFullScreenWindow()
            self.fs_window.request_exit.connect(self.toggle_fullscreen) 
            
            # Reparent to fullscreen window
            self.lbl_video.setParent(self.fs_window)
            self.fs_window.layout.addWidget(self.lbl_video)
            self.lbl_video.show()
            
            self.fs_window.showFullScreen()
