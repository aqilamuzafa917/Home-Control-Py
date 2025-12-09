from PyQt6.QtWidgets import QWidget, QLabel, QGraphicsDropShadowEffect, QPushButton, QSlider, QStyleOptionSlider, QSizePolicy, QFrame, QVBoxLayout, QHBoxLayout, QMenu, QStackedWidget, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QSize, QRect, QPoint, QPropertyAnimation, QEasingCurve, pyqtProperty, QParallelAnimationGroup, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QFont, QPen, QBrush, QLinearGradient, QIcon, QPixmap

class FadeStackedWidget(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fade_anim = None

    def setCurrentIndex(self, index):
        self.fade_transition(index)

    def fade_transition(self, index):
        if index == self.currentIndex(): return
        
        current_widget = self.currentWidget()
        next_widget = self.widget(index)
        
        if not current_widget:
            super().setCurrentIndex(index)
            return

        # Create screen of current widget
        pixmap = QPixmap(self.size())
        current_widget.render(pixmap)
        
        # Overlay label
        self.overlay = QLabel(self)
        self.overlay.setPixmap(pixmap)
        self.overlay.setGeometry(0, 0, self.width(), self.height())
        self.overlay.show()
        
        # Switch immediately behind overlay
        super().setCurrentIndex(index)
        
        # Animate overlay opacity
        self.effect = QGraphicsOpacityEffect(self.overlay)
        self.overlay.setGraphicsEffect(self.effect)
        
        self.anim = QPropertyAnimation(self.effect, b"opacity")
        self.anim.setDuration(250) # Fast fade
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.anim.finished.connect(self.cleanup_overlay)
        self.anim.start()

    def cleanup_overlay(self):
        if hasattr(self, 'overlay'):
            self.overlay.hide()
            self.overlay.deleteLater()
            del self.overlay
import qtawesome as qta
from .theme import THEME_DARK

class ClickableLabel(QLabel):
    clicked = pyqtSignal()
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

class CardWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Style set dynamically
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(20)
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(4)
        self.shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(self.shadow)

class AirQualityRing(QWidget):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200) # Reduced from 220 to fix collision
        self._aqi = 0
        self._animated_aqi = 0
        self._color = QColor(THEME_DARK["green"])
        self.theme = THEME_DARK
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.anim = QPropertyAnimation(self, b"animated_aqi")
        self.anim.setDuration(1000)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    @pyqtProperty(int)
    def animated_aqi(self):
        return self._animated_aqi

    @animated_aqi.setter
    def animated_aqi(self, value):
        self._animated_aqi = value
        self.update()

    def set_theme(self, theme):
        self.theme = theme
        self.update()

    def set_aqi(self, value):
        self._aqi = value
        if value < 50: self._color = QColor(self.theme["green"])
        elif value < 100: self._color = QColor(self.theme["orange"])
        else: self._color = QColor(self.theme["red"])
        
        self.anim.setStartValue(self._animated_aqi)
        self.anim.setEndValue(value)
        self.anim.start()

    def replay_animation(self):
        target = self._aqi
        self._animated_aqi = 0
        self.update()
        self.anim.stop()
        self.anim.setStartValue(0)
        self.anim.setEndValue(target)
        self.anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect().adjusted(10, 10, -10, -10)
        
        # Background Ring
        pen = QPen(QColor(self.theme["border"]), 12)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, -90 * 16, 360 * 16)
        
        # Progress Ring
        angle = min(360, int((self._animated_aqi / 300.0) * 360))
        pen.setColor(self._color)
        painter.setPen(pen)
        painter.drawArc(rect, 90 * 16, -angle * 16)
        
        # Text
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setFont(QFont("Helvetica Neue", 48, QFont.Weight.Bold))
        painter.setPen(QColor(self.theme["text"]))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(int(self._animated_aqi)))
        
        painter.setFont(QFont("Helvetica Neue", 14))
        painter.setPen(QColor(self.theme["text_sec"]))
        painter.drawText(rect.adjusted(0, 60, 0, 0), Qt.AlignmentFlag.AlignCenter, "PM2.5")

class DeviceCard(QPushButton):
    def __init__(self, name, icon_name, ip, parent=None, on_rename=None, on_delete=None, size=(140, 140), bg_color=None):
        super().__init__(parent)
        self.is_small = size[0] <= 80
        
        if self.is_small:
            self.setFixedSize(*size)
        else:
            self.setMinimumSize(*size)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.setFixedHeight(size[1]) # Keep height fixed effectively, but width expands
            
        self.setCheckable(True)
        self.name = name
        self.ip = ip
        self.theme = THEME_DARK
        self.on_rename = on_rename
        self.on_delete = on_delete
        self.bg_color = bg_color
        self.icon_name = icon_name
        
        if self.is_small:
            self.setIcon(qta.icon(icon_name, color=self.theme['text']))
            self.setIconSize(QSize(24, 24))
            self.setToolTip(f"{name} ({ip})")
            # Initialize attributes to None to avoid errors if accessed
            self.icon_lbl = None
            self.name_lbl = None
            self.ip_lbl = None
            self.status_lbl = None
        else:
            layout = QVBoxLayout(self)
            if size[1] <= 80:
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(0)
            else:
                layout.setContentsMargins(5, 10, 5, 10)
                layout.setSpacing(5)
            
            self.icon_lbl = QLabel()
            self.icon_lbl.setFixedSize(32, 32)
            self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.icon_lbl.setStyleSheet("background: transparent;")
            self.icon_pixmap = qta.icon(icon_name, color=self.theme['text']).pixmap(24, 24)
            self.icon_lbl.setPixmap(self.icon_pixmap)
            
            self.name_lbl = QLabel(name)
            self.name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.name_lbl.setWordWrap(True)
            self.name_lbl.setStyleSheet(f"color: {self.theme['text']}; font-size: 11px; font-weight: 600; background: transparent;")
            
            self.ip_lbl = QLabel(ip)
            self.ip_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.ip_lbl.setStyleSheet(f"color: white; font-size: 9px; background: transparent;")
            
            self.status_lbl = QLabel("Offline")
            self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.status_lbl.setStyleSheet(f"color: {self.theme['text_sec']}; font-size: 9px; background: transparent;")
            
            layout.addWidget(self.icon_lbl, 0, Qt.AlignmentFlag.AlignCenter)
            
            if size[0] > 80: # Only show text if wide enough
                layout.addWidget(self.name_lbl, 0, Qt.AlignmentFlag.AlignCenter)
                if size[1] > 100: # Only show IP/Status if tall enough
                    layout.addWidget(self.ip_lbl, 0, Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(self.status_lbl, 0, Qt.AlignmentFlag.AlignCenter)
            else:
                self.setToolTip(f"{name} ({ip})")
        
        self._current_bg = self.bg_color if self.bg_color else self.theme['card']
        
        # Animation support
        self._bg_anim = QPropertyAnimation(self, b"bg_color_prop", self)
        self._bg_anim.setDuration(200)
        self._bg_anim.setEasingCurve(QEasingCurve.Type.OutQuad)

        self.update_style()

    @pyqtProperty(QColor)
    def bg_color_prop(self):
        return QColor(self._current_bg)

    @bg_color_prop.setter
    def bg_color_prop(self, color):
        self._current_bg = color.name()
        self.update_style()
        
    def enterEvent(self, event):
        if not self.isChecked():
            start = QColor(self._current_bg)
            end = start.lighter(115) # Make it visibly lighter
            self._bg_anim.setStartValue(start)
            self._bg_anim.setEndValue(end)
            self._bg_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        # Always reset hover state to base, even if checked.
        # This ensures that when unchecking later, the color is correct (not stuck on hover color).
        start = self._bg_anim.currentValue() if self._bg_anim.state() == QPropertyAnimation.State.Running else QColor(self._current_bg)
        base = QColor(self.bg_color if self.bg_color else self.theme['card'])
        
        self._bg_anim.stop()
        self._bg_anim.setStartValue(start)
        self._bg_anim.setEndValue(base)
        self._bg_anim.start()
            
        super().leaveEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        if self.on_rename:
            menu.addAction("Edit", lambda: self.on_rename(self.ip, self.name))
        if self.on_delete:
            menu.addAction("Delete", lambda: self.on_delete(self.ip))
            
        menu.setStyleSheet(f"""
            QMenu {{ background-color: {self.theme['card']}; border: 1px solid {self.theme['border']}; }}
            QMenu::item {{ color: {self.theme['text']}; padding: 6px 20px; }}
            QMenu::item:selected {{ background-color: {self.theme['accent']}; color: white; }}
        """)
        menu.exec(event.globalPos())

    def set_theme(self, theme):
        self.theme = theme
        self._current_bg = self.bg_color if self.bg_color else theme['card']
        self.update_style()

    def set_status(self, online):
        if self.status_lbl:
            if online is None:
                self.status_lbl.setText("")
            else:
                self.status_lbl.setText("Online" if online else "Offline")
                self.status_lbl.setStyleSheet(f"color: {self.theme['green'] if online else self.theme['text_sec']}; font-size: 11px; background: transparent;")

    def update_style(self):
        t = self.theme
        bg = self._current_bg
        border = t['border']
        icon_color = t['text']
        
        if self.isChecked():
            bg = t['accent'] # Use flat color to match Play button
            border = t['accent']
            icon_color = "white"
        
        if self.is_small:
            self.setIcon(qta.icon(self.icon_name, color=icon_color))
        
        radius = 12
        border_val = f"1px solid {border}"
        if self.height() <= 50:
            radius = self.height() // 2 # Circular for small buttons
            border_val = "none"
            
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                border: {border_val};
                border-radius: {radius}px;
                outline: none;
            }}
            QPushButton:hover {{
                border: 1px solid {t['accent']};
            }}
            QPushButton:checked {{
                background-color: {t['accent']};
                border: 1px solid {t['accent']};
            }}
        """)

class GlowingIcon(QPushButton):
    def __init__(self, icon_name, size=60, color=THEME_DARK["text_sec"]):
        super().__init__()
        self.setFixedSize(size, size)
        self._default_color = color
        self._is_on = False
        self.theme = THEME_DARK
        self._icon_name = icon_name
        
        self.setIconSize(QSize(int(size/2), int(size/2)))
        self.update_style()

    def set_theme(self, theme):
        self.theme = theme
        self._default_color = theme["text_sec"]
        self.update_style()

    def set_active(self, active, color=None):
        self._is_on = active
        self._active_color = color or self.theme["accent_gradient"]
        self.update_style()

    def update_style(self):
        bg = self.theme["input"]
        fg = self._default_color
        
        if self._is_on:
            bg = self._active_color
            fg = "white"
            
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                border-radius: {self.height()//2}px;
                border: none;
            }}
        """)
        self.setIcon(qta.icon(self._icon_name, color=fg))

class GradientSlider(QSlider):
    def __init__(self, parent=None, colors=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.theme = THEME_DARK
        self.setFixedHeight(30) # Ensure enough height for handle
        # Default Temp Gradient
        self.colors = colors if colors else [QColor(255, 167, 87), QColor(255, 255, 255), QColor(200, 220, 255)]
        
        self.anim = QPropertyAnimation(self, b"value")
        self.anim.setDuration(1000)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def replay_animation(self):
        target = self.value()
        self.setValue(self.minimum())
        self.anim.stop()
        self.anim.setStartValue(self.minimum())
        self.anim.setEndValue(target)
        self.anim.start()

    def animate_to_value(self, target):
        if target == self.value(): return
        self.anim.stop()
        self.anim.setStartValue(self.value())
        self.anim.setEndValue(target)
        self.anim.start()

    def set_colors(self, colors):
        self.colors = colors
        self.update()

    def set_theme(self, theme):
        self.theme = theme
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        
        # Draw Groove
        groove_rect = self.rect().adjusted(0, 0, 0, 0)
        groove_rect.setHeight(8) # Slightly thinner
        groove_rect.moveCenter(self.rect().center())
        
        gradient = QLinearGradient(groove_rect.topLeft().toPointF(), groove_rect.topRight().toPointF())
        
        if self.colors:
            step = 1.0 / (len(self.colors) - 1) if len(self.colors) > 1 else 1.0
            for i, color in enumerate(self.colors):
                gradient.setColorAt(i * step, color)
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(groove_rect, 4, 4)
        
        # Draw Handle
        # Calculate handle position based on value
        val = self.value()
        mn = self.minimum()
        mx = self.maximum()
        
        if mx > mn:
            ratio = (val - mn) / (mx - mn)
        else:
            ratio = 0
            
        handle_x = int(groove_rect.left() + ratio * (groove_rect.width() - 24))
        handle_rect = QRect(handle_x, 0, 24, 24)
        handle_rect.moveCenter(QPoint(handle_rect.center().x(), self.rect().center().y()))
        
        painter.setBrush(QBrush(QColor("white")))
        painter.setPen(QPen(QColor(self.theme["border"]), 1))
        painter.drawEllipse(handle_rect.center(), 12, 12)

class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True) # Non-blocking
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.timer.start(16) # ~60 FPS
        
        self.hide()

    def rotate(self):
        self.angle = (self.angle + 10) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # YouTube-style centered spinner
        size = 48
        rect = QRect(0, 0, size, size)
        rect.moveCenter(self.rect().center())
        
        pen = QPen(QColor("white"), 4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        painter.drawArc(rect, -self.angle * 16, 270 * 16)

    def show_loading(self):
        self.raise_()
        self.resize(self.parent().size())
        self.show()

    def hide_loading(self):
        self.hide()

class AnimatedButton(QPushButton):
    def __init__(self, text="", parent=None, icon_name=None, color=None, size=None, hover_color_change=True, radius=12, checked_color=None):
        super().__init__(text, parent)
        self.theme = THEME_DARK
        self._color = QColor(self.theme['input'])
        self._hover_color = QColor(self.theme['border'])
        self._text_color = QColor(self.theme['text'])
        self._icon_name = icon_name
        self._hover_color_change = hover_color_change
        self._radius = radius
        self._checked_color = checked_color
        
        self._bg_anim = QPropertyAnimation(self, b"bg_color", self)
        self._bg_anim.setDuration(200)
        self._bg_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        if size:
            self.setFixedSize(*size)
            
        if icon_name:
            self.setIcon(qta.icon(icon_name, color=self.theme['text']))
            if not text:
                self.setIconSize(QSize(24, 24))
                
        if color:
            self._color = QColor(color)
            self._base_color = self._color
            self._hover_color = self._color.lighter(110)

        self.update_style()

    @pyqtProperty(QColor)
    def bg_color(self):
        return self._color

    @bg_color.setter
    def bg_color(self, color):
        self._color = color
        self.update_style()

    def enterEvent(self, event):
        if self._hover_color_change:
            self._bg_anim.setStartValue(self._color)
            self._bg_anim.setEndValue(self._hover_color)
            self._bg_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._hover_color_change:
            self._bg_anim.setStartValue(self._color)
            # If checked, revert to accent color, else input color
            # But wait, if it was initialized with a specific color (like Start Page tiles), we should revert to that.
            # The current implementation overrides it with theme['input'] or theme['accent'].
            # I need to store the "base" color.
            
            target = QColor(self.theme['input'])
            if self.isChecked():
                target = QColor(self._checked_color) if self._checked_color else QColor(self.theme['accent'])
            elif hasattr(self, '_base_color'):
                 target = self._base_color
            
            self._bg_anim.setEndValue(target)
            self._bg_anim.start()
        super().leaveEvent(event)

    def checkStateSet(self):
        super().checkStateSet()
        self.update_color_from_state()

    def nextCheckState(self):
        super().nextCheckState()
        self.update_color_from_state()

    def update_color_from_state(self):
        if self.isChecked():
            self._color = QColor(self._checked_color) if self._checked_color else QColor(self.theme['accent'])
            self._hover_color = self._color.lighter(110)
        else:
            if hasattr(self, '_base_color'):
                self._color = self._base_color
                self._hover_color = self._color.lighter(110)
            else:
                self._color = QColor(self.theme['input'])
                self._hover_color = QColor(self.theme['border'])
        self.update_style()

    def update_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color.name()};
                border-radius: {self._radius}px;
                color: {self._text_color.name()};
                border: none;
                font-weight: 600;
                padding: 10px;
            }}
        """)

    def set_theme(self, theme):
        self.theme = theme
        self._text_color = QColor(theme['text'])
        self.update_color_from_state()
