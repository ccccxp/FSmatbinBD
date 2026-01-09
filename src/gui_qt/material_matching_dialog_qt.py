from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, QObject, Signal, QSettings, QTimer, QRect, QSize, QPoint
from PySide6.QtGui import QClipboard, QDrag, QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import QMimeData
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSlider,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QFileDialog,
    QSizePolicy,
    QProxyStyle,
    QStyle,
    QLayout,
    QLayoutItem,
    QWidgetItem,
    QFrame,
    QScrollArea,
)
from .smooth_scroll import SmoothTableWidget
from src.utils.resource_path import get_assets_path



class _OpLabel(QLabel):
    """固定宽度的运算符显示（可点击循环切换 >/=）。"""

    def __init__(self, owner, index: int):
        super().__init__("")
        self._owner = owner
        self._index = index
        self.setFixedWidth(18)
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            """
            QLabel {
                color: rgba(255,255,255,0.78);
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 6px;
                padding: 0px;
            }
            QLabel:hover {
                color: rgba(255,255,255,0.92);
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.16);
            }
            """
        )

    def set_op(self, op: Optional[str]):
        self.setText(op if op in (">", "=") else "")

    def mousePressEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            event.accept()
            self._owner._toggle_relation_at_index(self._index)
            return
        super().mousePressEvent(event)


class _PriorityComboRow(QWidget):
    """横向下拉框排序：每个位置一个 ComboBox，选择后自动互换。"""

    def __init__(self, owner):
        super().__init__()
        self._owner = owner
        self._updating = False

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self._lay = lay
        self._combos: List[QComboBox] = []
        self._ops: List[_OpLabel] = []
        self.setMinimumHeight(32)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_items(self, items: List[Dict[str, Any]]):
        if self._updating:
            return
        self._updating = True

        while self._lay.count():
            it = self._lay.takeAt(0)
            if it and it.widget():
                it.widget().deleteLater()
        self._combos.clear()
        self._ops.clear()

        all_keys = [str(it.get("key")) for it in items]
        all_labels = [self._owner._priority_key_to_label(k) for k in all_keys]
        
        # 加载 SVG 图标（使用资源路径辅助模块）
        icon_path = get_assets_path("chevron_down.svg")
        chevron_icon = QIcon(icon_path)

        for idx, it in enumerate(items):
            is_last = idx == len(items) - 1
            current_key = str(it.get("key"))
            rel = it.get("relation") if not is_last else None

            combo = QComboBox()
            combo.setFixedHeight(26)
            combo.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            combo.setCursor(Qt.PointingHandCursor)

            # 添加选项（不再使用 Unicode 箭头）
            for i, label in enumerate(all_labels):
                combo.addItem(label, all_keys[i])

            current_idx = all_keys.index(current_key) if current_key in all_keys else 0
            combo.setCurrentIndex(current_idx)
            
            # 使用Qt的自适应内容策略
            combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
            
            combo.currentIndexChanged.connect(lambda new_idx, pos=idx: self._on_combo_changed(pos, new_idx))

            combo.setStyleSheet(
                f"""
                QComboBox {{
                    background: rgba(255,255,255,0.05);
                    border: 1px solid rgba(255,255,255,0.12);
                    border-radius: 13px;
                    padding: 3px 18px 3px 10px;
                    color: rgba(255,255,255,0.92);
                    font-size: 13px;
                }}
                QComboBox:hover {{
                    background: rgba(255,255,255,0.08);
                    border: 1px solid rgba(255,255,255,0.20);
                }}
                QComboBox::drop-down {{
                    subcontrol-origin: padding;
                    subcontrol-position: center right;
                    width: 14px;
                    border: none;
                }}
                QComboBox::down-arrow {{
                    image: url({icon_path.replace(chr(92), '/')});
                    width: 10px;
                    height: 10px;
                }}
                QComboBox QAbstractItemView {{
                    background: #2d2d30;
                    border: 1px solid rgba(255,255,255,0.15);
                    border-radius: 4px;
                    selection-background-color: rgba(88,166,255,0.3);
                    color: rgba(255,255,255,0.92);
                    padding: 4px;
                    outline: none;
                }}
                QComboBox QAbstractItemView::item {{
                    min-height: 24px;
                    padding: 2px 8px;
                }}
                QComboBox QAbstractItemView::item:selected {{
                    background: rgba(88,166,255,0.25);
                }}
                """
            )

            self._lay.addWidget(combo)
            self._combos.append(combo)

            if not is_last:
                op = _OpLabel(self._owner, idx)
                op.set_op(rel)
                self._lay.addWidget(op)
                self._ops.append(op)

        self._lay.addStretch(1)
        self._updating = False

    def _on_combo_changed(self, position: int, new_combo_index: int):
        if self._updating:
            return
        combo = self._combos[position]
        new_key = combo.itemData(new_combo_index)
        if not new_key:
            return
        self._owner._swap_priority_at(position, new_key)


class _PriorityPillRow(QWidget):
    """单行优先级：Pill 与运算符分离，运算符固定列位。"""

    def __init__(self, owner):
        super().__init__()
        self._owner = owner
        self.setAcceptDrops(True)
        self._drag_key: Optional[str] = None
        self._drop_index: int = -1
        self._hover_key: Optional[str] = None

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        self._lay = lay

        self._placeholder = QFrame()
        self._placeholder.setFixedSize(140, 26)
        self._placeholder.setStyleSheet(
            """
            QFrame {
                border: 1px dashed rgba(88, 166, 255, 0.55);
                border-radius: 14px;
                background: rgba(88, 166, 255, 0.10);
            }
            """
        )
        self._placeholder.hide()

        self.setMinimumHeight(34)
        self.setMaximumHeight(40)
        # 单行横向滚动：让自身尽量只占一行宽度（高度固定）
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

    def clear(self):
        while self._lay.count():
            it = self._lay.takeAt(0)
            if it is None:
                break
            w = it.widget()
            # placeholder 不能 deleteLater，否则拖拽事件还在用它会触发
            # RuntimeError: Internal C++ object already deleted
            if w is self._placeholder:
                try:
                    w.hide()
                except Exception:
                    pass
                # 不删除，直接跳过
                continue
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def set_items(self, items: List[Dict[str, Any]]):
        self.clear()
        # 确保 placeholder 仍然有效且处于隐藏状态
        try:
            self._placeholder.setParent(self)
            self._placeholder.hide()
        except Exception:
            pass
        for idx, it in enumerate(items):
            is_last = idx == len(items) - 1
            key = str(it.get("key"))
            label = self._owner._priority_key_to_label(key)
            rel = it.get("relation") if not is_last else None

            pill = _PriorityChipWidget(label=label, relation=None, is_last=True, key=key, owner=self)  # 关系不在 pill 内
            pill.setMinimumHeight(26)
            pill.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            # 默认/悬停态样式（更像“胶囊卡片”）
            if self._hover_key and key == self._hover_key:
                pill.setStyleSheet(
                    """
                    QWidget {
                        background: rgba(88,166,255,0.22);
                        border: 1px solid rgba(88,166,255,0.70);
                        border-radius: 14px;
                    }
                    """
                )
            else:
                pill.setStyleSheet(
                    """
                    QWidget {
                        background: rgba(255,255,255,0.05);
                        border: 1px solid rgba(255,255,255,0.12);
                        border-radius: 14px;
                    }
                    QWidget:hover {
                        background: rgba(255,255,255,0.08);
                        border: 1px solid rgba(255,255,255,0.18);
                    }
                    """
                )
            self._lay.addWidget(pill)

            if not is_last:
                op = _OpLabel(self._owner, left_key=key)
                op.set_op(rel)
                self._lay.addWidget(op)

        self._lay.addStretch(1)

    # 被 pill 调用
    def start_drag(self, chip: _PriorityChipWidget):
        key = chip.key()
        self._drag_key = key
        drag = QDrag(chip)
        mime = QMimeData()
        mime.setText(key)
        drag.setMimeData(mime)
        try:
            drag.exec(Qt.MoveAction)
        finally:
            # 拖拽结束：清理状态 + 占位
            self._drag_key = None
            try:
                self._placeholder.hide()
            except Exception:
                pass

    def toggle_relation_for_key(self, key: str):
        # row 内不切换，交给 OpLabel
        return

    def dragEnterEvent(self, event):  # type: ignore[override]
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):  # type: ignore[override]
        if not event.mimeData().hasText():
            return event.ignore()
        event.acceptProposedAction()
        # 目标高亮：鼠标落在哪个 pill 上
        pos = event.position().toPoint()

        # 靠近左右边缘自动滚动（提升长列表拖拽体验）
        try:
            scroll = getattr(self._owner, "priority_scroll", None)
            if scroll is not None and hasattr(scroll, "horizontalScrollBar"):
                sb = scroll.horizontalScrollBar()
                margin = 28
                step = 18
                if pos.x() < margin:
                    sb.setValue(sb.value() - step)
                elif pos.x() > self.width() - margin:
                    sb.setValue(sb.value() + step)
        except Exception:
            pass
        hover_key: Optional[str] = None
        for p in self._pill_widgets():
            if p.geometry().contains(pos):
                try:
                    hover_key = p.key()
                except Exception:
                    hover_key = None
                break
        if hover_key != self._hover_key:
            # 直接更新 pill 样式，不要重建整个列表（否则会打断拖拽导致卡死）
            old_key = self._hover_key
            self._hover_key = hover_key
            self._update_pill_highlight(old_key, hover_key)
        self._drop_index = self._calc_insert_index(pos)
        self._show_placeholder(self._drop_index)

    def dropEvent(self, event):  # type: ignore[override]
        if not event.mimeData().hasText():
            return event.ignore()
        key = event.mimeData().text()
        idx = self._drop_index if self._drop_index >= 0 else self._calc_insert_index(event.position().toPoint())
        self._placeholder.hide()
        # 统一约定：这里传入“移除前的插入点”(idx)，由 owner 负责做一次性补偿。
        self._owner._move_priority_key(key, idx)
        event.acceptProposedAction()

    def leaveEvent(self, event):  # type: ignore[override]
        self._placeholder.hide()
        if self._hover_key is not None:
            old_key = self._hover_key
            self._hover_key = None
            self._update_pill_highlight(old_key, None)
        return super().leaveEvent(event)

    def _update_pill_highlight(self, old_key: Optional[str], new_key: Optional[str]):
        """直接更新 pill 样式，避免重建整个列表导致拖拽卡死"""
        normal_style = """
            QWidget {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 14px;
            }
            QWidget:hover {
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.18);
            }
        """
        highlight_style = """
            QWidget {
                background: rgba(88,166,255,0.22);
                border: 1px solid rgba(88,166,255,0.70);
                border-radius: 14px;
            }
        """
        for i in range(self._lay.count()):
            w = self._lay.itemAt(i).widget()
            if isinstance(w, _PriorityChipWidget):
                try:
                    k = w.key()
                    if k == old_key:
                        w.setStyleSheet(normal_style)
                    elif k == new_key:
                        w.setStyleSheet(highlight_style)
                except Exception:
                    pass

    def _pill_widgets(self) -> List[_PriorityChipWidget]:
        pills: List[_PriorityChipWidget] = []
        for i in range(self._lay.count()):
            w = self._lay.itemAt(i).widget()
            if isinstance(w, _PriorityChipWidget):
                # placeholder 不是 pill；另外拖拽中的 pill 不参与插入点计算，避免抖动
                if self._drag_key and w.key() == self._drag_key:
                    continue
                pills.append(w)
        return pills

    def _calc_insert_index(self, pos: QPoint) -> int:
        # UX 目标：拖到“某个目标优先级胶囊上”就应该触发位置调整（互换/前插），
        # 而不是必须拖到目标胶囊的后面才生效。
        #
        # 规则：
        # 1) 若鼠标落在某个 pill 的矩形范围内（不含拖拽自身），插入点 = 该 pill 的 index（即放到它前面）。
        # 2) 若鼠标在 pill 之间/运算符区域，退化为“中心点 x 分界”的稳定算法。
        pills = self._pill_widgets()
        if not pills:
            return 0

        x = pos.x()
        for i, p in enumerate(pills):
            r = p.geometry()
            if r.contains(pos):
                return i

        # fallback：中心点分界
        centers: List[int] = []
        for p in pills:
            r = p.geometry()
            centers.append(r.left() + r.width() // 2)
        for i, cx in enumerate(centers):
            if x < cx:
                return i
        return len(pills)

    def _show_placeholder(self, insert_index: int):
        if self._placeholder.parent() is None:
            self._placeholder.setParent(self)
        if not self._placeholder.isVisible():
            self._placeholder.show()

        # 移除旧位置
        for i in range(self._lay.count()):
            w = self._lay.itemAt(i).widget()
            if w is self._placeholder:
                self._lay.takeAt(i)
                break

        pills = self._pill_widgets()
        insert_index = max(0, min(insert_index, len(pills)))

        # 算出在 layout 中对应的 widget index（pill 与 op 交错，外加 stretch）
        # 每个 pill 占 1；除最后外每个 op 占 1
        layout_index = 0
        pill_seen = 0
        while layout_index < self._lay.count():
            w = self._lay.itemAt(layout_index).widget()
            if isinstance(w, _PriorityChipWidget):
                if pill_seen == insert_index:
                    break
                pill_seen += 1
            layout_index += 1

        self._lay.insertWidget(layout_index, self._placeholder)

        # 更强的视觉提示：在显示时临时加深（避免一直很亮）
        try:
            self._placeholder.setStyleSheet(
                """
                QFrame {
                    border: 1px dashed rgba(88, 166, 255, 0.80);
                    border-radius: 14px;
                    background: rgba(88, 166, 255, 0.16);
                }
                """
            )
        except Exception:
            pass


class _PriorityChipStyle(QProxyStyle):
    """让 QListWidget 的 item 尺寸更紧凑一点（避免影响全局样式）。"""

    def pixelMetric(self, metric, option=None, widget=None):  # type: ignore[override]
        if metric == QStyle.PM_FocusFrameHMargin:
            return 0
        return super().pixelMetric(metric, option, widget)


class _PriorityChip(QWidget):
    """优先级小卡片：左侧文本 + 右侧循环按钮(>/=)。最后一项按钮隐藏。"""

    def __init__(self, label: str, relation: Optional[str], is_last: bool, on_toggle):
        super().__init__()
        self._on_toggle = on_toggle

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 4, 8, 4)
        lay.setSpacing(6)

        self.label = QLabel(label)
        self.label.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        lay.addWidget(self.label, 1)

        # 固定位置的关系符号按钮（右侧固定宽度，不随文本变化）
        self.btn = QPushButton()
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.setFixedSize(22, 18)
        self.btn.setFocusPolicy(Qt.NoFocus)
        self.btn.setVisible(not is_last)
        self.btn.clicked.connect(self._on_toggle)
        lay.addWidget(self.btn, 0, Qt.AlignRight | Qt.AlignVCenter)

        self.set_relation(relation)

        self.setObjectName("priorityChip")
        self.setStyleSheet(
            """
            QWidget#priorityChip {
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 10px;
                background: rgba(255,255,255,0.05);
            }
            QWidget#priorityChip:hover {
                border: 1px solid rgba(255,255,255,0.28);
                background: rgba(255,255,255,0.07);
            }
            QWidget#priorityChip QLabel {
                color: rgba(255,255,255,0.92);
            }
            QWidget#priorityChip QPushButton {
                border: 1px solid rgba(255,255,255,0.18);
                border-radius: 6px;
                background: rgba(255,255,255,0.06);
                padding: 0px;
                font-weight: 600;
            }
            QWidget#priorityChip QPushButton:hover {
                border: 1px solid rgba(255,255,255,0.30);
                background: rgba(255,255,255,0.10);
            }
            """
        )

    def set_relation(self, relation: Optional[str]):
        if relation in (">", "="):
            self.btn.setText(relation)
        else:
            self.btn.setText("")


class _FlowLayout(QLayout):
    """简单 FlowLayout：让子控件按行自动换行布局。"""

    def __init__(self, parent=None, margin: int = 0, spacing: int = 6):
        super().__init__(parent)
        self._items: List[QLayoutItem] = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

    def addItem(self, item: QLayoutItem) -> None:  # type: ignore[override]
        self._items.append(item)

    def addWidget(self, w: QWidget) -> None:  # type: ignore[override]
        super().addWidget(w)

    def count(self) -> int:  # type: ignore[override]
        return len(self._items)

    def itemAt(self, index: int):  # type: ignore[override]
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):  # type: ignore[override]
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):  # type: ignore[override]
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self) -> bool:  # type: ignore[override]
        return True

    def heightForWidth(self, width: int) -> int:  # type: ignore[override]
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:  # type: ignore[override]
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # type: ignore[override]
        size = QSize(0, 0)
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        m = self.contentsMargins()
        x = rect.x() + m.left()
        y = rect.y() + m.top()
        line_h = 0
        space = self.spacing()
        max_w = rect.width() - (m.left() + m.right())

        for item in self._items:
            hint = item.sizeHint()
            w = hint.width()
            h = hint.height()
            if x > rect.x() + m.left() and (x - (rect.x() + m.left()) + w) > max_w:
                x = rect.x() + m.left()
                y = y + line_h + space
                line_h = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))

            x = x + w + space
            line_h = max(line_h, h)

        return (y + line_h + m.bottom()) - rect.y()


class _PriorityChipWidget(QFrame):
    """方案A：真正的“胶囊卡片”，支持拖拽排序。

    - 左：标题
    - 右：固定宽度关系区（按钮），位置稳定
    """

    def __init__(self, label: str, relation: Optional[str], is_last: bool, key: str, owner):
        super().__init__()
        self._owner = owner
        self._key = key
        self._is_last = is_last
        self._drag_start: Optional[QPoint] = None

        self.setObjectName("priorityPill")
        self.setFrameShape(QFrame.NoFrame)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 4, 8, 4)
        lay.setSpacing(6)

        self.label = QLabel(label)
        # 使用 Preferred 而不是 MinimumExpanding，让标签显示完整文字
        self.label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.label.setMinimumWidth(60)  # 确保最小宽度
        lay.addWidget(self.label, 0)  # stretch=0 让胶囊自适应文字宽度

        self.rel_btn = QPushButton()
        self.rel_btn.setFocusPolicy(Qt.NoFocus)
        self.rel_btn.setCursor(Qt.PointingHandCursor)
        self.rel_btn.setFixedSize(24, 18)
        self.rel_btn.setVisible(not is_last)
        self.rel_btn.clicked.connect(self._on_toggle)
        lay.addWidget(self.rel_btn, 0, Qt.AlignRight | Qt.AlignVCenter)

        self.set_relation(relation)
        # 更接近截图的“扁平胶囊”
        self.setStyleSheet(
            """
            QFrame#priorityPill {
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 14px;
                background: rgba(255,255,255,0.04);
            }
            QFrame#priorityPill:hover {
                border: 1px solid rgba(255,255,255,0.26);
                background: rgba(255,255,255,0.06);
            }
            QFrame#priorityPill QLabel { color: rgba(255,255,255,0.92); }
            QFrame#priorityPill QPushButton {
                border: 1px solid rgba(255,255,255,0.18);
                border-radius: 6px;
                background: rgba(255,255,255,0.06);
                padding: 0px;
                font-weight: 650;
            }
            QFrame#priorityPill QPushButton:hover {
                border: 1px solid rgba(255,255,255,0.30);
                background: rgba(255,255,255,0.10);
            }
            """
        )

    def key(self) -> str:
        return self._key

    def set_relation(self, relation: Optional[str]):
        if relation in (">", "="):
            self.rel_btn.setText(relation)
        else:
            self.rel_btn.setText("")

    def _on_toggle(self):
        if self._is_last:
            return
        self._owner.toggle_relation_for_key(self._key)

    def mousePressEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            # 从胶囊任意位置拖拽（按钮点击已经单独处理）
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # type: ignore[override]
        # 只在按住左键移动时才启动拖拽；否则会导致“轻微移动就弹出拖拽窗口”的异常体验
        if (event.buttons() & Qt.LeftButton) == 0:
            return super().mouseMoveEvent(event)

        if self._drag_start is None:
            return super().mouseMoveEvent(event)

        # 如果鼠标在运算符按钮区域内，禁止开启拖拽（避免点击/轻微移动触发 drag）
        try:
            pos = event.position().toPoint()
            if self.rel_btn.isVisible() and self.rel_btn.geometry().contains(pos):
                return super().mouseMoveEvent(event)
        except Exception:
            pass

        if (event.position().toPoint() - self._drag_start).manhattanLength() < QApplication.startDragDistance():
            return super().mouseMoveEvent(event)
        event.accept()
        self._owner.start_drag(self)


class _PriorityFlowWidget(QWidget):
    """方案A容器：FlowLayout + 自定义 drag/drop，提供占位预览并写回顺序。"""

    def __init__(self, owner):
        super().__init__()
        self._owner = owner
        self._flow = _FlowLayout(self, margin=0, spacing=6)
        self.setLayout(self._flow)
        self.setAcceptDrops(True)
        self._chips: List[_PriorityChipWidget] = []

        self._placeholder = QFrame()
        self._placeholder.setObjectName("priorityPlaceholder")
        self._placeholder.setFixedSize(120, 26)
        self._placeholder.setStyleSheet(
            """
            QFrame#priorityPlaceholder {
                border: 1px dashed rgba(255,255,255,0.25);
                border-radius: 12px;
                background: rgba(255,255,255,0.03);
            }
            """
        )
        self._placeholder.hide()

        self.setMinimumHeight(44)
        self.setMaximumHeight(86)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def clear(self):
        while self._flow.count():
            it = self._flow.takeAt(0)
            if it is None:
                break
            w = it.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._chips = []

    def set_items(self, items: List[Dict[str, Any]]):
        self.clear()
        self._placeholder.hide()

        for idx, it in enumerate(items):
            is_last = idx == len(items) - 1
            key = str(it.get("key"))
            label = self._owner._priority_key_to_label(key)
            rel = it.get("relation") if not is_last else None

            chip = _PriorityChipWidget(label=label, relation=rel, is_last=is_last, key=key, owner=self)
            chip.setMinimumHeight(26)
            chip.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            self._chips.append(chip)
            self._flow.addWidget(chip)

        # 预创建 placeholder 但不在 layout 中占位，拖拽时再插入

    def start_drag(self, chip: _PriorityChipWidget):
        self._drag_chip = chip
        drag = QDrag(chip)
        mime = QMimeData()
        mime.setText(chip.key())
        drag.setMimeData(mime)
        drag.exec(Qt.MoveAction)

    def toggle_relation_for_key(self, key: str):
        self._owner._toggle_relation_by_key(key)

    def dragEnterEvent(self, event):  # type: ignore[override]
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):  # type: ignore[override]
        if not event.mimeData().hasText():
            return event.ignore()
        event.acceptProposedAction()
        self._update_placeholder(event.position().toPoint())

    def dropEvent(self, event):  # type: ignore[override]
        if not event.mimeData().hasText():
            return event.ignore()
        key = event.mimeData().text()
        idx = self._placeholder_index_for_pos(event.position().toPoint())
        self._placeholder.hide()
        self._owner._move_priority_key(key, idx)
        event.acceptProposedAction()

    def leaveEvent(self, event):  # type: ignore[override]
        self._placeholder.hide()
        return super().leaveEvent(event)

    def _update_placeholder(self, pos: QPoint):
        idx = self._placeholder_index_for_pos(pos)
        self._show_placeholder_at(idx)

    def _show_placeholder_at(self, index: int):
        # layout 中插入一个 placeholder
        if self._placeholder.parent() is None:
            self._placeholder.setParent(self)
        if not self._placeholder.isVisible():
            self._placeholder.show()

        # 先移除旧位置（如果存在）
        try:
            self._flow.removeWidget(self._placeholder)
        except Exception:
            # removeWidget 可能不存在于极老版本；兜底用遍历 takeAt
            for i in range(self._flow.count()):
                it = self._flow.itemAt(i)
                if it is not None and it.widget() is self._placeholder:
                    self._flow.takeAt(i)
                    break

        # clamp 后插入
        index = max(0, min(index, self._flow.count()))
        self._flow.insertWidget(index, self._placeholder)
        self.updateGeometry()
        self.update()

    def _placeholder_index_for_pos(self, pos: QPoint) -> int:
        # 通过 chip 的区间决定插入位置：落在 chip 左半边->其前，否则->其后
        chips = [c for c in self._chips if c.isVisible()]
        if not chips:
            return 0
        for i, c in enumerate(chips):
            r = c.geometry()
            if pos.y() < r.top() - 8:
                return 0
            if r.contains(pos):
                return i if pos.x() < (r.left() + r.width() // 2) else i + 1
        return len(chips)


from src.core.multi_thread_matcher import AsyncMaterialMatcher
from src.core.i18n import _


@dataclass
class _MatchRunConfig:
    source_material_name: str
    source_library_id: int
    target_library_id: int
    similarity_threshold: float
    priority_order: List[str]


class _MatchSignals(QObject):
    progress = Signal(int, int, int)  # percent, processed, total
    finished = Signal(list, object)  # results, error(str|None)


class MaterialMatchingDialogQt(QDialog):
    """Qt 版材质匹配对话框（最小可用版）。

    约定：
    - 输入：源库、目标库、源材质名（可为空）、相似度阈值
    - 输出：展示匹配结果（Top N），可复制目标材质文件名
    - 线程：复用 core 的 `AsyncMaterialMatcher`，通过 Qt Signal 回主线程更新 UI
    """

    def __init__(
        self,
        parent,
        database_manager,
        initial_source_library_id: Optional[int] = None,
        initial_material_name: str = "",
        version_tag: str = "MM-20251217-01",
    ):
        super().__init__(parent)
        
        # 应用深色标题栏
        from .dark_titlebar import apply_dark_titlebar_to_dialog
        apply_dark_titlebar_to_dialog(self)
        self.setWindowTitle(_('matching_dialog_title'))
        self.setModal(False)
        self.resize(980, 720)

        self.db = database_manager
        self.async_matcher = AsyncMaterialMatcher(database_manager)
        self.signals = _MatchSignals()
        self.signals.progress.connect(self._on_progress)
        self.signals.finished.connect(self._on_finished)

        self._current_run: Optional[_MatchRunConfig] = None
        self._running = False
        self._last_results = []  # type: List[Dict[str, Any]]
        self._last_mode = ""  # fast/exact
        self._last_progress_ui_tick = 0  # 用于 UI 刷新节流

        # 优先级模块（顺序 + 与下一项关系）
        self.priority_items = []  # type: List[Dict[str, Any]]
        self._priority_selected_row = -1

        # settings
        self._settings = QSettings("FSmatbinBD", "MaterialLibrary")

        self._build_ui()

        self._load_libraries(initial_source_library_id)
        self.source_material_edit.setText(initial_material_name or "")

        # 初始化优先级（从持久化恢复，否则用默认）
        self._load_priority_config()
        self._render_priority_list()

    # ---------------- UI ----------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ===== Title / Hint (对齐旧版) =====
        title_row = QHBoxLayout()
        title = QLabel(_('material_matching_title'))
        title.setStyleSheet("font-size:16px; font-weight:600;")
        title_row.addWidget(title)
        title_row.addStretch(1)
        hint = QLabel(_('matching_hint'))
        hint.setStyleSheet("color: #9aa4b2;")
        title_row.addWidget(hint)
        root.addLayout(title_row)

        # ===== 输入区（对齐旧版：材质名 + 源/目标库） =====
        input_group = QGroupBox(_('material_input_section'))
        input_layout = QFormLayout(input_group)
        input_layout.setLabelAlignment(Qt.AlignRight)
        input_layout.setFormAlignment(Qt.AlignTop)

        self.source_material_edit = QLineEdit()
        self.source_material_edit.setPlaceholderText(_('input_source_material_placeholder'))

        self.source_library_combo = QComboBox()
        self.target_library_combo = QComboBox()

        input_layout.addRow(_('matching_material_label'), self.source_material_edit)
        input_layout.addRow(_('matching_source_lib_label'), self.source_library_combo)
        input_layout.addRow(_('matching_target_lib_label'), self.target_library_combo)
        root.addWidget(input_group)

        # ===== 匹配配置区（紧凑：阈值滑条 + 卡片优先级） =====
        cfg_group = QGroupBox(_('matching_config_section'))
        cfg_group.setFlat(False)
        cfg_layout = QFormLayout(cfg_group)
        cfg_layout.setLabelAlignment(Qt.AlignRight)
        cfg_layout.setFormAlignment(Qt.AlignTop)

        # --- threshold: slider + spinbox ---
        threshold_container = QWidget()
        threshold_row = QHBoxLayout(threshold_container)
        threshold_row.setContentsMargins(0, 0, 0, 0)
        threshold_row.setSpacing(8)

        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(10, 100)  # 0.10 - 1.00
        self.threshold_slider.setValue(50)
        self.threshold_slider.setSingleStep(1)
        self.threshold_slider.setPageStep(5)
        self.threshold_slider.setMinimumWidth(260)

        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.10, 1.00)
        self.threshold_spin.setSingleStep(0.01)
        self.threshold_spin.setDecimals(2)
        self.threshold_spin.setValue(0.50)
        self.threshold_spin.setFixedWidth(80)

        # 双向绑定
        self.threshold_slider.valueChanged.connect(lambda v: self.threshold_spin.setValue(v / 100.0))
        self.threshold_spin.valueChanged.connect(lambda v: self.threshold_slider.setValue(int(round(v * 100))))

        threshold_row.addWidget(self.threshold_slider, 1)
        threshold_row.addWidget(self.threshold_spin, 0)
        cfg_layout.addRow(_('similarity_threshold_label'), threshold_container)

        # --- priority: 下拉框互换方案 ---
        self.priority_row = _PriorityComboRow(owner=self)

        # 单行横向滚动容器
        self.priority_scroll = QScrollArea()
        self.priority_scroll.setWidgetResizable(True)
        self.priority_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.priority_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.priority_scroll.setFrameShape(QFrame.NoFrame)
        self.priority_scroll.setWidget(self.priority_row)
        self.priority_scroll.setFixedHeight(36)
        self.priority_scroll.setStyleSheet(
            """
            QScrollArea { background: transparent; }
            QScrollBar:horizontal {
                height: 10px;
                background: rgba(255,255,255,0.04);
                border-radius: 5px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: rgba(88,166,255,0.45);
                border-radius: 5px;
                min-width: 24px;
            }
            QScrollBar::handle:horizontal:hover {
                background: rgba(88,166,255,0.65);
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px; height: 0px;
            }
            """
        )

        cfg_layout.addRow(_('priority_drag_label'), self.priority_scroll)

        root.addWidget(cfg_group)

        # ===== 匹配按钮区（保留：快速匹配/精确匹配/停止/导出） =====
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        self.exact_btn = QPushButton(_('btn_exact_match'))
        self.fast_btn = QPushButton(_('btn_fast_match'))
        self.stop_btn = QPushButton(_('btn_stop'))
        self.export_btn = QPushButton(_('btn_export_result'))

        # 更现代一点的按钮/进度条样式（局部，不污染全局主题）
        btn_base = (
            "QPushButton {"
            "  padding: 6px 12px;"
            "  border-radius: 8px;"
            "  font-weight: 600;"
            "  border: 1px solid rgba(255,255,255,0.12);"
            "}"
            "QPushButton:hover { border-color: rgba(255,255,255,0.25); }"
            "QPushButton:pressed { background: rgba(255,255,255,0.08); }"
            "QPushButton:disabled { color: rgba(255,255,255,0.35); border-color: rgba(255,255,255,0.08); background: rgba(255,255,255,0.03); }"
        )
        self.exact_btn.setStyleSheet(
            btn_base
            + "QPushButton { background: rgba(88,166,255,0.25); border-color: rgba(88,166,255,0.55); }"
            + "QPushButton:hover { background: rgba(88,166,255,0.32); }"
        )
        self.fast_btn.setStyleSheet(
            btn_base
            + "QPushButton { background: rgba(255,255,255,0.06); }"
            + "QPushButton:hover { background: rgba(255,255,255,0.09); }"
        )
        self.stop_btn.setStyleSheet(
            btn_base
            + "QPushButton { background: rgba(248,81,73,0.16); border-color: rgba(248,81,73,0.55); }"
            + "QPushButton:hover { background: rgba(248,81,73,0.22); }"
        )
        self.export_btn.setStyleSheet(
            btn_base
            + "QPushButton { background: rgba(46,160,67,0.16); border-color: rgba(46,160,67,0.55); }"
            + "QPushButton:hover { background: rgba(46,160,67,0.22); }"
        )

        self.stop_btn.setEnabled(False)
        self.export_btn.setEnabled(False)

        self.exact_btn.clicked.connect(self._start_exact_matching)
        self.fast_btn.clicked.connect(self._start_fast_matching)
        self.stop_btn.clicked.connect(self._cancel_matching)
        self.export_btn.clicked.connect(self._export_results)

        actions_row.addWidget(self.exact_btn)
        actions_row.addWidget(self.fast_btn)
        actions_row.addWidget(self.stop_btn)
        actions_row.addWidget(self.export_btn)

        actions_row.addStretch(1)

        self.progress_label = QLabel(_('ready'))
        self.progress_label.setStyleSheet("color: rgba(255,255,255,0.80);")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMinimumWidth(260)
        self.progress_bar.setFixedHeight(16)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 8px;
                background: rgba(255,255,255,0.05);
                text-align: center;
                color: rgba(255,255,255,0.85);
            }
            QProgressBar::chunk {
                border-radius: 8px;
                background: rgba(88,166,255,0.70);
            }
            """
        )

        actions_row.addWidget(self.progress_label)
        actions_row.addWidget(self.progress_bar)

        root.addLayout(actions_row)

        # results
        self.results_table = SmoothTableWidget(0, 4)
        self.results_table.setHorizontalHeaderLabels([_('similarity'), _('header_target_material'), _('header_target_lib'), _('header_details')])
        self.results_table.setSelectionBehavior(SmoothTableWidget.SelectRows)
        self.results_table.setEditTriggers(SmoothTableWidget.NoEditTriggers)
        self.results_table.setSortingEnabled(True)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setStyleSheet("""
            QTableWidget {
                background: rgba(10, 14, 24, 160);
                alternate-background-color: rgba(255, 255, 255, 5);
                gridline-color: rgba(255, 255, 255, 8);
                border: 1px solid rgba(110, 165, 255, 90);
                border-radius: 14px;
                font-size: 9pt;
            }
            QTableWidget::item {
                padding: 6px 10px;
            }
            QTableWidget::item:hover {
                background-color: rgba(47, 129, 247, 18);
            }
            QTableWidget::item:selected {
                background-color: rgba(47, 129, 247, 230);
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: rgba(255, 255, 255, 5);
                color: rgba(245,248,255,235);
                padding: 5px 8px;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 8);
                font-size: 9pt;
                font-weight: 750;
            }
        """)
        self.results_table.cellDoubleClicked.connect(self._copy_cell_text)
        self.results_table.cellClicked.connect(self._on_result_clicked)

        root.addWidget(self.results_table, 1)

        # pagination controls
        page_row = QHBoxLayout()
        page_row.setContentsMargins(0, 8, 0, 0)
        page_row.setSpacing(8)
        
        self.page_prev_btn = QPushButton("◀ 上一页")
        self.page_prev_btn.setFixedWidth(90)
        self.page_prev_btn.clicked.connect(self._on_prev_page)
        
        self.page_label = QLabel("第 1/1 页")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setMinimumWidth(120)
        
        self.page_next_btn = QPushButton("下一页 ▶")
        self.page_next_btn.setFixedWidth(90)
        self.page_next_btn.clicked.connect(self._on_next_page)
        
        self.page_info_label = QLabel("共 0 条结果")
        self.page_info_label.setStyleSheet("color: rgba(255,255,255,0.7);")
        
        # close button merged into pagination row
        self.close_btn = QPushButton(_('close'))
        self.close_btn.setFixedWidth(80)
        self.close_btn.clicked.connect(self.close)
        
        page_row.addWidget(self.page_prev_btn)
        page_row.addWidget(self.page_label)
        page_row.addWidget(self.page_next_btn)
        page_row.addStretch(1)
        page_row.addWidget(self.page_info_label)
        page_row.addSpacing(16)
        page_row.addWidget(self.close_btn)
        
        root.addLayout(page_row)
        
        # pagination state
        self._page_size = 500
        self._current_page = 0
        self._all_results = []  # 存储所有结果用于分页

    # ---------------- priority config (drag & persist) ----------------
    def _priority_default_items(self) -> List[Dict[str, Any]]:
        # 最后一项 relation=None
        items = [
            {"key": "sampler_types", "relation": ">"},
            {"key": "shader_path", "relation": ">"},
            {"key": "material_keywords", "relation": ">"},
            {"key": "sampler_count", "relation": ">"},
            {"key": "parameters", "relation": ">"},
            {"key": "sampler_paths", "relation": None},
        ]
        return items

    def _priority_key_to_label(self, key: str) -> str:
        mapping = {
            "sampler_types": _('sampler_types'),
            "shader_path": _('priority_shader_path'),
            "material_keywords": _('material_keywords'),
            "sampler_count": _('sampler_count'),
            "parameters": _('parameters'),
            "sampler_paths": _('sampler_paths'),
        }
        return mapping.get(key, key)

    def _priority_item_label(self, item: Dict[str, Any], is_last: bool) -> str:
        # 显示“模块名  >” 或 “模块名  =”；最后一项不显示关系
        base = self._priority_key_to_label(str(item.get("key", "")))
        rel = item.get("relation") if not is_last else None
        if rel in (">", "="):
            return f"{base}  {rel}"
        return base

    def _load_priority_config(self):
        raw = self._settings.value("material_matching/priority_items", None)
        if isinstance(raw, str) and raw.strip():
            try:
                import json

                data = json.loads(raw)
                if isinstance(data, list) and data:
                    # 合法性过滤
                    keys = {"sampler_types", "shader_path", "material_keywords", "sampler_count", "parameters", "sampler_paths"}
                    cleaned = []
                    for it in data:
                        if not isinstance(it, dict):
                            continue
                        k = it.get("key")
                        if k not in keys:
                            continue
                        rel = it.get("relation")
                        if rel not in (">", "=", None):
                            rel = ">"
                        cleaned.append({"key": k, "relation": rel})
                    # 去重补齐缺项（保持原顺序）
                    seen = set()
                    result = []
                    for it in cleaned:
                        if it["key"] in seen:
                            continue
                        seen.add(it["key"])
                        result.append(it)
                    for k in ["sampler_types", "shader_path", "material_keywords", "sampler_count", "parameters", "sampler_paths"]:
                        if k not in seen:
                            result.append({"key": k, "relation": ">"})
                    if result:
                        result[-1]["relation"] = None
                        self.priority_items = result
                        return
            except Exception:
                pass

        self.priority_items = self._priority_default_items()

    def _save_priority_config(self):
        try:
            import json

            self._settings.setValue("material_matching/priority_items", json.dumps(self.priority_items, ensure_ascii=False))
        except Exception:
            # QSettings 写入失败不应影响主流程
            return

    def _render_priority_list(self):
        # 方案A(改)：单行渲染，运算符固定位置
        if hasattr(self, "priority_row"):
            self.priority_row.set_items(self.priority_items)

    def _sync_priority_items_from_view(self):
        # 方案A不再从 view 反推数据
        return

    def _on_priority_row_changed(self, row: int):
        self._priority_selected_row = row

    def _on_priority_reordered(self):
        # 方案A：拖拽直接作用于 priority_items，这里保留兼容钩子
        self._render_priority_list()
        self._save_priority_config()

    def _toggle_relation_at(self, row: int):
        # 循环切换 row 与下一项的关系：'>' <-> '='（最后一项无关系）
        if row < 0 or row >= self.priority_list.count() - 1:
            return
        witem = self.priority_list.item(row)
        data = witem.data(Qt.UserRole)
        if not isinstance(data, dict):
            return
        rel = data.get("relation")
        data["relation"] = "=" if rel != "=" else ">"
        witem.setData(Qt.UserRole, data)
        self._sync_priority_items_from_view()
        self._render_priority_list()
        self._save_priority_config()

    # ---------------- scheme A actions ----------------
    def _toggle_relation_at_index(self, index: int):
        """根据索引切换运算符"""
        if index < 0 or index >= len(self.priority_items) - 1:
            return
        rel = self.priority_items[index].get("relation")
        self.priority_items[index]["relation"] = "=" if rel != "=" else ">"
        if self.priority_items:
            self.priority_items[-1]["relation"] = None
        self._save_priority_config()
        self._render_priority_list()

    def _swap_priority_at(self, position: int, new_key: str):
        """在 position 位置选择了 new_key，执行互换"""
        if position < 0 or position >= len(self.priority_items):
            return
        
        # 找到 new_key 当前的位置
        new_position = -1
        for i, it in enumerate(self.priority_items):
            if str(it.get("key")) == str(new_key):
                new_position = i
                break
        
        if new_position < 0 or new_position == position:
            return  # 选的是自己，不动
        
        # 交换两个位置的内容（保留各自的 relation）
        items = list(self.priority_items)
        items[position], items[new_position] = items[new_position], items[position]
        
        # 确保最后一项 relation=None
        if items:
            items[-1]["relation"] = None
        
        self.priority_items = items
        self._save_priority_config()
        self._render_priority_list()

    def _index_of_key(self, key: str) -> int:
        for i, it in enumerate(getattr(self, "priority_items", []) or []):
            if str(it.get("key")) == str(key):
                return i
        return -1

    def _toggle_relation_by_key(self, key: str):
        idx = self._index_of_key(key)
        if idx < 0 or idx >= len(self.priority_items) - 1:
            return
        rel = self.priority_items[idx].get("relation")
        self.priority_items[idx]["relation"] = "=" if rel != "=" else ">"
        # 确保最后一项 relation=None
        if self.priority_items:
            self.priority_items[-1]["relation"] = None
        self._save_priority_config()
        self._render_priority_list()

    def _move_priority_key(self, key: str, target_index: int):
        # 彻底简化：把 key 项移动到 target_index 位置。
        items = list(self.priority_items)
        src = -1
        for i, it in enumerate(items):
            if str(it.get("key")) == str(key):
                src = i
                break
        if src < 0:
            return

        # 拖到自己身上：不动
        if target_index == src:
            return

        moving = items.pop(src)

        # pop 后索引会变化：如果目标在源之后，需要 -1
        if target_index > src:
            target_index -= 1

        # clamp 到合法范围
        target_index = max(0, min(target_index, len(items)))

        items.insert(target_index, moving)

        if items:
            items[-1]["relation"] = None
        self.priority_items = items
        self._save_priority_config()
        self._render_priority_list()

    def _load_libraries(self, initial_source_library_id: Optional[int]):
        libs = self.db.get_libraries()

        self.source_library_combo.blockSignals(True)
        self.target_library_combo.blockSignals(True)
        self.source_library_combo.clear()
        self.target_library_combo.clear()

        source_index_to_set = 0
        target_index_to_set = 0

        for idx, lib in enumerate(libs):
            self.source_library_combo.addItem(lib.get("name", ""), lib)
            self.target_library_combo.addItem(lib.get("name", ""), lib)
            if initial_source_library_id is not None and lib.get("id") == initial_source_library_id:
                source_index_to_set = idx

        # 默认目标库：若有两库则选第二个，否则同库
        if len(libs) >= 2:
            target_index_to_set = 1 if source_index_to_set == 0 else 0

        self.source_library_combo.setCurrentIndex(source_index_to_set if libs else -1)
        self.target_library_combo.setCurrentIndex(target_index_to_set if libs else -1)

        self.source_library_combo.blockSignals(False)
        self.target_library_combo.blockSignals(False)

    # ---------------- logic ----------------
    def _get_priority_order(self) -> List[str]:
        # 基于拖拽模块条生成 flatten 顺序（与 Tk 版 _get_priority_order 一致：直接展平）
        if getattr(self, "priority_items", None):
            return [str(it.get("key")) for it in self.priority_items if it.get("key")]
        return ["sampler_types", "shader_path", "material_keywords", "sampler_count", "parameters", "sampler_paths"]

    def _get_priority_groups(self) -> List[List[str]]:
        # 根据 relation('>'/'=') 生成分组，用于 core 的 _calculate_weights_with_groups
        items = getattr(self, "priority_items", None) or []
        groups: List[List[str]] = []
        cur: List[str] = []
        for i, it in enumerate(items):
            key = it.get("key")
            if not key:
                continue
            cur.append(str(key))
            rel = it.get("relation")
            if i == len(items) - 1 or rel == ">":
                if cur:
                    groups.append(cur)
                cur = []
        return groups if groups else [["sampler_types"], ["shader_path"], ["material_keywords"]]

    def _get_similarity_threshold(self) -> float:
        # 统一阈值来源：以 spinbox 为准（slider 已双向绑定）
        try:
            v = float(self.threshold_spin.value())
        except Exception:
            v = 0.5
        return max(0.10, min(1.00, v))

    def _resolve_source_material(self, source_library_id: int, keyword: str) -> Optional[Dict[str, Any]]:
        # 优先用 search_materials（与主界面一致）
        keyword = (keyword or "").strip()
        mats = self.db.search_materials(library_id=source_library_id, keyword=keyword)
        if mats:
            return mats[0]
        # 若 keyword 为空也没有结果：回退拿库里所有材质第一条
        mats2 = self.db.get_materials_by_library(source_library_id)
        return mats2[0] if mats2 else None

    def _start_exact_matching(self):
        """精确匹配：走 MultiThreadMaterialMatcher 并发全量策略（通过 AsyncMaterialMatcher）。"""
        self._start_matching(mode="exact")

    def _start_fast_matching(self):
        """快速匹配：走 MaterialMatcher 两层策略（预筛选 + 全量兜底），仍后台线程避免卡 UI。"""
        self._start_matching(mode="fast")

    def _start_matching(self, mode: str):
        if self._running:
            return

        src_data = self.source_library_combo.currentData()
        tgt_data = self.target_library_combo.currentData()
        if not isinstance(src_data, dict) or not isinstance(tgt_data, dict):
            QMessageBox.information(self, _('info'), _('msg_select_libraries'))
            return

        source_library_id = src_data.get("id")
        target_library_id = tgt_data.get("id")
        if not source_library_id or not target_library_id:
            QMessageBox.information(self, _('info'), _('msg_invalid_libraries'))
            return

        if source_library_id == target_library_id:
            QMessageBox.information(self, _('info'), _('msg_same_libraries'))
            return

        source_material = self._resolve_source_material(source_library_id, self.source_material_edit.text())
        if not source_material:
            QMessageBox.information(self, _('info'), _('msg_no_source_material'))
            return

        # 阈值转换：spinbox 是 0.0-1.0，匹配器需要 0-100
        threshold = float(self.threshold_spin.value()) * 100.0
        priority_order = self._get_priority_order()

        self._current_run = _MatchRunConfig(
            source_material_name=str(source_material.get("name") or source_material.get("file_name") or ""),
            source_library_id=source_library_id,
            target_library_id=target_library_id,
            similarity_threshold=threshold,
            priority_order=priority_order,
        )

        self._running = True
        self._last_mode = mode
        self._last_results = []

        self.exact_btn.setEnabled(False)
        self.fast_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.export_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_label.setText(_('status_matching'))
        self.results_table.setRowCount(0)

        # 复用 core 的 AsyncMaterialMatcher 线程逻辑，但 completion/progress 回调要转为 Qt signal。
        # 注意：MultiThreadMaterialMatcher 的 progress_callback 只会传一个 percent(float)，
        # Tk 版通过包装层扩展成 (progress, processed, total)。这里兼容两种签名。
        def progress_cb(*args):
            try:
                if len(args) == 1:
                    progress = float(args[0])
                    percent = int(max(0, min(100, progress)))
                    self.signals.progress.emit(percent, 0, 0)
                    return
                if len(args) >= 3:
                    progress = float(args[0])
                    processed = int(args[1])
                    total = int(args[2])
                    percent = int(max(0, min(100, progress)))
                    self.signals.progress.emit(percent, processed, total)
                    return
                # fallback
                if args:
                    progress = float(args[0])
                    percent = int(max(0, min(100, progress)))
                    self.signals.progress.emit(percent, 0, 0)
            except Exception:
                # 进度回调里不要抛异常，避免被 core 静默吞掉导致“看起来没反应”
                return

        def completion_cb(results: List[Dict[str, Any]], error: Optional[str]):
            self.signals.finished.emit(results, error)

        # exact / fast 两条路径
        if mode == "exact":
            self.async_matcher.start_matching(
                source_material=source_material,
                target_library_id=target_library_id,
                priority_order=priority_order,
                similarity_threshold=threshold,
                progress_callback=progress_cb,
                completion_callback=completion_cb,
            )
        else:
            # fast：使用 MaterialMatcher 的两层策略（预筛选，0结果再全面搜索）。
            import threading

            from src.core.material_matcher import MaterialMatcher

            # 执行体
            def worker():
                try:
                    matcher = MaterialMatcher(self.db)
                    results = matcher.find_similar_materials(
                        source_material,
                        target_library_id,
                        priority_order,
                        threshold,
                    )
                    completion_cb(results, None)
                except Exception as e:
                    completion_cb([], str(e))

            threading.Thread(target=worker, daemon=True).start()

    def _cancel_matching(self):
        if not self._running:
            return
        try:
            self.async_matcher.stop_matching()
        finally:
            self._running = False
            self.exact_btn.setEnabled(True)
            self.fast_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.progress_label.setText("已取消")

    # ---------------- slots ----------------
    def _on_progress(self, percent: int, processed: int, total: int):
        self.progress_bar.setValue(percent)
        if total:
            self.progress_label.setText(f"匹配中… {processed}/{total}")
        else:
            self.progress_label.setText(f"匹配中… {percent}%")

        # 保障 UI 实时刷新：在高频进度下做轻量节流，避免卡顿
        try:
            import time

            now = time.monotonic()
            if now - float(getattr(self, "_last_progress_ui_tick", 0)) >= 0.05:
                self._last_progress_ui_tick = now
                QApplication.processEvents()
        except Exception:
            pass

    def _on_finished(self, results: List[Dict[str, Any]], error: Any):
        self._running = False
        self.exact_btn.setEnabled(True)
        self.fast_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        if error:
            self.progress_label.setText("失败")
            # 只在确实失败时提示；该弹窗是正常提示，不是“异常窗口”
            QMessageBox.warning(self, "匹配失败", str(error))
            return

        self._last_results = results or []
        # UI 兜底按阈值过滤（防止 core 返回未过滤情况）
        # 注意：相似度分数范围是 0-100，阈值需要转换
        try:
            thr = self._get_similarity_threshold() * 100.0  # 转换为 0-100 范围
            self._last_results = [r for r in self._last_results if float(r.get("similarity", 0.0)) >= thr]
        except Exception:
            pass
        self.export_btn.setEnabled(bool(self._last_results))
        self.progress_label.setText(f"完成：{len(self._last_results)} 条")
        self.progress_bar.setValue(100)
        self._fill_results(self._last_results)

    def _export_results(self):
        if not self._last_results:
            QMessageBox.information(self, "提示", "没有可导出的结果")
            return

        file_path, _unused = QFileDialog.getSaveFileName(
            self,
            "导出匹配结果",
            "matching_results.csv",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not file_path:
            return

        try:
            import csv

            with open(file_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["similarity", "target_library", "target_material", "details"])
                for item in self._last_results:
                    similarity = item.get("similarity", 0.0)
                    lib_name = item.get("library_name", "")
                    target_material = item.get("target_material") or item.get("material") or {}
                    target_name = (
                        target_material.get("name")
                        or target_material.get("file_name")
                        or target_material.get("filename")
                        or ""
                    )
                    details = item.get("details")
                    details_text = ""
                    if isinstance(details, dict):
                        details_text = ", ".join(
                            [
                                f"{k}:{v:.2f}"
                                for k, v in list(details.items())[:12]
                                if isinstance(v, (int, float))
                            ]
                        )
                    w.writerow([similarity, lib_name, target_name, details_text])

            QMessageBox.information(self, "导出成功", f"已导出到：\n{file_path}")
        except Exception as e:
            QMessageBox.warning(self, _('export_failed'), str(e))

    def _fill_results(self, results: List[Dict[str, Any]]):
        """存储所有结果并显示第一页"""
        self._all_results = results
        self._current_page = 0
        self._update_page_display()
    
    def _update_page_display(self):
        """更新分页显示"""
        total = len(self._all_results)
        total_pages = max(1, (total + self._page_size - 1) // self._page_size)
        
        # 更新分页信息
        self.page_label.setText(f"第 {self._current_page + 1}/{total_pages} 页")
        self.page_info_label.setText(f"共 {total} 条结果")
        
        # 更新按钮状态
        self.page_prev_btn.setEnabled(self._current_page > 0)
        self.page_next_btn.setEnabled(self._current_page < total_pages - 1)
        
        # 显示当前页数据
        self._display_page_results()
    
    def _on_prev_page(self):
        """上一页"""
        if self._current_page > 0:
            self._current_page -= 1
            self._update_page_display()
    
    def _on_next_page(self):
        """下一页"""
        total_pages = max(1, (len(self._all_results) + self._page_size - 1) // self._page_size)
        if self._current_page < total_pages - 1:
            self._current_page += 1
            self._update_page_display()
    
    def _display_page_results(self):
        """显示当前页的结果"""
        start_idx = self._current_page * self._page_size
        end_idx = min(start_idx + self._page_size, len(self._all_results))
        rows = self._all_results[start_idx:end_idx]
        
        self.results_table.setSortingEnabled(False)
        self.results_table.setRowCount(len(rows))
        
        # 相似度分数是 0-100 范围的百分比，需要转换为 0-1 进行显示
        def _to_unit_sim(v: Any) -> float:
            try:
                x = float(v)
            except Exception:
                return 0.0
            if x <= 1.0:
                return max(0.0, min(1.0, x))
            return max(0.0, min(1.0, x / 100.0))

        for r, item in enumerate(rows):
            raw_similarity = item.get("similarity", 0.0)
            similarity = _to_unit_sim(raw_similarity)
            lib_name = item.get("library_name", "")
            target_material = item.get("target_material") or item.get("material") or {}
            target_name = (
                target_material.get("name")
                or target_material.get("file_name")
                or target_material.get("filename")
                or ""
            )

            sim_item = QTableWidgetItem(f"{similarity * 100.0:.1f}%")
            sim_item.setData(Qt.UserRole, float(similarity))
            name_item = QTableWidgetItem(str(target_name))
            lib_item = QTableWidgetItem(str(lib_name))

            details = item.get("details")
            details_text = ""
            if isinstance(details, dict):
                source_sampler_count = details.get("source_sampler_count", 0)
                target_sampler_count = details.get("target_sampler_count", 0)
                source_param_count = details.get("source_param_count", 0)
                target_param_count = details.get("target_param_count", 0)
                
                score_items = []
                
                if "material_keywords" in details:
                    score = details["material_keywords"]
                    if isinstance(score, (int, float)):
                        score_items.append(f"材质关键词:{score:.0f}%")
                
                if "sampler_count" in details:
                    score = details["sampler_count"]
                    if isinstance(score, (int, float)):
                        score_items.append(
                            f"采样器: {source_sampler_count}(源)→{target_sampler_count}个 "
                            f"(相似度{score:.0f}%)"
                        )
                
                if "sampler_types" in details:
                    score = details["sampler_types"]
                    if isinstance(score, (int, float)):
                        score_items.append(f"采样器类型:{score:.0f}%")
                
                if "parameters" in details:
                    score = details["parameters"]
                    if isinstance(score, (int, float)):
                        score_items.append(
                            f"参数: {source_param_count}(源)→{target_param_count}个 "
                            f"(相似度{score:.0f}%)"
                        )
                
                if "shader_path" in details:
                    score = details["shader_path"]
                    if isinstance(score, (int, float)):
                        score_items.append(f"Shader路径:{score:.0f}%")
                
                if "sampler_paths" in details:
                    score = details["sampler_paths"]
                    if isinstance(score, (int, float)):
                        score_items.append(f"采样器路径:{score:.0f}%")
                
                details_text = ", ".join(score_items)
            detail_item = QTableWidgetItem(details_text)

            self.results_table.setItem(r, 0, sim_item)
            self.results_table.setItem(r, 1, name_item)
            self.results_table.setItem(r, 2, lib_item)
            self.results_table.setItem(r, 3, detail_item)

        self.results_table.setSortingEnabled(True)
        self.results_table.resizeColumnsToContents()

    def _copy_cell_text(self, row: int, column: int):
        item = self.results_table.item(row, column)
        if not item:
            return
        text = item.text()
        if not text:
            return
        QApplication.clipboard().setText(text)
        self.progress_label.setText(f"已复制：{text}")

    def _on_result_clicked(self, row: int, column: int):
        """点击搜索结果时，在主界面中选中该材质"""
        # 计算实际索引（考虑分页偏移）
        actual_idx = self._current_page * self._page_size + row
        if actual_idx < 0 or actual_idx >= len(self._all_results):
            return
        
        result = self._all_results[actual_idx]
        
        # 从嵌套的 target_material 中获取名称和 ID
        target_material = result.get("target_material") or result.get("material") or {}
        target_name = (
            target_material.get("name")
            or target_material.get("file_name")
            or target_material.get("filename")
            or ""
        )
        target_id = target_material.get("id")
        target_lib_id = result.get("target_library_id")
        
        if not target_name or not target_id:
            return
        
        # 获取父窗口（主窗口）
        main_window = self.parent()
        if not main_window or not hasattr(main_window, 'select_material_by_id'):
            return
        
        try:
            # 使用新的选中方法：会自动切换库、加载列表、选中材质
            main_window.select_material_by_id(target_id, target_lib_id)
            self.progress_label.setText(f"已切换到：{target_name}")
        except Exception as e:
            self.progress_label.setText(f"切换失败：{str(e)}")

