
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen
from PyQt6.QtWidgets import QWidget, QFrame, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QRect
import qtawesome as qta
from ..theme import THEME_DARK
from ..widgets import AnimatedButton

class AddressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self.text = ""
        self.progress = 0
        self.theme = THEME_DARK
        
    def set_theme(self, theme):
        self.theme = theme
        self.update()
        
    def set_text(self, text):
        self.text = text
        self.update()
        
    def set_progress(self, val):
        self.progress = val
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Background (Input Color)
        rect = self.rect()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self.theme['input']))
        painter.drawRoundedRect(rect, 10, 10)
        
        # 2. Progress Fill (Blue)
        if self.progress > 0:
            prog_width = int(rect.width() * (self.progress / 100))
            if prog_width > 0:
                painter.setBrush(QColor("#007AFF"))
                # Draw rounded rect clip? Or just rect?
                # To keep rounded corners on left usually:
                # Simple approach: Draw same rounded rect but clipped?
                # Easier: Draw rect with clip path.
                
                path = qta.QtGui.QPainterPath()
                path.addRoundedRect(0, 0, rect.width(), rect.height(), 10, 10)
                painter.setClipPath(path)
                
                painter.setClipPath(path)
                
                # Draw thin line at bottom (2px)
                line_height = 2
                painter.drawRect(0, rect.height() - line_height, prog_width, line_height)
                painter.setClipping(False)

        # 3. Text (Centered)
        painter.setPen(QColor(self.theme['text']))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text)

class SafariToolbar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(52)
        self.theme = THEME_DARK
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)
        
        # Sidebar Toggle
        self.btn_sidebar = AnimatedButton(icon_name="fa5s.columns", size=(36, 36))
        layout.addWidget(self.btn_sidebar)
        
        # Navigation Buttons
        self.btn_back = AnimatedButton(icon_name="fa5s.chevron-left", size=(36, 36))
        
        layout.addWidget(self.btn_back)
        
        # Address Bar
        self.address_bar = AddressBar()
        layout.addWidget(self.address_bar, 1)
        
        self.apply_theme()
        
    def apply_theme(self):
        t = self.theme
        self.setStyleSheet(f"""
            SafariToolbar {{ background-color: {t['bg']}; border-bottom: 1px solid {t['border']}; }}
        """)
        self.btn_sidebar.set_theme(t)
        self.btn_back.set_theme(t)
        self.address_bar.set_theme(t)

    def set_title(self, title):
        self.address_bar.set_text(title)
        
    def set_progress(self, val):
        self.address_bar.set_progress(val)
