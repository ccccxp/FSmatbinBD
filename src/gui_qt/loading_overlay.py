"""
加载遮罩组件 - 显示在内容上方的半透明加载动画
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QPainter, QColor, QFont, QPen
from src.core.i18n import _


class LoadingOverlay(QWidget):
    """半透明加载遮罩，带旋转动画"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setWindowFlags(Qt.FramelessWindowHint)
        
        self._angle = 0
        self._text = _('loading')
        
        # 旋转动画定时器
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.setInterval(30)  # ~33fps
        
        self.hide()
    
    def _get_angle(self):
        return self._angle
    
    def _set_angle(self, value):
        self._angle = value
        self.update()
    
    angle = Property(int, _get_angle, _set_angle)
    
    def _rotate(self):
        self._angle = (self._angle + 10) % 360
        self.update()
    
    def showEvent(self, event):
        super().showEvent(event)
        # 确保覆盖整个父组件
        if self.parent():
            self.setGeometry(self.parent().rect())
        self._timer.start()
    
    def hideEvent(self, event):
        super().hideEvent(event)
        self._timer.stop()
    
    def set_text(self, text: str):
        self._text = text
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 半透明黑色背景
        painter.fillRect(self.rect(), QColor(0, 0, 0, 160))
        
        # 绘制旋转的加载圈
        center = self.rect().center()
        radius = 30
        
        painter.translate(center)
        painter.rotate(self._angle)
        
        # 绘制渐变弧线
        pen = QPen(QColor(88, 166, 255, 255))
        pen.setWidth(4)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        
        from PySide6.QtCore import QRectF
        arc_rect = QRectF(-radius, -radius, radius * 2, radius * 2)
        painter.drawArc(arc_rect, 0, 270 * 16)  # 270度弧
        
        # 恢复变换绘制文字
        painter.resetTransform()
        
        # 绘制文字
        painter.setPen(QColor(255, 255, 255, 220))
        font = QFont()
        font.setPointSize(11)
        painter.setFont(font)
        
        text_rect = self.rect()
        text_rect.setTop(center.y() + radius + 20)
        painter.drawText(text_rect, Qt.AlignHCenter | Qt.AlignTop, self._text)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 确保覆盖整个父组件
        if self.parent():
            self.setGeometry(self.parent().rect())
