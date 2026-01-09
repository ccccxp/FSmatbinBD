from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame,
    QHBoxLayout, QPushButton, QLineEdit, QMessageBox,
    QGroupBox, QCheckBox, QGridLayout, QComboBox,
    QSpinBox, QDoubleSpinBox, QSizePolicy, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal, QRect, QSize, QEvent
from PySide6.QtWidgets import QLayout, QWidgetItem
from PySide6.QtGui import QCursor, QIcon
import json

from src.core.i18n import _
from src.utils.resource_path import get_assets_path
from .sampler_panel import SamplerPanel
from .models import SamplerTableModel
from .smooth_scroll import SmoothScrollArea
from .color_picker_dialog import ColorPreviewWidget, GradientPreviewWidget, ColorPickerDialog, GradientEditorDialog


class FocusWheelSpinBox(QSpinBox):
    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()

class FocusWheelDoubleSpinBox(QDoubleSpinBox):
    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class MaterialEditorPanel(QWidget):
    """材质编辑面板 - 卡片式参数编辑,对齐原Tkinter功能"""
    saveRequested = Signal(dict)
    exportRequested = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_detail: Optional[Dict[str, Any]] = None
        self._param_cards = {}
        self._param_list: List[Dict[str, Any]] = []
        self._param_groups: dict[str, dict] = {}

        # 参数显示/筛选状态
        self._show_type = True
        self._show_key = True
        # 默认隐藏“参数名称”编辑行：标题已展示参数名，除非用户主动开启
        self._show_name_edit = False
        self._use_grouping = True
        self._selected_group = _('all_params')
        self._search_text = ""
        self._params_cols = 3
        self._build_ui()

        # 双击复制：注册表（用 eventFilter 统一处理）
        self._dblclick_copy_widgets = set()

    def eventFilter(self, watched, event):
        try:
            if watched in getattr(self, "_dblclick_copy_widgets", set()):
                if event.type() == QEvent.MouseButtonDblClick:
                    from PySide6.QtWidgets import QApplication
                    text = ""
                    try:
                        text = str(getattr(watched, "text", lambda: "")())
                    except Exception:
                        text = ""
                    if text:
                        QApplication.clipboard().setText(text)
                    event.accept()
                    return True
        except Exception:
            pass
        return super().eventFilter(watched, event)

    def _enable_dblclick_copy(self, widget: QWidget):
        """为任意只读显示控件启用“双击复制”。"""
        try:
            widget.setCursor(QCursor(Qt.IBeamCursor))
        except Exception:
            pass
        try:
            widget.installEventFilter(self)
            self._dblclick_copy_widgets.add(widget)
        except Exception:
            pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 自适应列数：随右侧面板宽度变化重新排布，避免右侧空白
        self._update_params_columns()

    def _update_params_columns(self):
        # 以滚动区域 viewport 宽度为准（更贴近真实可用宽度，避免右侧空白）
        container_w = None
        if hasattr(self, 'params_scroll') and self.params_scroll is not None:
            try:
                container_w = int(self.params_scroll.viewport().width())
            except Exception:
                container_w = None
        if not container_w:
            container_w = self.params_grid_widget.width() if hasattr(self, 'params_grid_widget') else self.width()
        if container_w <= 0:
            return

        # 估算卡片最小宽度：标题+两列内容，需要更宽一些
        # 说明：过大将导致“右侧空一大片”，过小又会让卡片内容挤压。
        # 这里取一个偏保守的值，并留出 spacing 的余量。
        min_card_w = 320
        cols = max(1, min(4, int(max(1, container_w) / min_card_w)))
        if cols != getattr(self, '_params_cols', 3):
            self._params_cols = cols
            self._rebuild_params_view()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = self._create_header()
        layout.addWidget(header)

        scroll = SmoothScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        # 添加透明背景和滚动条样式
        scroll.setStyleSheet("""
            SmoothScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: rgba(11, 16, 32, 200);
                width: 10px;
                border-radius: 5px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(43, 50, 80, 200);
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(47, 129, 247, 200);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)
        
        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content_widget)
        # 更贴顶：减小顶部边距，让“基本参数”更靠近标题条
        content_layout.setContentsMargins(12, 6, 12, 12)
        content_layout.setSpacing(10)

        self.basic_info_widget = self._create_compact_basic_info()
        self.basic_info_widget.setMaximumHeight(120)
        content_layout.addWidget(self.basic_info_widget)

        self.params_container = self._create_params_container()
        content_layout.addWidget(self.params_container, 1)  # stretch=1 让参数区域占主要空间

        self.sampler_panel = SamplerPanel()
        self.sampler_model = SamplerTableModel()
        self.sampler_panel.set_model(self.sampler_model)
        content_layout.addWidget(self.sampler_panel)

        scroll.setWidget(content_widget)
        layout.addWidget(scroll, 1)

        self.empty_label = QLabel(_('select_material_detail_hint'))
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #9ca9c5; font-size: 13px;")
        layout.addWidget(self.empty_label)

        self.basic_info_widget.hide()
        self.params_container.hide()
        self.sampler_panel.hide()

    def _glass_input_qss(self) -> str:
        """统一的“玻璃拟态输入控件”样式。

        目标：减少硬边框、增加轻微高光与 focus glow，让 QLineEdit/QComboBox/SpinBox
        在深色主题下更通透。
        """
        return (
            "background: rgba(0, 0, 0, 35);"
            "border: 1px solid rgba(255, 255, 255, 26);"
            "border-radius: 8px;"
            "padding: 4px 10px;"
            "color: #f5f7ff;"
        )

    def _glass_input_qss_focus(self) -> str:
        return (
            # 恢复亮蓝 focus 体系
            "border: 1px solid rgba(47, 129, 247, 190);"
            "background: rgba(47, 129, 247, 18);"
        )

    def _ui_tokens(self) -> dict:
        """局部 UI 设计 token，尽量贴近你给的参考图（深色卡片 + 细描边 + 柔阴影 + 嵌入式控件）。"""
        return {
            "card_radius": 18,
            "inner_radius": 14,
            "control_radius": 12,
            "card_bg_1": "rgba(22, 30, 46, 235)",
            "card_bg_2": "rgba(12, 16, 28, 235)",
            "card_border": "rgba(255,255,255,14)",
            # hover 边框更亮一点，作为“重点色提示”
            "card_border_hover": "rgba(47, 129, 247, 120)",
            "shadow": "rgba(0,0,0,160)",
            # Accent / emphasis
            # 亮蓝方案（与全局 palette 对齐）
            "accent": "#2F81F7",
            "accent_soft": "rgba(47, 129, 247, 38)",
            "accent_border": "rgba(47, 129, 247, 170)",

            # Typography colors
            "title": "#F5F8FF",
            "muted": "rgba(190,200,220,175)",
            "label": "rgba(221,230,255,235)",
            "value": "rgba(245,248,255,235)",
            "key": "rgba(165,175,205,155)",
            "control_bg": "rgba(10, 14, 24, 160)",
            # 控件边框：统一为“淡蓝细边框”（和顶部搜索栏一致的观感）
            "control_border": "rgba(110, 165, 255, 90)",
            "control_border_hover": "rgba(140, 190, 255, 130)",
            "focus": "rgba(47, 129, 247, 210)",
            "focus_fill": "rgba(47, 129, 247, 24)",
        }

    def _card_shadow(self, widget: QWidget, blur: int = 34, y: int = 14):
        t = self._ui_tokens()
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(blur)
        shadow.setOffset(0, y)
        # 用更柔和的阴影，避免边缘“发灰/发白”
        shadow.setColor(Qt.black)
        widget.setGraphicsEffect(shadow)

        # 记录默认值，供 hover 动态调整
        widget._shadow_default_blur = blur
        widget._shadow_default_y = y
        widget._shadow_effect = shadow

    def _set_card_shadow_state(self, widget: QWidget, *, hovered: bool):
        """卡片 hover 交互：调整阴影强度/偏移，形成轻微“浮起”感。"""
        try:
            shadow = getattr(widget, "_shadow_effect", None)
            if shadow is None:
                return
            blur0 = int(getattr(widget, "_shadow_default_blur", 34))
            y0 = int(getattr(widget, "_shadow_default_y", 14))

            if hovered:
                shadow.setBlurRadius(max(blur0, 34) + 12)
                shadow.setOffset(0, y0 + 4)
            else:
                shadow.setBlurRadius(blur0)
                shadow.setOffset(0, y0)
        except Exception:
            pass

    def _card_container_qss(self) -> str:
        t = self._ui_tokens()
        r = t["card_radius"]
        return (
            # 只作用于大区块卡片，避免误伤其它 QFrame（例如标题栏里的分隔线/各种容器）
            "QFrame#SectionCard {"
            f"background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {t['card_bg_1']}, stop:1 {t['card_bg_2']});"
            # 大卡片边框压暗，避免出现白色细框
            f"border: 1px solid rgba(255,255,255,8);"
            f"border-radius: {r}px;"
            "}"
        )

    def _card_inner_qss(self) -> str:
        t = self._ui_tokens()
        r = t["inner_radius"]
        return (
            "QFrame {"
            # 让参数卡片更“黑底”，并且边框更暗，避免出现大量白色细线
            f"background: rgba(7, 10, 18, 210);"
            f"border: 1px solid rgba(255,255,255,6);"
            f"border-radius: {r}px;"
            "}"
            # hover 只做轻微强调，不要太亮
            f"QFrame:hover {{ border-color: rgba(47, 129, 247, 90); }}"
        )

    def _card_title_qss(self) -> str:
        t = self._ui_tokens()
        # 标题要更像组件库：大一点、更亮、字重更高
        return f"font-weight: 850; font-size: 12.5pt; color: {t['title']}; letter-spacing: 0.2px;"

    def _card_subtitle_qss(self) -> str:
        t = self._ui_tokens()
        return f"color: {t['muted']}; font-size: 9pt;"

    def _field_label_qss(self) -> str:
        t = self._ui_tokens()
        # 参考图里的 label 更像小标题：偏亮、字重中等
        return f"color: {t['label']}; font-size: 9.2pt; font-weight: 750;"

    def _field_value_qss(self) -> str:
        t = self._ui_tokens()
        return f"color: {t['value']}; font-size: 9pt; font-weight: 550;"

    def _field_key_qss(self) -> str:
        t = self._ui_tokens()
        return f"color: {t['key']}; font-size: 8.8pt; font-weight: 500;"

    def _accent_bar_qss(self) -> str:
        """字段名左侧的重点色竖条（让 label/value 更易区分）。"""
        t = self._ui_tokens()
        return (
            "QFrame {"
            f"background: {t['accent']};"
            "border-radius: 2px;"
            "}"
        )

    def _control_qss(self) -> str:
        t = self._ui_tokens()
        r = t["control_radius"]
        return (
            # 更顺滑的“玻璃质感”背景（轻微渐变 + 顶部高光），降低边框噪点感
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            " stop:0 rgba(14, 18, 30, 185),"
            " stop:1 rgba(8, 10, 18, 150));"
            # 默认边框更柔和
            f"border: 1px solid {t['control_border']};"
            f"border-radius: {r}px;"
            "padding: 5px 10px;"
            f"color: {t['value']};"
        )

    def _control_state_qss(self) -> str:
        t = self._ui_tokens()
        return (
            # hover：边框更亮一些 + 背景略提亮
            f":hover {{ border-color: {t['control_border_hover']}; background: rgba(47, 129, 247, 14); }}"
            # focus：更强的亮蓝边框与填充
            f":focus {{ border-color: {t['focus']}; background: {t['focus_fill']}; }}"
        )

    def _combobox_full_qss(self) -> str:
        """完整的深色主题 ComboBox 样式（包含下拉列表）"""
        t = self._ui_tokens()
        r = t["control_radius"]
        return f"""
            QComboBox {{
                background: {t['control_bg']};
                border: 1px solid {t['control_border']};
                border-radius: {r}px;
                padding: 5px 10px;
                padding-right: 24px;
                color: {t['value']};
                font-size: 9pt;
            }}
            QComboBox:hover {{
                border-color: {t['control_border_hover']};
            }}
            QComboBox:focus {{
                border-color: {t['focus']};
                background: {t['focus_fill']};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 20px;
                border: none;
            }}
            QComboBox::down-arrow {{
                width: 12px;
                height: 12px;
                image: url(src/gui_qt/assets/combo_arrow_down.svg);
            }}
            QComboBox::down-arrow:hover {{
                image: url(src/gui_qt/assets/combo_arrow_down.svg);
            }}
            QComboBox QAbstractItemView {{
                background: rgba(20, 26, 40, 250);
                border: 1px solid {t['control_border']};
                border-radius: 8px;
                selection-background-color: {t['accent']};
                selection-color: #ffffff;
                outline: none;
                padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{
                height: 26px;
                padding: 4px 10px;
                border-radius: 4px;
                color: rgba(220, 230, 250, 220);
            }}
            QComboBox QAbstractItemView::item:hover {{
                background: rgba(255, 255, 255, 15);
            }}
            QComboBox QAbstractItemView::item:selected {{
                background: {t['accent']};
                color: #ffffff;
            }}
        """

    # --- Unified card system (modern dark cards like reference) ---
    def _section_card_qss(self) -> str:
        return self._card_container_qss()

    def _param_card_qss(self) -> str:
        # 参数卡片 hover 交互：边框高亮 + 背景轻微提亮 + 产生“浮起”视觉
        t = self._ui_tokens()
        r = t["inner_radius"]
        return (
            # 外层 wrapper 透明（只负责阴影）
            "QFrame#ParamCard { background: transparent; border: none; }"

            # 内层 surface 承载真实圆角
            "QFrame#ParamCardSurface {"
            "background: rgba(7, 10, 18, 210);"
            # 默认边框更暗更细
            "border: 1px solid rgba(255,255,255,7);"
            f"border-radius: {r}px;"
            "}"
            "QFrame#ParamCardSurface:hover {"
            # 边框高亮：加粗 + 更亮（Qt QSS 不稳定支持 box-shadow，这里用最稳的方式）
            f"border: 2px solid rgba(140, 190, 255, 210);"
            # 背景轻微提亮（避免太亮导致“发灰/发白”）
            "background: rgba(10, 14, 24, 225);"
            "}"
        )

    def _create_header(self) -> QFrame:
        header = QFrame()
        header_layout = QVBoxLayout(header)
        # 顶部标题条：更紧凑（不降低字体大小，只压缩上下边距/控件高度）
        header_layout.setContentsMargins(12, 6, 12, 6)
        header_layout.setSpacing(4)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        
        self.title_label = QLabel(_('material_details'))  # 材质详情
        self.title_label.setStyleSheet("font-weight:600; font-size:14px;")
        title_row.addWidget(self.title_label, 1)

        self.autopack_check = QCheckBox(_('add_to_autopack'))
        # 修复：复选框不明显（深色背景下提升对比度与可点击感）
        t = self._ui_tokens()
        self.autopack_check.setStyleSheet(
            f"QCheckBox {{ color: {t['label']}; font-size: 9.5pt; spacing: 8px; }}"
            "QCheckBox::indicator {"
            " width: 16px; height: 16px; border-radius: 4px;"
            " border: 1px solid rgba(255,255,255,70);"
            " background: rgba(0,0,0,28);"
            "}"
            "QCheckBox::indicator:hover { border-color: rgba(255,255,255,120); }"
            "QCheckBox::indicator:checked {"
            f" background: {t['accent']}; border: 1px solid {t['accent_border']};"
            " image: url(src/gui_qt/assets/checkbox_check_white.svg);"
            "}"
            "QCheckBox::indicator:checked:hover {"
            f" border: 1px solid {t['accent']};"
            "}"
        )
        title_row.addWidget(self.autopack_check)

        self.save_btn = QPushButton(_('save'))
        self.save_btn.setObjectName("primary")
        self.save_btn.setFixedHeight(26)
        self.save_btn.clicked.connect(self._on_save_clicked)
        title_row.addWidget(self.save_btn)



        header_layout.addLayout(title_row)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        # 用更暗的分隔线，避免看起来像白色边框
        separator.setStyleSheet("background-color: rgba(70, 90, 130, 90);")
        separator.setFixedHeight(1)
        header_layout.addWidget(separator)

        return header

    def _create_compact_basic_info(self) -> QFrame:
        # 外层大卡片（统一风格）
        card = QFrame()
        card.setObjectName("SectionCard")
        card.setStyleSheet(self._section_card_qss())

        self._card_shadow(card, blur=36, y=14)

        layout = QVBoxLayout(card)
        # 更贴顶、更紧凑（不降低字体大小）
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(5)

        self.basic_info_title = QLabel(_('basic_info'))
        self.basic_info_title.setStyleSheet(self._card_title_qss() + "background: transparent;")
        layout.addWidget(self.basic_info_title)

        # 两行布局：
        # 1) 名称 + Shader（Shader 更宽，路径通常很长）
        # 2) 路径 / 压缩 / Key
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(5)

        self.info_labels = {}
        self.field_label_widgets = {}  # Store references to field labels for i18n refresh

        def add_field(row: int, label_col: int, value_col: int, field: str, label_text: str):
            # label：与可编辑参数卡片的“类型/Key”一致（左侧蓝条 + 透明背景）
            label_w = QWidget()
            label_w.setAutoFillBackground(False)
            label_w.setAttribute(Qt.WA_StyledBackground, True)
            label_w.setStyleSheet("background: transparent; border: none;")
            label_l = QHBoxLayout(label_w)
            label_l.setContentsMargins(0, 0, 0, 0)
            label_l.setSpacing(6)

            bar = QFrame()
            bar.setFixedWidth(3)
            bar.setFixedHeight(11)
            bar.setStyleSheet(self._accent_bar_qss())
            label_l.addWidget(bar)

            label = QLabel(label_text)
            label.setStyleSheet(self._field_label_qss() + "background: transparent;")
            label_l.addWidget(label)
            label_l.addStretch()

            grid.addWidget(label_w, row, label_col)
            # Store label reference for i18n refresh
            self.field_label_widgets[field] = label

            # 值：改成只读输入框风格（和可编辑参数里的控件一致的淡蓝边框）
            value_edit = QLineEdit("-")
            value_edit.setReadOnly(True)
            value_edit.setFrame(False)
            value_edit.setCursor(QCursor(Qt.IBeamCursor))
            value_edit.setStyleSheet(
                "QLineEdit { font-size: 9pt; " + self._control_qss() + " }"
                + "QLineEdit" + self._control_state_qss()
            )

            # 双击复制到剪贴板（eventFilter 方式更稳定）
            self._enable_dblclick_copy(value_edit)

            grid.addWidget(value_edit, row, value_col)
            self.info_labels[field] = value_edit

        # 第一行
        add_field(0, 0, 1, 'filename', _('filename'))
        add_field(0, 2, 3, 'shader_path', _('shader_path'))
        # 第二行
        add_field(1, 0, 1, 'source_path', _('file_path'))
        add_field(1, 2, 3, 'compression', _('compression_type'))
        add_field(1, 4, 5, 'key_value', _('key_value'))

        # stretch：让 Shader/路径列更宽
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 3)
        grid.setColumnStretch(5, 1)

        # 让 Key 这一对更紧凑一些
        grid.setColumnMinimumWidth(4, 36)

        layout.addLayout(grid)
        return card

    def _create_params_container(self) -> QFrame:
        # 外层大卡片（统一风格）
        container = QFrame()
        container.setObjectName("SectionCard")
        container.setStyleSheet(self._section_card_qss())

        self._card_shadow(container, blur=36, y=14)

        layout = QVBoxLayout(container)
        # 压缩顶部区域：标题/提示/功能控件同一行
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        self.editable_params_title = QLabel(_('editable_params'))
        self.editable_params_title.setStyleSheet(self._card_title_qss() + "background: transparent;")
        header_row.addWidget(self.editable_params_title)

        self.editor_hint_label = QLabel(_('editor_hint'))
        self.editor_hint_label.setStyleSheet(self._card_subtitle_qss() + "background: transparent;")
        header_row.addWidget(self.editor_hint_label, 1)

        # 显示栏目（多选下拉，用 QToolButton + QMenu）
        from PySide6.QtWidgets import QToolButton, QMenu

        self.display_btn = QToolButton()
        self.display_btn.setText(_('content'))
        # 强制显示“图标 + 文本”，避免某些平台/主题下只剩图标导致文字看似消失
        try:
            from PySide6.QtCore import Qt as _Qt
            self.display_btn.setToolButtonStyle(_Qt.ToolButtonTextBesideIcon)
        except Exception:
            pass
        self.display_btn.setAutoRaise(True)
        # 与右侧“全部”下拉框统一高度
        self.display_btn.setFixedHeight(24)
        # 使用 SVG 图标，避免字体/Unicode 在不同环境下显示为方块
        self.display_btn.setIcon(QIcon(get_assets_path("chevron_right.svg")))
        self.display_btn.setIconSize(QSize(14, 14))
        self.display_btn.setPopupMode(QToolButton.InstantPopup)
        btn_qss = self._control_qss()
        btn_states = self._control_state_qss()
        self.display_btn.setStyleSheet(
            "QToolButton {"
            "font-size: 9pt;"
            + btn_qss +
            # QToolButton 的文字颜色需要显式指定（不然可能继承成非常暗的颜色）
            f"color: {self._ui_tokens()['value']};"
            "text-align: left;"
            # 让边框高度体感与 QComboBox 一致
            "padding-top: 5px; padding-bottom: 5px;"
            "padding-right: 10px;"
            "}"
            # 不显示 QToolButton 自带的 menu-indicator，小三角会叠在图标/文字上
            "QToolButton::menu-indicator { image: none; width: 0px; }"
            + "QToolButton" + btn_states
        )
        menu = QMenu(self.display_btn)

        self.action_show_type = menu.addAction(_('editor_show_type'))
        self.action_show_type.setCheckable(True)
        self.action_show_type.setChecked(True)

        self.action_show_key = menu.addAction(_('editor_show_key'))
        self.action_show_key.setCheckable(True)
        self.action_show_key.setChecked(True)

        self.action_show_name_edit = menu.addAction(_('editor_show_name_edit'))
        self.action_show_name_edit.setCheckable(True)
        self.action_show_name_edit.setChecked(False)

        menu.addSeparator()

        self.action_grouping = menu.addAction(_('editor_group_by_type'))
        self.action_grouping.setCheckable(True)
        self.action_grouping.setChecked(True)

        self.display_btn.setMenu(menu)
        self.action_show_type.toggled.connect(self._on_display_options_changed)
        self.action_show_key.toggled.connect(self._on_display_options_changed)
        self.action_show_name_edit.toggled.connect(self._on_display_options_changed)
        self.action_grouping.toggled.connect(self._on_display_options_changed)
        header_row.addWidget(self.display_btn)

        # 分组筛选
        self.group_combo = QComboBox()
        self.group_combo.addItems([_('all_params')])  # 在 load_params 后刷新
        self.group_combo.setFixedHeight(24)
        self.group_combo.setMinimumWidth(110)
        self.group_combo.setStyleSheet(self._combobox_full_qss())
        self.group_combo.currentTextChanged.connect(self._on_group_changed)
        header_row.addWidget(self.group_combo)

        # 搜索
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(_('search_params_placeholder'))
        self.search_edit.setFixedHeight(26)
        self.search_edit.setMinimumWidth(160)
        self.search_edit.setStyleSheet(
            "QLineEdit { font-size: 9pt; " + self._control_qss() + " }"
            + "QLineEdit" + self._control_state_qss()
        )
        self.search_edit.textChanged.connect(self._on_search_changed)
        header_row.addWidget(self.search_edit)

        # 展开/折叠
        self.expand_all_btn = QPushButton(_('expand_all'))
        self.expand_all_btn.setFixedHeight(26)
        self.expand_all_btn.setStyleSheet(
            "QPushButton { font-size: 9pt; " + self._control_qss() + " }"
            + "QPushButton" + self._control_state_qss()
        )
        self.expand_all_btn.clicked.connect(lambda: self._set_all_groups_collapsed(False))
        header_row.addWidget(self.expand_all_btn)

        self.collapse_all_btn = QPushButton(_('collapse_all'))
        self.collapse_all_btn.setFixedHeight(26)
        self.collapse_all_btn.setStyleSheet(
            "QPushButton { font-size: 9pt; " + self._control_qss() + " }"
            + "QPushButton" + self._control_state_qss()
        )
        self.collapse_all_btn.clicked.connect(lambda: self._set_all_groups_collapsed(True))
        header_row.addWidget(self.collapse_all_btn)

        layout.addLayout(header_row)

        scroll = SmoothScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMinimumHeight(200)  # 确保参数区域有足够显示空间
        # 添加透明背景和滚动条样式
        scroll.setStyleSheet("""
            SmoothScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: rgba(11, 16, 32, 200);
                width: 10px;
                border-radius: 5px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(43, 50, 80, 200);
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(47, 129, 247, 200);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)

        # 保存引用：用于 resize 时取 viewport 宽度计算列数
        self.params_scroll = scroll
        
        self.params_grid_widget = QWidget()
        self.params_grid_widget.setStyleSheet("background: transparent;")
        self.params_grid = QGridLayout(self.params_grid_widget)
        # 卡片之间留出更明显的间距，避免边框在视觉上“连成一片”
        self.params_grid.setSpacing(16)
        self.params_grid.setContentsMargins(0, 0, 0, 0)
        # 关键：让分组/卡片顶部对齐而不是拉伸占满整个高度
        self.params_grid.setAlignment(Qt.AlignTop)
        
        scroll.setWidget(self.params_grid_widget)
        layout.addWidget(scroll, 1)

        return container

    def _on_display_options_changed(self):
        self._show_type = self.action_show_type.isChecked()
        self._show_key = self.action_show_key.isChecked()
        self._show_name_edit = self.action_show_name_edit.isChecked()
        self._use_grouping = self.action_grouping.isChecked()

        # 当用户只想看“必要的名称和对应的值”时，建议：关掉 type/key/name_edit
        self._rebuild_params_view()

    def _on_group_changed(self, text: str):
        self._selected_group = text
        self._rebuild_params_view()

    def _on_search_changed(self, text: str):
        self._search_text = (text or "").strip().lower()
        self._rebuild_params_view()

    def _set_all_groups_collapsed(self, collapsed: bool):
        for grp in self._param_groups.values():
            content = grp.get('content')
            btn = grp.get('toggle')
            if content is None or btn is None:
                continue
            content.setVisible(not collapsed)
            btn.setChecked(not collapsed)
            btn.setIcon(QIcon(get_assets_path("chevron_down.svg") if not collapsed else get_assets_path("chevron_right.svg")))

    def _rebuild_params_view(self):
        # 使用当前缓存的参数重新渲染（支持搜索/分组/显示栏目切换）
        if not self._param_list:
            return
        self._load_params(self._param_list)

    def _create_param_card(self, index: int, param: Dict[str, Any]) -> QFrame:
        # 外层 wrapper：只负责阴影与为圆角留空间（避免阴影/子布局把下圆角“切直”）
        card = QFrame()
        card.setObjectName("ParamCard")
        card.setAttribute(Qt.WA_StyledBackground, False)
        card.setStyleSheet("QFrame#ParamCard { background: transparent; border: none; }")
        # 给阴影留空间：否则 QGraphicsDropShadowEffect 在某些平台下会被布局边界裁切
        outer_layout = QVBoxLayout(card)
        outer_layout.setContentsMargins(6, 6, 6, 10)
        outer_layout.setSpacing(0)


        self._card_shadow(card, blur=26, y=10)

        # hover 时增强阴影，获得“卡片浮起”效果
        def _enter_event(e):
            self._set_card_shadow_state(card, hovered=True)
            e.accept()

        def _leave_event(e):
            self._set_card_shadow_state(card, hovered=False)
            e.accept()

        card.enterEvent = _enter_event
        card.leaveEvent = _leave_event

        # 内层 surface：承载真实背景/边框/圆角
        surface = QFrame()
        surface.setObjectName("ParamCardSurface")
        surface.setAttribute(Qt.WA_StyledBackground, True)
        surface.setAttribute(Qt.WA_Hover, True)
        surface.setMouseTracking(True)
        # 复用现有 ParamCard QSS（里面的选择器仍是 #ParamCard，所以这里直接写同款）
        t = self._ui_tokens()
        r = t["inner_radius"]
        surface.setStyleSheet(
            "QFrame#ParamCardSurface {"
            "background: rgba(7, 10, 18, 210);"
            "border: 1px solid rgba(255,255,255,6);"
            f"border-radius: {r}px;"
            "}"
        )
        outer_layout.addWidget(surface)

        card.setMouseTracking(True)

        layout = QVBoxLayout(surface)
        # 更紧凑：让一屏能容纳更多参数卡，但保持卡片内留白
        layout.setContentsMargins(10, 8, 10, 9)
        layout.setSpacing(6)

        param_name = param.get('name', _('param_default_name').format(index+1))
        param_type = param.get('type', 'Float')
        param_value = param.get('value', '')
        param_key = param.get('key_value', '')

        # 参数标题：更醒目（重点色 + 更高字重），并与内容区拉开层级
        title_row = QHBoxLayout()
        title_row.setSpacing(6)

        accent = QFrame()
        accent.setFixedWidth(4)
        accent.setFixedHeight(14)
        accent.setStyleSheet(self._accent_bar_qss())
        title_row.addWidget(accent)

        title = QLabel(param_name)
        title.setStyleSheet(
            f"font-weight: 850; font-size: 9.8pt; color: {self._ui_tokens()['title']};"
        )
        title.setWordWrap(True)
        title.setToolTip(param_name)
        title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        title_row.addWidget(title, 1)

        layout.addLayout(title_row)

        # 控件样式：卡片体系里更克制（弱边框、轻 hover、focus 高亮）
        control_qss = self._control_qss()
        control_states = self._control_state_qss()

        # 参数内容区：类型+Key 同行两列；参数内容独立一行
        content_grid = QGridLayout()
        content_grid.setContentsMargins(0, 0, 0, 0)
        content_grid.setHorizontalSpacing(8)
        content_grid.setVerticalSpacing(6)

        # 4 列：label/value | label/value
        # 默认两侧均衡，后续会根据 Key 是否为空/是否很长做动态调整
        content_grid.setColumnStretch(1, 2)
        content_grid.setColumnStretch(3, 2)

        label_style = self._field_label_qss()
        key_label_style = self._field_key_qss()
        row = 0

        def add_label_with_accent(text: str, *, weak: bool = False) -> QWidget:
            """左侧字段名：accent 竖条 + label，让字段名与右侧输入区区别更明显。"""
            w = QWidget()
            l = QHBoxLayout(w)
            l.setContentsMargins(0, 0, 0, 0)
            l.setSpacing(6)

            bar = QFrame()
            bar.setFixedWidth(3)
            bar.setFixedHeight(11)
            if weak:
                t = self._ui_tokens()
                bar.setStyleSheet(
                    f"QFrame {{ background: {t['accent_soft']}; border-radius: 2px; }}"
                )
            else:
                bar.setStyleSheet(self._accent_bar_qss())
            l.addWidget(bar)

            lab = QLabel(text)
            lab.setStyleSheet(key_label_style if weak else label_style)
            lab.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            l.addWidget(lab)
            l.addStretch()
            return w

        # 行：类型 + Key（同一行两列）
        type_label = add_label_with_accent(_('type_label'))
        type_combo = QComboBox()
        type_combo.addItems(['Float', 'Float2', 'Float3', 'Float4', 'Float5', 'Int', 'Int2', 'Bool'])
        type_combo.setCurrentText(param_type)
        type_combo.setStyleSheet(self._combobox_full_qss())
        type_combo.setMinimumHeight(22)
        type_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        type_combo.currentTextChanged.connect(lambda t: self._on_param_type_changed(index, t))

        key_label = add_label_with_accent("Key", weak=True)
        key_edit = QLineEdit(str(param_key))
        key_edit.setReadOnly(True)
        key_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        key_edit.setMinimumWidth(60)
        # 长文本允许水平滚动/选择复制
        try:
            key_edit.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        except Exception:
            pass
        key_edit.setCursorPosition(0)
        key_edit.setStyleSheet(
            "QLineEdit { font-size:8.8pt; "
            + control_qss
            + " color: "
            + self._ui_tokens()["key"]
            + "; }"
            + "QLineEdit"
            + control_states
        )
        key_edit.setMinimumHeight(22)
        key_edit.setToolTip(str(param_key))
        self._enable_dblclick_copy(key_edit)

        # --- Key 自适应策略 ---
        key_text = str(param_key) if param_key is not None else ""
        key_text = key_text.strip()
        key_is_empty = (key_text == "" or key_text.lower() == "none")

        # 空值：隐藏 Key 区域，让“类型”占满一行（更紧凑）
        if key_is_empty:
            key_label.setVisible(False)
            key_edit.setVisible(False)
            content_grid.setColumnStretch(1, 4)
            content_grid.setColumnStretch(3, 0)
        else:
            # 非空：根据长度倾斜布局
            # 说明：key 通常是数字/短字符串，但有时会很长；这里让右侧列更“贪婪”
            if len(key_text) >= 10:
                content_grid.setColumnStretch(1, 2)
                content_grid.setColumnStretch(3, 4)

            # 超长：提高卡片最小宽度（触发整体变宽），尽量完整显示
            if len(key_text) >= 14:
                # 简单估算：每个字符约 7px，再加上控件内边距与两列间距
                est = 320 + (len(key_text) - 14) * 7
                card.setMinimumWidth(min(max(est, 360), 560))

        # 仅当两者其一需要显示时才占一行
        if self._show_type or self._show_key:
            if self._show_type:
                content_grid.addWidget(type_label, row, 0)
                content_grid.addWidget(type_combo, row, 1)
            else:
                content_grid.addWidget(QWidget(), row, 0)
                content_grid.addWidget(QWidget(), row, 1)

            # Key 显示遵循：全局开关 + 非空策略
            if self._show_key and (not key_is_empty):
                content_grid.addWidget(key_label, row, 2)
                content_grid.addWidget(key_edit, row, 3)
            else:
                content_grid.addWidget(QWidget(), row, 2)
                content_grid.addWidget(QWidget(), row, 3)
            row += 1

        # 行：参数名称（可编辑）
        name_label = add_label_with_accent(_('param_name_label'))

        name_edit = QLineEdit(param_name)
        name_edit.setStyleSheet(
            "QLineEdit { font-size:9pt; " + control_qss + " }"
            + "QLineEdit" + control_states
        )
        name_edit.setMinimumHeight(22)
        name_edit.setToolTip(param_name)

        if self._show_name_edit:
            content_grid.addWidget(name_label, row, 0)
            content_grid.addWidget(name_edit, row, 1, 1, 3)
            row += 1

        # 行：参数内容
        # 行：参数内容
        value_label = add_label_with_accent(_('param_value_content_label'))

        value_container = QWidget()
        value_container.setStyleSheet("background: transparent;")
        value_layout = QVBoxLayout(value_container)
        value_layout.setContentsMargins(0, 0, 0, 0)
        value_layout.setSpacing(0)

        value_widgets = self._create_value_editor(param_type, param_value, param_name)
        value_widgets.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        value_layout.addWidget(value_widgets)

        content_grid.addWidget(value_label, row, 0)
        content_grid.addWidget(value_container, row, 1, 1, 3)

        layout.addLayout(content_grid)

        # 最小高度兜底（数组类型可能换行）
        if str(param_type) in ['Float2', 'Float3', 'Float4', 'Float5', 'Int2']:
            base_h = 124
        else:
            base_h = 112
        card.setMinimumHeight(base_h if (self._show_type or self._show_key or self._show_name_edit) else 96)

        self._param_cards[index] = {
            'card': card,
            'type_combo': type_combo,
            'key_edit': key_edit,
            'name_edit': name_edit,
            'value_container': value_container,
            'value_layout': value_layout,
            'param_data': param
        }

        return card

    def _create_value_editor(self, param_type: str, value: Any, param_name: str = "") -> QWidget:
        container = QWidget()
        # 非数组参数使用简单的 HBoxLayout
        # Float3/4/5/Int2 在下面的分支中设置自己的布局
        if param_type not in ['Float2', 'Float3', 'Float4', 'Float5', 'Int2']:
            layout = QHBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(4)

        if param_type == 'Bool':
            combo = QComboBox()
            combo.addItems(['true', 'false'])
            combo.setCurrentText(str(value).lower() if value else 'false')
            combo.setStyleSheet(self._combobox_full_qss())
            combo.setMinimumHeight(22)
            combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            layout.addWidget(combo, 1)
            container.value_widgets = [combo]
            
        elif param_type in ['Float2', 'Float3', 'Float4', 'Float5', 'Int2']:
            array_values = self._parse_array_value(value, param_type)
            container.value_widgets = []
            
            # 使用水平布局：左侧为数值输入，右侧为预览方块
            main_layout = QHBoxLayout(container)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(8)
            
            # 左侧：数值输入区（使用 FlowLayout 自动换行）
            spin_container = QWidget()
            spin_layout = _FlowLayout(spin_container, margin=0, hSpacing=4, vSpacing=4)
            
            for i, val in enumerate(array_values):
                # 为每个数组元素创建一个水平容器，确保编号和数值紧密关联
                item_widget = QWidget()
                item_layout = QHBoxLayout(item_widget)
                item_layout.setContentsMargins(0, 0, 0, 0)
                item_layout.setSpacing(3)
                
                spin_label = QLabel(f"[{i}]")
                spin_label.setStyleSheet("font-size:9px; color:#6b738c;")
                spin_label.setFixedWidth(18)
                item_layout.addWidget(spin_label)
                
                if 'Int' in param_type:
                    spin = FocusWheelSpinBox()
                    spin.setRange(-999999, 999999)
                    spin.setValue(int(val) if val else 0)
                else:
                    spin = FocusWheelDoubleSpinBox()
                    spin.setRange(-999999.0, 999999.0)
                    spin.setDecimals(6)
                    spin.setValue(float(val) if val else 0.0)
                
                spin.setStyleSheet(
                    "QAbstractSpinBox { font-size:9pt; "
                    + self._control_qss()
                    + " padding-right: 18px; }"
                    + "QAbstractSpinBox"
                    + self._control_state_qss()
                    # up/down 按钮：透明底 + hover 轻提示，避免出现硬分割
                    + "QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {"
                    + "subcontrol-origin: border;"
                    + "width: 18px;"
                    + "border: none;"
                    + "background: transparent;"
                    + "}"
                    + "QAbstractSpinBox::up-button { subcontrol-position: top right; }"
                    + "QAbstractSpinBox::down-button { subcontrol-position: bottom right; }"
                    + "QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover {"
                    + "background: rgba(255,255,255,6);"
                    + "}"
                    + "QAbstractSpinBox::up-button:pressed, QAbstractSpinBox::down-button:pressed {"
                    + "background: rgba(47,129,247,18);"
                    + "}"
                    + "QAbstractSpinBox::up-arrow, QAbstractSpinBox::down-arrow { width: 8px; height: 8px; }"
                )
                spin.setMinimumHeight(22)
                spin.setMinimumWidth(80)
                spin.setMaximumWidth(120)
                spin.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                item_layout.addWidget(spin)
                
                # 将整个 item_widget 添加到 FlowLayout
                item_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                spin_layout.addWidget(item_widget)
                container.value_widgets.append(spin)
            
            spin_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            main_layout.addWidget(spin_container, 1)
            
            # 右侧：颜色/透明度预览控件（较大尺寸，40px）
            preview_widget = self._create_preview_widget(param_type, param_name, container.value_widgets)
            if preview_widget:
                main_layout.addWidget(preview_widget)
                container.preview_widget = preview_widget
                
        else:
            if param_type == 'Int':
                spin = FocusWheelSpinBox()
                spin.setRange(-999999, 999999)
                spin.setValue(int(value) if value else 0)
            else:
                spin = FocusWheelDoubleSpinBox()
                spin.setRange(-999999.0, 999999.0)
                spin.setDecimals(6)
                spin.setValue(float(value) if value else 0.0)
            
            spin.setStyleSheet(
                "QAbstractSpinBox { font-size:9pt; "
                + self._control_qss()
                + " padding-right: 18px; }"
                + "QAbstractSpinBox"
                + self._control_state_qss()
                + "QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {"
                + "subcontrol-origin: border;"
                + "width: 18px;"
                + "border: none;"
                + "background: transparent;"
                + "}"
                + "QAbstractSpinBox::up-button { subcontrol-position: top right; }"
                + "QAbstractSpinBox::down-button { subcontrol-position: bottom right; }"
                + "QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover {"
                + "background: rgba(255,255,255,6);"
                + "}"
                + "QAbstractSpinBox::up-button:pressed, QAbstractSpinBox::down-button:pressed {"
                + "background: rgba(47,129,247,18);"
                + "}"
                + "QAbstractSpinBox::up-arrow, QAbstractSpinBox::down-arrow { width: 8px; height: 8px; }"
            )
            spin.setMinimumHeight(22)
            spin.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            layout.addWidget(spin, 1)
            container.value_widgets = [spin]

        # FlowLayout 不支持 addStretch；QHBoxLayout 也不强制加 stretch，避免把编辑器挤太窄
        return container
    
    def _should_show_color_preview(self, param_name: str, param_type: str) -> bool:
        """判断是否应该显示颜色预览"""
        if param_type in ['Float4', 'Float5']:
            return True
        if param_type == 'Float3':
            return 'color' in param_name.lower()
        return False
    
    def _create_preview_widget(self, param_type: str, param_name: str, value_widgets: list) -> Optional[QWidget]:
        """创建预览控件（颜色或透明度渐变）"""
        from PySide6.QtGui import QColor
        
        if param_type == 'Int2':
            # Int2: 透明度渐变预览
            preview = GradientPreviewWidget(size=48)
            
            def update_gradient():
                x = value_widgets[0].value() if len(value_widgets) > 0 else 0
                y = value_widgets[1].value() if len(value_widgets) > 1 else 0
                preview.set_direction(int(x), int(y))
            
            def open_gradient_editor():
                x = value_widgets[0].value() if len(value_widgets) > 0 else 0
                y = value_widgets[1].value() if len(value_widgets) > 1 else 0
                dialog = GradientEditorDialog(self, int(x), int(y))
                if dialog.exec() == GradientEditorDialog.Accepted:
                    new_x, new_y = dialog.get_direction()
                    if len(value_widgets) > 0:
                        value_widgets[0].setValue(new_x)
                    if len(value_widgets) > 1:
                        value_widgets[1].setValue(new_y)
            
            for spin in value_widgets:
                spin.valueChanged.connect(update_gradient)
            preview.clicked.connect(open_gradient_editor)
            update_gradient()
            return preview
        
        elif self._should_show_color_preview(param_name, param_type):
            # Float3/4/5: 颜色预览
            preview = ColorPreviewWidget(size=48)
            show_alpha = param_type in ['Float4', 'Float5']
            
            def update_color():
                r = value_widgets[0].value() if len(value_widgets) > 0 else 0.0
                g = value_widgets[1].value() if len(value_widgets) > 1 else 0.0
                b = value_widgets[2].value() if len(value_widgets) > 2 else 0.0
                a = value_widgets[3].value() if len(value_widgets) > 3 else 1.0
                preview.set_rgba(r, g, b, a)
            
            def open_picker():
                current = preview.get_color()
                dialog = ColorPickerDialog(self, current, show_alpha=show_alpha)
                if dialog.exec() == ColorPickerDialog.Accepted:
                    r, g, b, a = dialog.get_rgba_floats()
                    if len(value_widgets) > 0:
                        value_widgets[0].setValue(r)
                    if len(value_widgets) > 1:
                        value_widgets[1].setValue(g)
                    if len(value_widgets) > 2:
                        value_widgets[2].setValue(b)
                    if len(value_widgets) > 3 and show_alpha:
                        value_widgets[3].setValue(a)
            
            for spin in value_widgets[:4]:  # 只监听前4个值
                spin.valueChanged.connect(update_color)
            preview.clicked.connect(open_picker)
            update_color()
            return preview
        
        return None

    def _parse_array_value(self, value: Any, param_type: str) -> List:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except:
                pass
        
        lengths = {'Float2': 2, 'Float3': 3, 'Float4': 4, 'Float5': 5, 'Int2': 2}
        length = lengths.get(param_type, 4)
        return [0.0] * length

    def _on_param_type_changed(self, index: int, new_type: str):
        if index not in self._param_cards:
            return
        
        card_data = self._param_cards[index]
        value_container = card_data['value_container']
        value_layout = card_data['value_layout']
        
        while value_layout.count():
            item = value_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        new_editor = self._create_value_editor(new_type, '')
        value_layout.addWidget(new_editor)

    def load_detail(self, detail: Optional[Dict[str, Any]]):
        if not detail:
            self._current_detail = None
            self.empty_label.show()
            self.basic_info_widget.hide()
            self.params_container.hide()
            self.sampler_panel.hide()
            return

        # 禁用UI更新以提升性能
        self.setUpdatesEnabled(False)
        try:
            self._current_detail = detail
            
            self.empty_label.hide()
            self.basic_info_widget.show()
            self.params_container.show()
            self.sampler_panel.show()

            filename = detail.get('filename') or detail.get('file_name') or _('unknown_material')
            self.title_label.setText(f"{_('material_details')}: {filename}")

            for field, label in self.info_labels.items():
                value = detail.get(field, '') or detail.get(field.replace('_value', ''), '') or '-'
                label.setText(str(value))
                label.setToolTip(str(value))  # 完整值显示在tooltip中

            self._load_params(detail.get('params', []))
            self.sampler_model.load(detail.get('samplers', []))
            # 通知 sampler_panel 刷新列宽
            self.sampler_panel.on_data_loaded()
        finally:
            self.setUpdatesEnabled(True)

    def _load_params(self, params: List[Dict[str, Any]]):
        # 缓存原始参数，供“显示内容/分组/搜索”动态刷新
        self._param_list = list(params or [])

        # 快速清空旧卡片/旧分组容器（使用 setParent(None) 比 deleteLater 更快）
        for card_data in self._param_cards.values():
            card = card_data.get('card')
            if card:
                card.setParent(None)
                card.deleteLater()
        self._param_cards.clear()

        for grp in self._param_groups.values():
            w = grp.get('widget')
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._param_groups.clear()

        # 应用搜索过滤
        filtered: List[Dict[str, Any]] = []
        for p in (params or []):
            if not self._search_text:
                filtered.append(p)
                continue

            name = str(p.get('name', '') or '').lower()
            key = str(p.get('key_value', '') or p.get('key', '') or '').lower()
            ptype = str(p.get('type', '') or '').lower()
            val = p.get('value', '')
            val_text = ''
            try:
                val_text = json.dumps(val, ensure_ascii=False).lower()
            except Exception:
                val_text = str(val).lower()

            if (self._search_text in name) or (self._search_text in key) or (self._search_text in ptype) or (self._search_text in val_text):
                filtered.append(p)

        # 分组下拉刷新
        all_groups = sorted({(p.get('type') or 'Unknown') for p in (params or [])})
        all_text = _('all_params')
        desired_items = [all_text] + all_groups
        curr_items = [self.group_combo.itemText(i) for i in range(self.group_combo.count())]
        if curr_items != desired_items:
            current = self.group_combo.currentText() if hasattr(self, 'group_combo') else all_text
            self.group_combo.blockSignals(True)
            self.group_combo.clear()
            self.group_combo.addItems(desired_items)
            if current in desired_items:
                self.group_combo.setCurrentText(current)
            self.group_combo.blockSignals(False)

        # 分组筛选 - 使用动态翻译比较
        all_text = _('all_params')
        if self._selected_group and self._selected_group != all_text:
            filtered = [p for p in filtered if (p.get('type') or 'Unknown') == self._selected_group]

        # 清空 grid 中旧布局项
        while self.params_grid.count():
            item = self.params_grid.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        if not filtered:
            empty = QLabel(_('no_matching_params'))
            empty.setStyleSheet("color:#9ca9c5; font-size: 12px;")
            empty.setAlignment(Qt.AlignCenter)
            self.params_grid.addWidget(empty, 0, 0, 1, 1)
            self.params_grid.setColumnStretch(0, 1)
            return

        if self._use_grouping:
            # 垂直分组：每组一个折叠容器（更适合搜索/展开折叠）
            top_row = 0
            for t in sorted({(p.get('type') or 'Unknown') for p in filtered}):
                grp_params = [p for p in filtered if (p.get('type') or 'Unknown') == t]
                grp_widget = self._create_param_group_widget(t, grp_params)
                self.params_grid.addWidget(grp_widget, top_row, 0, 1, 1)
                top_row += 1
            self.params_grid.setColumnStretch(0, 1)
        else:
            # 传统三列卡片
            row, col = 0, 0
            max_cols = getattr(self, '_params_cols', 3)
            for i, param in enumerate(filtered):
                card = self._create_param_card(i, param)
                self.params_grid.addWidget(card, row, col)
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

            for c in range(max_cols):
                self.params_grid.setColumnStretch(c, 1)

    def _create_param_group_widget(self, group_name: str, params: List[Dict[str, Any]]) -> QWidget:
        wrapper = QFrame()
        # 分组容器不应拉伸高度：使用 Minimum 垂直策略，让折叠后保持紧凑
        wrapper.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        # 分组 wrapper 必须透明：否则会在卡片背后形成“一整块连在一起的背景”
        wrapper.setStyleSheet("QFrame { background: transparent; border: none; }")

        # 分组不必再额外加阴影（卡片本身已有阴影），否则会产生大块发灰的底
        wrapper.setGraphicsEffect(None)

        v = QVBoxLayout(wrapper)
        # 给分组本身留一点外边距，但不画背景
        v.setContentsMargins(0, 0, 0, 6)
        v.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(8)

        toggle = QPushButton()
        toggle.setCheckable(True)
        toggle.setChecked(True)  # True=展开
        toggle.setFixedSize(22, 22)
        toggle.setIconSize(QSize(12, 12))
        toggle.setStyleSheet("""
            QPushButton {
                border-radius: 6px;
                background-color: rgba(255, 255, 255, 12);
                border: 1px solid rgba(255, 255, 255, 18);
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 22);
                border-color: rgba(255, 255, 255, 30);
            }
        """)

        toggle.setIcon(QIcon(get_assets_path("chevron_down.svg")))

        title = QLabel(f"{group_name}  ({len(params)})")
        title.setStyleSheet("font-size: 12px; font-weight: 600; color: #f5f7ff;")

        header.addWidget(toggle)
        header.addWidget(title, 1)
        v.addLayout(header)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        grid = QGridLayout(content)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        max_cols = getattr(self, '_params_cols', 3)
        r, c = 0, 0
        for i, p in enumerate(params):
            card = self._create_param_card(i, p)
            grid.addWidget(card, r, c)
            c += 1
            if c >= max_cols:
                c = 0
                r += 1
        for cc in range(max_cols):
            grid.setColumnStretch(cc, 1)

        v.addWidget(content)

        def _toggle():
            collapsed = content.isVisible()
            content.setVisible(not collapsed)
            toggle.setChecked(not collapsed)
            toggle.setIcon(QIcon(get_assets_path("chevron_down.svg") if not collapsed else get_assets_path("chevron_right.svg")))

        toggle.clicked.connect(_toggle)

        self._param_groups[group_name] = {
            'widget': wrapper,
            'toggle': toggle,
            'content': content,
        }
        return wrapper

    def _collect_params(self) -> List[Dict[str, Any]]:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"_collect_params called, _param_cards has {len(self._param_cards)} items, _param_list has {len(getattr(self, '_param_list', []))} items")
        
        # 使用原始参数列表作为基础，避免丢失未显示的参数
        original_params = getattr(self, '_param_list', [])
        
        # 如果没有原始参数列表，则只使用当前显示的卡片
        if not original_params:
            params = []
            for index in sorted(self._param_cards.keys()):
                card_data = self._param_cards[index]
                params.append(self._extract_param_from_card(card_data))
            return params
        
        # 收集当前显示卡片中的编辑数据
        edited_params = {}
        for index in sorted(self._param_cards.keys()):
            card_data = self._param_cards[index]
            param_data = card_data.get('param_data', {})
            # 使用原始参数的name+type作为key来匹配
            key = (param_data.get('name', ''), param_data.get('type', ''))
            edited_params[key] = self._extract_param_from_card(card_data)
        
        # 合并：原始列表中的参数，如果在编辑卡片中则用编辑后的值
        result = []
        for orig_param in original_params:
            key = (orig_param.get('name', ''), orig_param.get('type', ''))
            if key in edited_params:
                result.append(edited_params[key])
            else:
                # 保留原始参数（未被编辑的）
                result.append({
                    'name': orig_param.get('name', ''),
                    'type': orig_param.get('type', ''),
                    'value': orig_param.get('value', ''),
                    'key': orig_param.get('key_value', '') or orig_param.get('key', ''),
                    'key_value': orig_param.get('key_value', '') or orig_param.get('key', '')
                })
        
        logger.info(f"_collect_params returning {len(result)} params")
        return result
    
    def _extract_param_from_card(self, card_data: Dict[str, Any]) -> Dict[str, Any]:
        """从卡片中提取参数数据"""
        param_type = card_data['type_combo'].currentText()
        param_name = card_data['name_edit'].text()
        param_key = card_data['key_edit'].text()
        
        value_container = card_data['value_container']
        if hasattr(value_container, 'value_widgets'):
            widgets = value_container.value_widgets
            
            if param_type == 'Bool':
                value = widgets[0].currentText() == 'true'
            elif param_type in ['Float2', 'Float3', 'Float4', 'Float5', 'Int2']:
                value = [w.value() for w in widgets]
            else:
                value = widgets[0].value()
        else:
            value = ''

        return {
            'name': param_name,
            'type': param_type,
            'value': value,
            'key': param_key,
            'key_value': param_key
        }

    def _on_save_clicked(self):
        if not self._current_detail:
            return
        
        try:
            params = self._collect_params()
            
            updated = {
                'filename': self._current_detail.get('filename', ''),
                'shader_path': self._current_detail.get('shader_path', ''),
                'source_path': self._current_detail.get('source_path', ''),
                'compression': self._current_detail.get('compression', ''),
                'key': self._current_detail.get('key_value', '') or self._current_detail.get('key', ''),
                'params': params,
                'samplers': self._current_detail.get('samplers', []),
            }
            self.saveRequested.emit(updated)
        except Exception as exc:
            QMessageBox.warning(self, "保存失败", f"收集参数时出错: {exc}")



    def refresh_translations(self):
        """刷新所有翻译文本（语言切换时调用）"""
        # 顶部标题栏
        self.title_label.setText(_('material_details'))  # 材质详情
        self.autopack_check.setText(_('add_to_autopack'))
        self.save_btn.setText(_('save'))

        
        # 区域卡片标题
        if hasattr(self, 'basic_info_title') and self.basic_info_title:
            self.basic_info_title.setText(_('basic_info'))
        if hasattr(self, 'editable_params_title') and self.editable_params_title:
            self.editable_params_title.setText(_('editable_params'))
        if hasattr(self, 'editor_hint_label') and self.editor_hint_label:
            self.editor_hint_label.setText(_('editor_hint'))
        
        # 基本信息字段标签
        field_key_map = {
            'filename': 'filename',
            'shader_path': 'shader_path',
            'source_path': 'file_path',
            'compression': 'compression_type',
            'key_value': 'key_value'
        }
        if hasattr(self, 'field_label_widgets'):
            for field, i18n_key in field_key_map.items():
                if field in self.field_label_widgets:
                    self.field_label_widgets[field].setText(_( i18n_key))
        
        # 可编辑参数区域的工具栏
        self.display_btn.setText(_('content'))
        self.search_edit.setPlaceholderText(_('search_params_placeholder'))
        self.expand_all_btn.setText(_('expand_all'))
        self.collapse_all_btn.setText(_('collapse_all'))
        
        # 显示选项菜单
        self.action_show_type.setText(_('editor_show_type'))
        self.action_show_key.setText(_('editor_show_key'))
        self.action_show_name_edit.setText(_('editor_show_name_edit'))
        self.action_grouping.setText(_('editor_group_by_type'))
        
        # 分组下拉框的第一项
        if self.group_combo.count() > 0:
            self.group_combo.setItemText(0, _('all_params'))
        
        # 采样器面板
        if hasattr(self, 'sampler_panel') and self.sampler_panel:
            self.sampler_panel.refresh_translations()
        
        # 空白提示
        if hasattr(self, 'empty_label') and self.empty_label:
            self.empty_label.setText(_('select_material_detail_hint'))


class _FlowLayout(QLayout):
    """简单 FlowLayout：控件不足一行时自动换行，提升“参数内容”可读性。"""

    def __init__(self, parent=None, margin: int = 0, hSpacing: int = 6, vSpacing: int = 6):
        super().__init__(parent)
        self._items: list[QWidgetItem] = []
        self._hSpace = hSpacing
        self._vSpace = vSpacing
        self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), testOnly=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, testOnly=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        left, top, right, bottom = self.getContentsMargins()
        size += QSize(left + right, top + bottom)
        return size

    def _do_layout(self, rect: QRect, testOnly: bool) -> int:
        left, top, right, bottom = self.getContentsMargins()
        effective = rect.adjusted(left, top, -right, -bottom)

        x = effective.x()
        y = effective.y()
        lineHeight = 0

        for item in self._items:
            hint = item.sizeHint()

            nextX = x + hint.width() + self._hSpace
            if nextX - self._hSpace > effective.right() and lineHeight > 0:
                x = effective.x()
                y = y + lineHeight + self._vSpace
                nextX = x + hint.width() + self._hSpace
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(x, y, hint.width(), hint.height()))

            x = nextX
            lineHeight = max(lineHeight, hint.height())

        return (y + lineHeight) - rect.y() + bottom
