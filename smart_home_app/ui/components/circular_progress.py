from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from ..theme import THEME_DARK

DEFAULT_THEME = THEME_DARK

class CircularProgress(QWidget):
    def __init__(self, parent=None, size=80):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._value = 0
        self.theme = DEFAULT_THEME
        
        self.anim = QPropertyAnimation(self, b"value")
        self.anim.setDuration(1000)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    @pyqtProperty(int)
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        self._value = v
        self.update()

    def set_value(self, v):
        if self._value == v: return
        self.target_value = v # Store target
        self.anim.stop()
        self.anim.setStartValue(self._value)
        self.anim.setEndValue(v)
        self.anim.start()

    def replay_animation(self):
        target = self._value
        self._value = 0
        self.update()
        self.anim.stop()
        self.anim.setStartValue(0)
        self.anim.setEndValue(target)
        self.anim.start()

    def set_theme(self, theme):
        self.theme = theme
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect().adjusted(4, 4, -4, -4)
        
        # Track
        painter.setPen(QPen(QColor(self.theme['border']), 4))
        painter.drawEllipse(rect)
        
        # Progress Color
        color = QColor(self.theme['green'])
        if self._value < 20: color = QColor(self.theme['red'])
        elif self._value < 50: color = QColor(self.theme['orange'])

        # Progress Arc
        if self._value > 0:
            painter.setPen(QPen(color, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            span = int(-self._value * 3.6 * 16)
            painter.drawArc(rect, 90 * 16, span)
            
        # Text: Value
        painter.setPen(color)
        font = self.font()
        font.setPixelSize(18)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{int(self._value)}%")
