from PyQt6.QtWidgets import QStackedWidget, QLabel
from PyQt6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QAbstractAnimation
from PyQt6.QtGui import QPixmap, QPainter, QColor
import logging
from ..theme import THEME_DARK

class SlidingStackedWidget(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.m_direction = Qt.Orientation.Horizontal
        self.m_speed = 300 # Faster, smoother
        self.m_animationtype = QEasingCurve.Type.OutCubic # Apple-like ease
        self.m_now = 0
        self.m_next = 0
        self.m_wrap = False
        self.m_active = False
        self.m_labels = []

    def setDirection(self, direction):
        self.m_direction = direction

    def setSpeed(self, speed):
        self.m_speed = speed

    def setAnimation(self, animationtype):
        self.m_animationtype = animationtype

    def setWrap(self, wrap):
        self.m_wrap = wrap

    def slideInPrev(self):
        now = self.currentIndex()
        if self.m_wrap or now > 0:
            self.slideInIdx(now - 1)

    def slideInNext(self):
        now = self.currentIndex()
        if self.m_wrap or now < (self.count() - 1):
            self.slideInIdx(now + 1)

    def slideInIdx(self, idx):
        if idx > (self.count() - 1):
            idx = idx % self.count()
        elif idx < 0:
            idx = (idx + self.count()) % self.count()

        self.slideInWgt(self.widget(idx))

    def slideInWgt(self, newwidget):
        if self.m_active:
            return

        try:
            self.m_active = True
            _now = self.currentIndex()
            _next = self.indexOf(newwidget)

            if _now == _next:
                self.m_active = False
                return

            # Dimensions
            w = self.frameRect().width()
            h = self.frameRect().height()
            
            # Use Theme Background Color
            bg_color = QColor(THEME_DARK['bg'])
            self.setStyleSheet(f"background-color: {bg_color.name()};")
            
            # Prepare Direction
            offsetx, offsety = 0, 0
            if self.m_direction == Qt.Orientation.Horizontal:
                if _now < _next:
                    offsetx = -w
                else:
                    offsetx = w
            else:
                if _now < _next:
                    offsety = -h
                else:
                    offsety = h

            # Snapshot Current
            current_widget = self.currentWidget()
            pix_curr = QPixmap(self.size())
            pix_curr.fill(bg_color) 
            current_widget.render(pix_curr)
            
            lbl_curr = QLabel(self)
            lbl_curr.setPixmap(pix_curr)
            lbl_curr.setGeometry(0, 0, w, h)
            lbl_curr.raise_()
            lbl_curr.show()

            # Snapshot Next
            # Ensure it is sized correctly
            newwidget.resize(self.size())
            
            # Hook: Prepare visuals (e.g. reset animations to 0) before snapshot
            if hasattr(newwidget, 'prepare_visuals'):
                newwidget.prepare_visuals()
            
            # Force layout update if needed (optional)
            
            pix_next = QPixmap(self.size())
            pix_next.fill(bg_color)
            newwidget.render(pix_next)
            
            lbl_next = QLabel(self)
            lbl_next.setPixmap(pix_next)
            # Start position
            lbl_next.setGeometry(-offsetx, -offsety, w, h)
            lbl_next.raise_()
            lbl_next.show()
            
            # Switch actual stack immediately (hidden behind labels)
            # This ensures state is updated
            # But we must ensure it doesn't paint over our labels
            # Actually, standard QStackedWidget paints current widget.
            # We want to hide the "real" widgets during animation ideally.
            # But render() works on them.
            
            # Let's keep current shown? No, that causes flash.
            # We'll just rely on labels covering everything.
            
            # Create Animation Group
            self.anim_group = QParallelAnimationGroup(self)
            
            # Animate Current Out
            anim_curr = QPropertyAnimation(lbl_curr, b"pos")
            anim_curr.setDuration(self.m_speed)
            anim_curr.setEasingCurve(self.m_animationtype)
            anim_curr.setStartValue(QPoint(0, 0))
            anim_curr.setEndValue(QPoint(offsetx, offsety))
            self.anim_group.addAnimation(anim_curr)
            
            # Animate Next In
            anim_next = QPropertyAnimation(lbl_next, b"pos")
            anim_next.setDuration(self.m_speed)
            anim_next.setEasingCurve(self.m_animationtype)
            anim_next.setStartValue(QPoint(-offsetx, -offsety))
            anim_next.setEndValue(QPoint(0, 0))
            self.anim_group.addAnimation(anim_next)
            
            self.m_next = _next
            self.m_labels = [lbl_curr, lbl_next]
            
            self.anim_group.finished.connect(self.animationDone)
            self.anim_group.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
            
        except Exception as e:
            logging.error(f"Animation error: {e}")
            self.m_active = False
            self.cleanup_labels()
            self.setCurrentIndex(self.indexOf(newwidget))

    def animationDone(self):
        self.setCurrentIndex(self.m_next)
        self.cleanup_labels()
        self.m_active = False
        
    def cleanup_labels(self):
        for lbl in self.m_labels:
            lbl.hide()
            lbl.deleteLater()
        self.m_labels = []
