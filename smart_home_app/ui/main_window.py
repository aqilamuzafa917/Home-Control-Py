
import sys
import platform
import logging
import traceback
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QKeySequence, QShortcut
import qtawesome as qta

from ..core.constants import APP_TITLE, DEFAULT_SIZE, MIN_SIZE
from .theme import THEME_DARK
from .components.toolbar import SafariToolbar
from .components.stacked_widget import SlidingStackedWidget
from .pages.start_page import StartPage
from .pages.wiz_page import WiZTab
from .pages.air_purifier_page import AirPurifierTab
from .pages.camera_page import CameraPage
from .pages.settings_page import SettingsPage

class SmartHomeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # OS-Specific Window Flags
        if platform.system() == "Darwin":
            # macOS: Remove minimize button (yellow), keep close and maximize
            self.setWindowFlags(
                Qt.WindowType.Window |
                Qt.WindowType.WindowTitleHint |
                Qt.WindowType.WindowCloseButtonHint |
                Qt.WindowType.WindowMaximizeButtonHint |
                Qt.WindowType.CustomizeWindowHint
            )
        
        self.setWindowTitle(APP_TITLE)
        self.resize(*DEFAULT_SIZE)
        self.setMinimumSize(*MIN_SIZE)
        
        self.current_theme = THEME_DARK
        self.is_dark_mode = True
        
        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar Container
        self.sidebar_container = QWidget()
        self.sidebar_container.setMaximumWidth(260)
        self.sidebar_container.setMinimumWidth(0)
        sidebar_layout = QVBoxLayout(self.sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        # Logo Area
        self.logo_label = QLabel("   Home Control")
        self.logo_label.setFixedHeight(60)
        self.logo_label.setFont(QFont("Helvetica Neue", 18, QFont.Weight.Bold))
        sidebar_layout.addWidget(self.logo_label)
        
        # Tabs List
        self.sidebar = QListWidget()
        self.sidebar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        self.add_sidebar_item("Start Page", "fa5s.compass") # Hidden/Top item
        self.add_sidebar_header("DEVICES")
        self.add_sidebar_item("WiZ Lights", "fa5s.lightbulb")
        self.add_sidebar_item("Xiaomi Air Purifier", "fa5s.wind")
        self.add_sidebar_item("Security Camera", "fa5s.video")
        
        self.sidebar.currentRowChanged.connect(self.switch_tab)
        sidebar_layout.addWidget(self.sidebar)
        
        # Spacer to push settings to bottom
        sidebar_layout.addStretch()
        
        # Settings Button (Subtle, at bottom)
        self.btn_settings = QPushButton("   Settings")
        self.btn_settings.setIcon(qta.icon("fa5s.cog", color=self.current_theme['text_sec']))
        self.btn_settings.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.current_theme['text_sec']};
                text-align: left;
                padding: 10px 15px;
                border-radius: 6px;
                font-weight: 500;
                font-size: 13px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {self.current_theme['sidebar_hover']};
                color: {self.current_theme['text']};
            }}
        """)
        self.btn_settings.clicked.connect(lambda: self.switch_tab(6))
        sidebar_layout.addWidget(self.btn_settings)
        
        main_layout.addWidget(self.sidebar_container)

        # Main Content Area (Right Side)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Safari Toolbar
        self.toolbar = SafariToolbar()
        self.toolbar.btn_back.clicked.connect(self.go_back)
        self.toolbar.btn_sidebar.clicked.connect(self.toggle_sidebar)
        content_layout.addWidget(self.toolbar)

        # Stacked Pages
        self.stack = SlidingStackedWidget()
        content_layout.addWidget(self.stack)
        
        main_layout.addWidget(content_widget)

        self.start_page = StartPage()
        self.wiz_tab = WiZTab()
        self.air_tab = AirPurifierTab()
        self.cam_tab = CameraPage()
        self.settings_tab = SettingsPage()

        self.stack.addWidget(self.start_page)
        self.stack.addWidget(self.wiz_tab)
        self.stack.addWidget(self.air_tab)
        self.stack.addWidget(self.cam_tab)
        self.stack.addWidget(self.settings_tab)
        
        # Connect Loading Signal
        self.cam_tab.loading_signal.connect(self.toolbar.set_progress)
        
        # Connect Start Page Buttons
        self.start_page.btn_0.clicked.connect(lambda: self.sidebar.setCurrentRow(2))
        self.start_page.btn_1.clicked.connect(lambda: self.sidebar.setCurrentRow(3))
        self.start_page.btn_2.clicked.connect(lambda: self.sidebar.setCurrentRow(4))

        self.sidebar.setCurrentRow(0) # Start Page
        self.toolbar.set_title("Start Page")
        
        self.shortcut_esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self.shortcut_esc.activated.connect(self.handle_esc)
        
        self.apply_theme()

    def add_sidebar_header(self, text):
        item = QListWidgetItem(text)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        font = QFont("Helvetica Neue", 11, QFont.Weight.Bold)
        item.setFont(font)
        self.sidebar.addItem(item)

    def add_sidebar_item(self, name, icon_name):
        item = QListWidgetItem(f"   {name}")
        # Finder Blue for icons by default
        item.setIcon(qta.icon(icon_name, color="#0A84FF")) 
        font = QFont()
        font.setPointSize(13)
        item.setFont(font)
        self.sidebar.addItem(item)

    def switch_tab(self, index):
        try:
            # Index mapping:
            # 0: Start Page
            # 1: Header (DEVICES)
            # 2: WiZ
            # 3: Air
            # 4: Cam
            # 5: Header (SYSTEM)
            # 6: Settings
            
            if index == 1 or index == 5: return # Headers
            
            # Map list index to stack index
            # Stack: [Start, WiZ, Air, Cam, Settings]
            stack_index = 0
            title = "Start Page"
            
            if index == 0:
                stack_index = 0
                title = "Start Page"
            elif index == 2:
                stack_index = 1
                title = "WiZ Lights"
            elif index == 3:
                stack_index = 2
                title = "Xiaomi Air Purifier"
            elif index == 4:
                stack_index = 3
                title = "Security Camera"
            elif index == 6:
                stack_index = 4
                title = "Settings"
                # Avoid recursion if clearSelection triggers signals
                self.sidebar.blockSignals(True)
                self.sidebar.clearSelection()
                self.sidebar.setCurrentRow(-1) # Reset row so clicking an item again triggers signal
                self.sidebar.blockSignals(False)
            
            if stack_index < 0 or stack_index >= self.stack.count():
                logging.error(f"Invalid stack index: {stack_index}")
                return

            # Store history (simple 1-level history for now)
            if self.stack.currentIndex() != stack_index:
                self.last_sidebar_row = self.sidebar.currentRow() if self.sidebar.currentRow() >= 0 else 0
                # If we were in settings (row -1), default to 0

            # self.stack.setCurrentIndex(stack_index)
            self.stack.slideInIdx(stack_index)
            self.toolbar.set_title(title)
            
            # Toggle Back Button
            if stack_index == 0:
                self.toolbar.btn_back.hide()
            else:
                self.toolbar.btn_back.show()
            
            # Update Settings Button State
            self.btn_settings.setStyleSheet(f"""
                QPushButton {{
                    background-color: {'transparent' if index != 6 else self.current_theme['accent']};
                    color: {self.current_theme['text_sec'] if index != 6 else 'white'};
                    text-align: left;
                    padding: 10px 15px;
                    border-radius: 6px;
                    font-weight: 500;
                    font-size: 13px;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: {self.current_theme['sidebar_hover'] if index != 6 else self.current_theme['accent']};
                    color: {self.current_theme['text'] if index != 6 else 'white'};
                }}
            """)

            if stack_index == 3:
                # self.cam_tab.start_stream_if_ready()
                pass
            else:
                pass 
                # self.cam_tab.stop_stream() # Keep stream running for instant switch (User Request)
                
        except Exception as e:
            logging.error(f"Error switching tab: {e}")
            traceback.print_exc()
            
    def go_back(self):
        # If in settings, go back to last sidebar row
        if self.stack.currentIndex() == 4: # Settings
            if hasattr(self, 'last_sidebar_row'):
                self.sidebar.setCurrentRow(self.last_sidebar_row)
            else:
                self.sidebar.setCurrentRow(0)
        else:
            self.sidebar.setCurrentRow(0)
        
    def toggle_sidebar(self):
        width = self.sidebar_container.width()
        
        if width > 0:
            end_width = 0
            # Don't hide immediately, wait for animation
        else:
            end_width = 260
            self.sidebar_container.show()
            self.sidebar_container.setMaximumWidth(0) # Start from 0 if showing
            width = 0
            
        self.anim_side = QPropertyAnimation(self.sidebar_container, b"maximumWidth")
        self.anim_side.setDuration(300)
        self.anim_side.setStartValue(width)
        self.anim_side.setEndValue(end_width)
        self.anim_side.setEasingCurve(QEasingCurve.Type.InOutQuart)
        
        if end_width == 0:
            self.anim_side.finished.connect(lambda: self.sidebar_container.hide())
            
        self.anim_side.start()

    def apply_theme(self):
        t = self.current_theme
        
        # Main Window
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {t['bg']}; }}
            QWidget {{ color: {t['text']}; font-family: 'Helvetica Neue', sans-serif; }}
            QListWidget {{ background-color: {t['sidebar']}; border: none; outline: none; }}
            QListWidget::item {{ padding: 6px 10px; border-radius: 6px; color: {t['text']}; margin: 2px 10px; font-weight: 500; font-size: 13px; }}
            QListWidget::item:selected {{ background: {t['accent_gradient']}; color: white; }}
            QListWidget::item:hover {{ background-color: {t['input']}; }}
            QListWidget::item:disabled {{ background-color: transparent; color: #8E8E93; font-size: 11px; font-weight: bold; padding-top: 12px; padding-bottom: 4px; }}
            QPushButton {{ background-color: {t['input']}; border-radius: 8px; padding: 10px; border: none; font-weight: 600; color: {t['text']}; }}
            QPushButton:hover {{ background-color: {t['border']}; }}
            QLineEdit {{ background-color: {t['input']}; border-radius: 8px; padding: 10px; color: {t['text']}; border: 1px solid {t['border']}; }}
            
            QComboBox {{ 
                background-color: {t['input']}; 
                border-radius: 8px; 
                padding: 8px 12px; 
                color: {t['text']}; 
                border: 1px solid {t['border']}; 
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {t['card']};
                color: {t['text']};
                selection-background-color: {t['accent']};
                selection-color: white;
                border: 1px solid {t['border']};
                outline: none;
                padding: 4px;
            }}
            
            CardWidget {{
                background-color: {t['card']};
                border-radius: 16px;
                border: 1px solid {t['border']};
            }}
        """)
        
        # Sidebar
        self.sidebar_container.setStyleSheet(f"background-color: {t['sidebar']}; border-right: 1px solid {t['border']};")
        self.logo_label.setStyleSheet(f"color: {t['text']};")
        
        # Tabs
        self.wiz_tab.set_theme(t)
        self.air_tab.set_theme(t)
        self.cam_tab.set_theme(t)
        self.settings_tab.apply_theme()

    def closeEvent(self, event):
        self.cam_tab.stop_stream()
        
        if platform.system() == "Darwin":
            # macOS: Hide window (minimize to app icon)
            event.ignore()
            self.hide()
        else:
            # Windows: Standard close = Quit
            event.accept()
        
    def handle_esc(self):
        if self.cam_tab.is_fullscreen:
            self.cam_tab.toggle_fullscreen()
