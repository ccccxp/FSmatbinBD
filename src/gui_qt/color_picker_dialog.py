"""
颜色选择器对话框 - 支持 RGB/HSV/Hex 输入和 Alpha 通道
"""
from typing import Optional, Tuple
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSlider, QSpinBox, QFrame, QGridLayout,
    QWidget, QColorDialog, QDialogButtonBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize, QRect
from PySide6.QtGui import QColor, QPainter, QBrush, QPen, QLinearGradient, QPixmap

from src.core.i18n import _


class ColorPreviewWidget(QWidget):
    """颜色预览控件 - 带棋盘格背景显示透明度"""
    
    clicked = Signal()
    
    def __init__(self, parent=None, size: int = 16):
        super().__init__(parent)
        self._color = QColor(255, 255, 255, 255)
        self._size = size
        self.setMinimumSize(size, size)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        self.setCursor(Qt.PointingHandCursor)
    
    def set_color(self, color: QColor):
        self._color = color
        self.update()
    
    def get_color(self) -> QColor:
        return self._color
    
    def set_rgba(self, r: float, g: float, b: float, a: float = 1.0):
        """设置颜色，值范围 0-1"""
        self._color = QColor.fromRgbF(
            max(0, min(1, r)),
            max(0, min(1, g)),
            max(0, min(1, b)),
            max(0, min(1, a))
        )
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 计算居中的正方形区域
        side = min(self.width(), self.height())
        x_offset = (self.width() - side) // 2
        y_offset = (self.height() - side) // 2
        draw_rect = QRect(x_offset, y_offset, side, side)
        
        # 绘制棋盘格背景（表示透明度）
        self._draw_checkerboard(painter, draw_rect)
        
        # 绘制颜色
        painter.fillRect(draw_rect, self._color)
        
        # 绘制边框
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawRect(draw_rect.adjusted(0, 0, -1, -1))
    
    def _draw_checkerboard(self, painter: QPainter, rect: QRect):
        """绘制棋盘格背景"""
        cell_size = 4
        light = QColor(255, 255, 255)
        dark = QColor(180, 180, 180)
        
        # 在指定矩形内绘制
        painter.setClipRect(rect)
        for y in range(rect.top(), rect.bottom() + 1, cell_size):
            for x in range(rect.left(), rect.right() + 1, cell_size):
                # 基于相对位置计算棋盘格颜色
                rel_x = x - rect.left()
                rel_y = y - rect.top()
                is_light = ((rel_x // cell_size) + (rel_y // cell_size)) % 2 == 0
                painter.fillRect(x, y, cell_size, cell_size, light if is_light else dark)
        painter.setClipping(False)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()


class GradientPreviewWidget(QWidget):
    """透明度渐变预览控件 - 用于Int2 XY方向渐变"""
    
    clicked = Signal()
    
    def __init__(self, parent=None, size: int = 24):
        super().__init__(parent)
        self._size = size
        self._x = 0  # 渐变方向 X
        self._y = 0  # 渐变方向 Y
        self.setMinimumSize(size, size)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        self.setCursor(Qt.PointingHandCursor)
    
    def set_direction(self, x: int, y: int):
        self._x = x
        self._y = y
        self.update()
    
    def get_direction(self) -> Tuple[int, int]:
        return (self._x, self._y)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 计算居中的正方形区域
        side = min(self.width(), self.height())
        x_offset = (self.width() - side) // 2
        y_offset = (self.height() - side) // 2
        draw_rect = QRect(x_offset, y_offset, side, side)
        
        # 绘制棋盘格背景
        self._draw_checkerboard(painter, draw_rect)
        
        # 根据XY方向绘制渐变透明层
        self._draw_gradient(painter, draw_rect)
        
        # 绘制边框
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawRect(draw_rect.adjusted(0, 0, -1, -1))
    
    def _draw_checkerboard(self, painter: QPainter, rect: QRect):
        cell_size = max(4, rect.width() // 6)
        light = QColor(255, 255, 255)
        dark = QColor(180, 180, 180)
        
        painter.setClipRect(rect)
        for y in range(rect.top(), rect.bottom() + 1, cell_size):
            for x in range(rect.left(), rect.right() + 1, cell_size):
                rel_x = x - rect.left()
                rel_y = y - rect.top()
                is_light = ((rel_x // cell_size) + (rel_y // cell_size)) % 2 == 0
                painter.fillRect(x, y, cell_size, cell_size, light if is_light else dark)
        painter.setClipping(False)
    
    def _draw_gradient(self, painter: QPainter, rect: QRect):
        """根据XY向量绘制透明度渐变
        
        XY为正值坐标系（第一象限），表示透明度强度：
        - (0,0) = 完全不透明
        - XY值越大 = 越透明
        """
        # (0,0) 时完全不透明
        if self._x == 0 and self._y == 0:
            painter.fillRect(rect, QColor(0, 0, 0, 255))
            return
        
        # 计算透明度强度（基于XY的模长）
        max_val = 200
        magnitude = (self._x ** 2 + self._y ** 2) ** 0.5
        alpha_ratio = min(1.0, magnitude / max_val)
        
        # 使用简单的对角线渐变：从左下(不透明)到右上(透明)
        gradient = QLinearGradient(rect.bottomLeft(), rect.topRight())
        gradient.setColorAt(0, QColor(0, 0, 0, 255))
        end_alpha = int(255 * (1 - alpha_ratio))
        gradient.setColorAt(1, QColor(0, 0, 0, end_alpha))
        
        painter.fillRect(rect, gradient)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()


class GradientEditorDialog(QDialog):
    """透明度渐变方向编辑器对话框"""
    
    directionChanged = Signal(int, int)
    
    def __init__(self, parent=None, initial_x: int = 0, initial_y: int = 0):
        super().__init__(parent)
        self.setWindowTitle(_("gradient_editor_title"))
        self.setMinimumSize(280, 320)
        
        self._x = initial_x
        self._y = initial_y
        
        self._build_ui()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # 大预览区域（带方向控制线）
        self._preview_canvas = _DirectionCanvas(self)
        self._preview_canvas.setFixedSize(200, 200)
        self._preview_canvas.set_direction(self._x, self._y)
        self._preview_canvas.directionChanged.connect(self._on_canvas_changed)
        
        preview_row = QHBoxLayout()
        preview_row.addStretch()
        preview_row.addWidget(self._preview_canvas)
        preview_row.addStretch()
        layout.addLayout(preview_row)
        
        # XY输入
        xy_row = QHBoxLayout()
        xy_row.addWidget(QLabel("X:"))
        self._x_spin = QSpinBox()
        self._x_spin.setRange(-1000, 1000)
        self._x_spin.setValue(self._x)
        self._x_spin.valueChanged.connect(self._on_spin_changed)
        xy_row.addWidget(self._x_spin)
        
        xy_row.addSpacing(20)
        
        xy_row.addWidget(QLabel("Y:"))
        self._y_spin = QSpinBox()
        self._y_spin.setRange(-1000, 1000)
        self._y_spin.setValue(self._y)
        self._y_spin.valueChanged.connect(self._on_spin_changed)
        xy_row.addWidget(self._y_spin)
        
        layout.addLayout(xy_row)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _on_canvas_changed(self, x: int, y: int):
        self._x = x
        self._y = y
        self._x_spin.blockSignals(True)
        self._y_spin.blockSignals(True)
        self._x_spin.setValue(x)
        self._y_spin.setValue(y)
        self._x_spin.blockSignals(False)
        self._y_spin.blockSignals(False)
        self.directionChanged.emit(x, y)
    
    def _on_spin_changed(self):
        self._x = self._x_spin.value()
        self._y = self._y_spin.value()
        self._preview_canvas.set_direction(self._x, self._y)
        self.directionChanged.emit(self._x, self._y)
    
    def get_direction(self) -> Tuple[int, int]:
        return (self._x, self._y)


class _DirectionCanvas(QWidget):
    """方向控制画布 - 可拖动控制线"""
    
    directionChanged = Signal(int, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._x = 0
        self._y = 0
        self._dragging = False
        self.setCursor(Qt.CrossCursor)
    
    def set_direction(self, x: int, y: int):
        self._x = x
        self._y = y
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w, h = self.width(), self.height()
        
        # 绘制棋盘格背景
        cell_size = 10
        light = QColor(255, 255, 255)
        dark = QColor(200, 200, 200)
        for yy in range(0, h, cell_size):
            for xx in range(0, w, cell_size):
                is_light = ((xx // cell_size) + (yy // cell_size)) % 2 == 0
                painter.fillRect(xx, yy, cell_size, cell_size, light if is_light else dark)
        
        # 绘制渐变预览（从左下角向右上角）
        if self._x != 0 or self._y != 0:
            max_val = 200
            magnitude = (self._x ** 2 + self._y ** 2) ** 0.5
            alpha_ratio = min(1.0, magnitude / max_val)
            
            # 简单对角线渐变：从左下(不透明)到右上(透明)
            gradient = QLinearGradient(0, h, w, 0)
            gradient.setColorAt(0, QColor(0, 0, 0, 255))
            end_alpha = int(255 * (1 - alpha_ratio))
            gradient.setColorAt(1, QColor(0, 0, 0, end_alpha))
            painter.fillRect(self.rect(), gradient)
        else:
            # (0,0) = 完全不透明
            painter.fillRect(self.rect(), QColor(0, 0, 0, 255))
        
        # 绘制边框
        painter.setPen(QPen(QColor(80, 80, 80), 2))
        painter.drawRect(1, 1, w - 2, h - 2)
        
        # 绘制坐标轴（原点在左下角）
        painter.setPen(QPen(QColor(100, 100, 100, 200), 1))
        # X轴
        painter.drawLine(0, h, w, h)
        # Y轴
        painter.drawLine(0, 0, 0, h)
        
        # 绘制方向控制线（从原点出发）
        # 原点在左下角 (0, h)
        max_val = 200
        end_x = int(self._x * w / max_val)
        end_y = int(h - self._y * h / max_val)
        end_x = max(0, min(w, end_x))
        end_y = max(0, min(h, end_y))
        
        painter.setPen(QPen(QColor(88, 166, 255), 3))
        painter.drawLine(0, h, end_x, end_y)
        
        # 绘制控制点
        painter.setBrush(QColor(88, 166, 255))
        painter.drawEllipse(end_x - 6, end_y - 6, 12, 12)
        
        # 绘制当前值标签
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(5, 15, f"X: {self._x}  Y: {self._y}")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._update_from_pos(event.position().toPoint())
    
    def mouseMoveEvent(self, event):
        if self._dragging:
            self._update_from_pos(event.position().toPoint())
    
    def mouseReleaseEvent(self, event):
        self._dragging = False
    
    def _update_from_pos(self, pos):
        w, h = self.width(), self.height()
        
        # 原点在左下角，只允许正值（第一象限）
        max_val = 200
        self._x = max(0, int(pos.x() * max_val / w))
        self._y = max(0, int((h - pos.y()) * max_val / h))
        
        self.update()
        self.directionChanged.emit(self._x, self._y)


class ColorPickerDialog(QDialog):
    """颜色选择器对话框"""
    
    colorChanged = Signal(QColor)
    
    def __init__(self, parent=None, initial_color: QColor = None, show_alpha: bool = True):
        super().__init__(parent)
        self.setWindowTitle(_("color_picker_title") if hasattr(_, '__call__') else "颜色选择器")
        self.setMinimumSize(320, 280)
        
        self._color = initial_color or QColor(255, 255, 255, 255)
        self._show_alpha = show_alpha
        self._updating = False
        
        self._build_ui()
        self._update_all_from_color()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # 预览区域
        preview_row = QHBoxLayout()
        preview_row.addStretch()
        
        preview_label = QLabel(_("color_preview_label"))
        preview_row.addWidget(preview_label)
        
        self._preview = ColorPreviewWidget(size=48)
        self._preview.setFixedSize(48, 48)
        preview_row.addWidget(self._preview)
        
        # Qt内置取色按钮
        self._pick_btn = QPushButton(_("use_system_picker"))
        self._pick_btn.clicked.connect(self._open_system_picker)
        preview_row.addWidget(self._pick_btn)
        
        preview_row.addStretch()
        layout.addLayout(preview_row)
        
        # RGB输入
        rgb_group = QFrame()
        rgb_layout = QGridLayout(rgb_group)
        rgb_layout.setContentsMargins(0, 0, 0, 0)
        rgb_layout.setSpacing(8)
        
        self._r_spin = self._create_spin_row(rgb_layout, 0, "R:", 0, 255)
        self._g_spin = self._create_spin_row(rgb_layout, 1, "G:", 0, 255)
        self._b_spin = self._create_spin_row(rgb_layout, 2, "B:", 0, 255)
        
        if self._show_alpha:
            self._a_spin = self._create_spin_row(rgb_layout, 3, "A:", 0, 255)
        else:
            self._a_spin = None
        
        layout.addWidget(rgb_group)
        
        # Hex输入
        hex_row = QHBoxLayout()
        hex_label = QLabel("Hex:")
        hex_label.setFixedWidth(30)
        hex_row.addWidget(hex_label)
        
        self._hex_edit = QLineEdit()
        self._hex_edit.setPlaceholderText("#RRGGBB" + ("AA" if self._show_alpha else ""))
        self._hex_edit.textEdited.connect(self._on_hex_changed)
        hex_row.addWidget(self._hex_edit)
        
        layout.addLayout(hex_row)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _create_spin_row(self, layout: QGridLayout, row: int, label: str, 
                         min_val: int, max_val: int) -> QSpinBox:
        lbl = QLabel(label)
        lbl.setFixedWidth(30)
        layout.addWidget(lbl, row, 0)
        
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.valueChanged.connect(self._on_rgb_changed)
        layout.addWidget(spin, row, 1)
        
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.valueChanged.connect(spin.setValue)
        spin.valueChanged.connect(slider.setValue)
        layout.addWidget(slider, row, 2)
        
        return spin
    
    def _on_rgb_changed(self):
        if self._updating:
            return
        self._updating = True
        
        r = self._r_spin.value()
        g = self._g_spin.value()
        b = self._b_spin.value()
        a = self._a_spin.value() if self._a_spin else 255
        
        self._color = QColor(r, g, b, a)
        self._update_preview()
        self._update_hex()
        self.colorChanged.emit(self._color)
        
        self._updating = False
    
    def _on_hex_changed(self, text: str):
        if self._updating:
            return
        
        hex_str = text.strip()
        if not hex_str.startswith('#'):
            hex_str = '#' + hex_str
        
        color = QColor(hex_str)
        if color.isValid():
            self._updating = True
            self._color = color
            self._update_rgb_spins()
            self._update_preview()
            self.colorChanged.emit(self._color)
            self._updating = False
    
    def _open_system_picker(self):
        """打开系统取色器"""
        options = QColorDialog.ShowAlphaChannel if self._show_alpha else QColorDialog.ColorDialogOptions()
        color = QColorDialog.getColor(self._color, self, "选择颜色", options)
        if color.isValid():
            self._color = color
            self._update_all_from_color()
            self.colorChanged.emit(self._color)
    
    def _update_all_from_color(self):
        self._updating = True
        self._update_rgb_spins()
        self._update_hex()
        self._update_preview()
        self._updating = False
    
    def _update_rgb_spins(self):
        self._r_spin.setValue(self._color.red())
        self._g_spin.setValue(self._color.green())
        self._b_spin.setValue(self._color.blue())
        if self._a_spin:
            self._a_spin.setValue(self._color.alpha())
    
    def _update_hex(self):
        if self._show_alpha:
            hex_str = self._color.name(QColor.HexArgb)
        else:
            hex_str = self._color.name(QColor.HexRgb)
        self._hex_edit.setText(hex_str)
    
    def _update_preview(self):
        self._preview.set_color(self._color)
    
    def get_color(self) -> QColor:
        return self._color
    
    def get_rgba_floats(self) -> Tuple[float, float, float, float]:
        """返回0-1范围的RGBA值"""
        return (
            self._color.redF(),
            self._color.greenF(),
            self._color.blueF(),
            self._color.alphaF()
        )
