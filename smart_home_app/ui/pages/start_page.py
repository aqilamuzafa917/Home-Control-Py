
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont
import qtawesome as qta
from ..theme import THEME_DARK
from ..widgets import AnimatedButton

class StartPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = THEME_DARK
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(40)
        
        # Title
        title = QLabel("Home Control")
        title.setFont(QFont("Helvetica Neue", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {self.theme['text']};")
        layout.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft)

        # Grid
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(30)
        
        self.items = [
            ("WiZ Lights", "fa5s.lightbulb", "#FFC864"),
            ("Air Purifier", "fa5s.wind", "#69D84C"),
            ("Camera", "fa5s.video", "#0A84FF")
        ]
        
        for i, (name, icon, color) in enumerate(self.items):
            # Enable hover animations
            btn = AnimatedButton(icon_name=icon, color=color, size=(80, 80), hover_color_change=True)
            btn.setIconSize(QSize(40, 40))
            
            lbl = QLabel(name)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color: {self.theme['text']}; font-size: 13px; margin-top: 8px;")
            
            container = QWidget()
            vbox = QVBoxLayout(container)
            vbox.setContentsMargins(0, 0, 0, 0)
            vbox.setSpacing(0)
            vbox.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)
            vbox.addWidget(lbl, 0, Qt.AlignmentFlag.AlignCenter)
            
            grid_layout.addWidget(container, 0, i)
            
            # Store button for connection
            setattr(self, f"btn_{i}", btn)
            
        layout.addWidget(grid_widget)
        layout.addStretch()
