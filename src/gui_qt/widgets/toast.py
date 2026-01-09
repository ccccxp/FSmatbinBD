from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import QEasingCurve, QObject, QPoint, QPropertyAnimation, QTimer, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QFrame, QGraphicsDropShadowEffect, QLabel, QWidget


@dataclass(frozen=True)
class ToastStyle:
    background: str = "rgba(20, 26, 40, 220)"
    border: str = "rgba(90, 110, 140, 160)"
    text: str = "rgba(245, 247, 255, 235)"
    radius: int = 10
    padding_h: int = 12
    padding_v: int = 10


class Toast(QFrame):
    """轻量 Toast：淡入/停留/淡出，默认右下角堆叠显示。"""

    def __init__(
        self,
        parent: QWidget,
        text: str,
        *,
        duration_ms: int = 2600,
        style: ToastStyle = ToastStyle(),
        max_width: int = 520,
    ):
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self._duration_ms = max(300, duration_ms)
        self._style = style

        self._label = QLabel(text)
        self._label.setWordWrap(True)
        self._label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._label.setMaximumWidth(max_width)

        # QSS
        self.setStyleSheet(
            f"""
            QFrame#Toast {{
                background: {style.background};
                border: 1px solid {style.border};
                border-radius: {style.radius}px;
            }}
            QFrame#Toast QLabel {{
                background: transparent;
                color: {style.text};
            }}
            """
        )

        from PySide6.QtWidgets import QHBoxLayout

        lay = QHBoxLayout(self)
        lay.setContentsMargins(style.padding_h, style.padding_v, style.padding_h, style.padding_v)
        lay.addWidget(self._label)

        # shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 180))
        self.setGraphicsEffect(shadow)

        self._anim_in = QPropertyAnimation(self, b"windowOpacity", self)
        self._anim_in.setDuration(140)
        self._anim_in.setStartValue(0.0)
        self._anim_in.setEndValue(1.0)
        self._anim_in.setEasingCurve(QEasingCurve.OutCubic)

        self._anim_out = QPropertyAnimation(self, b"windowOpacity", self)
        self._anim_out.setDuration(160)
        self._anim_out.setStartValue(1.0)
        self._anim_out.setEndValue(0.0)
        self._anim_out.setEasingCurve(QEasingCurve.InCubic)
        self._anim_out.finished.connect(self.deleteLater)

        # start hidden (opacity 0)
        self.setWindowOpacity(0.0)

        # auto close timer
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.close_with_fade)

    def showEvent(self, event):  # type: ignore[override]
        super().showEvent(event)
        self._anim_in.stop()
        self._anim_in.start()
        self._timer.start(self._duration_ms)

    def close_with_fade(self):
        self._timer.stop()
        self._anim_out.stop()
        self._anim_out.start()


class ToastManager(QObject):
    """管理全局 Toast 堆叠。"""

    def __init__(self, parent_window: QWidget):
        super().__init__(parent_window)
        self._parent_window = parent_window
        self._toasts: list[Toast] = []
        self._margin = QPoint(16, 16)
        self._gap = 10

        parent_window.installEventFilter(self)

    def eventFilter(self, obj: QObject, event) -> bool:  # type: ignore[override]
        # 父窗口移动/缩放时重新布局
        if obj is self._parent_window and event.type() in (event.Move, event.Resize):
            self._relayout()
        return super().eventFilter(obj, event)

    def show(self, text: str, *, duration_ms: int = 2600):
        toast = Toast(self._parent_window, text, duration_ms=duration_ms)
        toast.destroyed.connect(lambda *_: self._on_toast_destroyed(toast))
        self._toasts.append(toast)
        toast.adjustSize()
        self._relayout()
        toast.show()

    def _on_toast_destroyed(self, toast: Toast):
        try:
            self._toasts.remove(toast)
        except ValueError:
            pass
        self._relayout()

    def _relayout(self):
        # 清理已隐藏/待删除
        self._toasts = [t for t in self._toasts if t is not None and not t.isHidden()]

        parent = self._parent_window
        if not parent.isVisible():
            return

        pr = parent.rect()
        x = pr.right() - self._margin.x()
        y = pr.bottom() - self._margin.y()

        # 从底向上堆叠
        for t in reversed(self._toasts):
            t.adjustSize()
            size = t.sizeHint()
            x0 = x - size.width()
            y0 = y - size.height()
            t.move(x0, y0)
            y = y0 - self._gap


_toast_manager: Optional[ToastManager] = None


def get_toast_manager(window: QWidget) -> ToastManager:
    global _toast_manager
    if _toast_manager is None or _toast_manager.parent() is not window:
        _toast_manager = ToastManager(window)
    return _toast_manager


def toast(window: QWidget, text: str, *, duration_ms: int = 2600):
    """便捷函数：toast(mainWindow, '保存成功')"""
    get_toast_manager(window).show(text, duration_ms=duration_ms)
