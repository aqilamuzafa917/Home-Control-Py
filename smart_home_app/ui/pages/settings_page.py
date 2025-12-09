
import os
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QFrame, QScrollArea, QMessageBox, QTextEdit
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont
import qtawesome as qta
from ..theme import THEME_DARK
from ...core.constants import ICSEE_CONFIG, XIAOMI_CONFIG, LOG_FILE

class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.theme = THEME_DARK
        
        # Main Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Scroll Area for Settings
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Container
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(40, 40, 40, 40)
        self.container_layout.setSpacing(30)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll.setWidget(self.container)
        self.layout.addWidget(self.scroll)
        
        # --- Content ---
        
        # Header
        lbl_header = QLabel("Settings")
        lbl_header.setFont(QFont("Helvetica Neue", 24, QFont.Weight.Bold))
        lbl_header.setStyleSheet(f"color: {self.theme['text']};")
        self.container_layout.addWidget(lbl_header)
        
        # Section: Configuration Files
        self.add_section_header("Configuration")
        
        self.add_file_viewer("Camera & WiZ Config", str(ICSEE_CONFIG))
        self.add_file_viewer("Xiaomi Token Config", str(XIAOMI_CONFIG))
        
        # Section: Logs
        self.add_section_header("Application Logs")
        
        self.log_viewer = self.add_file_viewer("App Logs", str(LOG_FILE), height=150)

        # go2rtc Logs
        go2rtc_log = os.path.join(os.path.dirname(LOG_FILE), "go2rtc.log")
        self.go2rtc_viewer = self.add_file_viewer("Video Bridge (go2rtc) Logs", go2rtc_log, height=150)
        
        # Logs Buttons (Refresh & Clear)
        logs_btn_container = QWidget()
        logs_btn_layout = QHBoxLayout(logs_btn_container)
        logs_btn_layout.setContentsMargins(0, 0, 0, 0)
        logs_btn_layout.setSpacing(15)
        
        self.btn_refresh_logs = QPushButton("  Refresh Logs")
        self.btn_refresh_logs.setIcon(qta.icon("fa5s.sync-alt", color=self.theme['accent']))
        self.btn_refresh_logs.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh_logs.setFixedHeight(40)
        self.btn_refresh_logs.clicked.connect(self.refresh_logs)
        logs_btn_layout.addWidget(self.btn_refresh_logs)

        self.btn_clear_logs = QPushButton("  Clear Logs")
        self.btn_clear_logs.setIcon(qta.icon("fa5s.trash-alt", color=self.theme['red']))
        self.btn_clear_logs.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_logs.setFixedHeight(40)
        self.btn_clear_logs.clicked.connect(self.clear_logs)
        logs_btn_layout.addWidget(self.btn_clear_logs)
        
        self.container_layout.addWidget(logs_btn_container)
        
        # About Section
        self.add_section_header("About")
        
        about_card = QFrame()
        about_card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme['card']};
                border-radius: 12px;
                border: 1px solid {self.theme['border']};
            }}
        """)
        about_layout = QVBoxLayout(about_card)
        about_layout.setContentsMargins(20, 20, 20, 20)
        
        lbl_app_name = QLabel("Home Control Py")
        lbl_app_name.setFont(QFont("Helvetica Neue", 16, QFont.Weight.Bold))
        lbl_app_name.setStyleSheet(f"color: {self.theme['text']}; border: none;")
        about_layout.addWidget(lbl_app_name)
        
        lbl_version = QLabel("Version 1.0.0 (PyQt6 Native)")
        lbl_version.setStyleSheet(f"color: {self.theme['text_sec']}; border: none; margin-top: 5px;")
        about_layout.addWidget(lbl_version)
        
        self.container_layout.addWidget(about_card)
        
        self.container_layout.addStretch()
        
        self.apply_theme()

    def add_section_header(self, text):
        lbl = QLabel(text.upper())
        lbl.setStyleSheet(f"color: {self.theme['text_sec']}; font-weight: bold; font-size: 12px; margin-top: 10px;")
        self.container_layout.addWidget(lbl)

    def add_file_viewer(self, title, path, height=120):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Title & Path
        header_layout = QHBoxLayout()
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"color: {self.theme['text']}; font-weight: 600;")
        header_layout.addWidget(lbl_title)
        
        lbl_path = QLabel(path)
        lbl_path.setStyleSheet(f"color: {self.theme['text_sec']}; font-size: 11px;")
        header_layout.addWidget(lbl_path, 0, Qt.AlignmentFlag.AlignRight)
        
        layout.addLayout(header_layout)
        
        # Content Viewer
        viewer = QTextEdit()
        viewer.setReadOnly(True)
        viewer.setFixedHeight(height)
        viewer.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.theme['input']};
                color: {self.theme['text_sec']};
                border: 1px solid {self.theme['border']};
                border-radius: 8px;
                font-family: 'Menlo', 'Consolas', monospace;
                font-size: 11px;
                padding: 5px;
            }}
        """)
        
        content = "File not found."
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    content = f.read()
            except Exception as e:
                content = f"Error reading file: {e}"
        
        viewer.setText(content)
        layout.addWidget(viewer)
        
        self.container_layout.addWidget(container)
        return viewer

    def apply_theme(self):
        t = self.theme
        self.setStyleSheet(f"background-color: {t['bg']};")
        self.scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                border: none;
                background: {t['bg']};
                width: 12px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {t['input']};
                min-height: 20px;
                border-radius: 6px;
                margin: 2px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        self.container.setStyleSheet(f"background-color: {t['bg']};")
        
        self.btn_clear_logs.setStyleSheet(f"""
            QPushButton {{
                background-color: {t['card']};
                color: {t['red']};
                border: 1px solid {t['border']};
                border-radius: 10px;
                text-align: left;
                padding-left: 20px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {t['input']};
                border: 1px solid {t['red']};
            }}
            QPushButton:pressed {{
                background-color: {t['border']};
            }}
        """)
        
        self.btn_refresh_logs.setStyleSheet(f"""
            QPushButton {{
                background-color: {t['card']};
                color: {t['accent']};
                border: 1px solid {t['border']};
                border-radius: 10px;
                text-align: left;
                padding-left: 20px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {t['input']};
                border: 1px solid {t['accent']};
            }}
            QPushButton:pressed {{
                background-color: {t['border']};
            }}
        """)

    def clear_logs(self):
        try:
            if os.path.exists(LOG_FILE):
                open(LOG_FILE, 'w').close()
            
            go2rtc_log = os.path.join(os.path.dirname(LOG_FILE), "go2rtc.log")
            if os.path.exists(go2rtc_log):
                open(go2rtc_log, 'w').close()
                
            self.refresh_logs() # Reuse refresh logic to clear UI
            QMessageBox.information(self, "Logs Cleared", "All logs have been cleared successfully.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to clear logs: {str(e)}")

    def refresh_logs(self):
        # Refresh App Log
        content = "File not found."
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, "r") as f:
                    content = f.read()
            except Exception as e:
                content = f"Error reading file: {e}"
        self.log_viewer.setText(content)
        self.log_viewer.verticalScrollBar().setValue(self.log_viewer.verticalScrollBar().maximum())

        # Refresh go2rtc Log
        go2rtc_log = os.path.join(os.path.dirname(LOG_FILE), "go2rtc.log")
        content_rtc = "File not found / No output yet."
        if os.path.exists(go2rtc_log):
            try:
                with open(go2rtc_log, "r") as f:
                    content_rtc = f.read()
            except Exception as e:
                content_rtc = f"Error reading file: {e}"
        
        if hasattr(self, 'go2rtc_viewer'):
            self.go2rtc_viewer.setText(content_rtc)
            self.go2rtc_viewer.verticalScrollBar().setValue(self.go2rtc_viewer.verticalScrollBar().maximum())
