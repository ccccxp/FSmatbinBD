"""
纹理编辑面板

按设计文档V3第六章 6.2 实现：
- 三行布局：采样器名/路径+XY/更多参数
- 批量替换入口
- 保存/取消
- 面板级缓存（按材质缓存）
"""

from typing import Optional, Dict, Any, List
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QDoubleSpinBox, QSpinBox, QCheckBox, QGroupBox,
    QScrollArea, QFrame, QSplitter, QMessageBox, QApplication,
    QSizePolicy, QFormLayout, QComboBox, QListWidget, QListWidgetItem,
    QGridLayout
)
from PySide6.QtCore import Qt, Signal, QSettings, QEvent, QTimer
from PySide6.QtGui import QIcon
import os
from src.utils.resource_path import get_assets_path

from src.core.i18n import _
from src.core.material_replace_models import (
    MaterialEntry, SamplerData, Vec2
)
from src.core.sampler_type_parser import get_sampler_display_name
from src.gui_qt.theme.palette import COLORS

# 主题颜色别名
C = COLORS


class SamplerCard(QFrame):
    """
    采样器卡片组件 - 使用主题配色
    
    三行布局：
    1. 采样器名称（只读）
    2. 路径 + X + Y
    3. 更多参数（默认隐藏）
    """
    
    dataChanged = Signal()
    
    def __init__(self, sampler: SamplerData, parent=None):
        super().__init__(parent)
        self._sampler = sampler
        self._show_more = False
        self._setup_ui()
        self._setup_style()
        self._load_data()
    
    def _setup_style(self):
        """设置卡片样式 - 参考采样器面板"""
        self.setStyleSheet(f"""
            SamplerCard {{
                background-color: rgba(10, 14, 24, 160);
                border: 1px solid rgba(110, 165, 255, 90);
                border-radius: 8px;
            }}
            SamplerCard:hover {{
                background-color: rgba(47, 129, 247, 18);
                border: 1px solid {C['accent']};
            }}
            QLabel {{
                color: {C['fg_primary']};
                background: transparent;
                border: none;
            }}
            QLineEdit {{
                background-color: rgba(255, 255, 255, 5);
                border: 1px solid rgba(110, 165, 255, 60);
                border-radius: 4px;
                padding: 4px 8px;
                color: {C['fg_primary']};
                font-size: 9pt;
            }}
            QLineEdit:focus {{
                border: 1px solid {C['accent']};
                background-color: rgba(47, 129, 247, 10);
            }}
            QDoubleSpinBox, QSpinBox {{
                background-color: rgba(255, 255, 255, 5);
                border: 1px solid rgba(110, 165, 255, 60);
                border-radius: 4px;
                padding: 2px 6px;
                color: {C['fg_primary']};
                font-size: 9pt;
            }}
            QDoubleSpinBox:focus, QSpinBox:focus {{
                border: 1px solid {C['accent']};
            }}
            QCheckBox {{
                color: {C['fg_secondary']};
                background: transparent;
            }}
        """)
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        
        # 第1行：采样器名称（完整type_name）
        row1 = QHBoxLayout()
        name_label = QLabel(self._sampler.type_name)
        name_label.setStyleSheet(f"font-weight: bold; color: {C['warning']};")
        name_label.setToolTip(self._sampler.type_name)  # 完整类型名作为提示
        row1.addWidget(name_label)
        layout.addLayout(row1)
        
        # 第2行：路径 + X + Y
        row2 = QHBoxLayout()
        row2.setSpacing(6)
        
        path_label = QLabel(_('path') + ":")
        path_label.setStyleSheet(f"color: {C['fg_secondary']};")
        path_label.setFixedWidth(40)
        row2.addWidget(path_label)
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText(_('texture_path_placeholder'))
        self.path_edit.textChanged.connect(self._on_data_changed)
        row2.addWidget(self.path_edit, 1)
        
        x_label = QLabel("X:")
        x_label.setStyleSheet(f"color: {C['fg_secondary']};")
        x_label.setFixedWidth(20)
        row2.addWidget(x_label)
        
        self.scale_x = QDoubleSpinBox()
        self.scale_x.setRange(-1000, 1000)
        self.scale_x.setDecimals(2)  # 保留2位小数以便手动输入
        self.scale_x.setSingleStep(1)  # 默认按整数递增/递减
        self.scale_x.setFixedWidth(70)
        self.scale_x.valueChanged.connect(self._on_data_changed)
        row2.addWidget(self.scale_x)
        
        y_label = QLabel("Y:")
        y_label.setStyleSheet(f"color: {C['fg_secondary']};")
        y_label.setFixedWidth(20)
        row2.addWidget(y_label)
        
        self.scale_y = QDoubleSpinBox()
        self.scale_y.setRange(-1000, 1000)
        self.scale_y.setDecimals(2)  # 保留2位小数以便手动输入
        self.scale_y.setSingleStep(1)  # 默认按整数递增/递减
        self.scale_y.setFixedWidth(70)
        self.scale_y.valueChanged.connect(self._on_data_changed)
        row2.addWidget(self.scale_y)
        
        layout.addLayout(row2)
        
        # 第3行：更多参数（默认隐藏）
        self.more_widget = QWidget()
        self.more_widget.setStyleSheet("background: transparent;")
        more_layout = QHBoxLayout(self.more_widget)
        more_layout.setContentsMargins(0, 4, 0, 0)
        more_layout.setSpacing(8)
        
        # Unk10
        unk10_label = QLabel("Unk10:")
        unk10_label.setStyleSheet(f"color: {C['fg_muted']};")
        more_layout.addWidget(unk10_label)
        self.unk10_spin = QSpinBox()
        self.unk10_spin.setRange(-999999, 999999)
        self.unk10_spin.setFixedWidth(70)
        self.unk10_spin.valueChanged.connect(self._on_data_changed)
        more_layout.addWidget(self.unk10_spin)
        
        # Unk11 (显示 True/False)
        unk11_label = QLabel("Unk11:")
        unk11_label.setStyleSheet(f"color: {C['fg_muted']};")
        more_layout.addWidget(unk11_label)
        self.unk11_check = QCheckBox()
        self.unk11_check.stateChanged.connect(self._on_data_changed)
        more_layout.addWidget(self.unk11_check)
        
        # Unk14
        unk14_label = QLabel("Unk14:")
        unk14_label.setStyleSheet(f"color: {C['fg_muted']};")
        more_layout.addWidget(unk14_label)
        self.unk14_spin = QSpinBox()
        self.unk14_spin.setRange(-999999, 999999)
        self.unk14_spin.setFixedWidth(70)
        self.unk14_spin.valueChanged.connect(self._on_data_changed)
        more_layout.addWidget(self.unk14_spin)
        
        # Unk18
        unk18_label = QLabel("Unk18:")
        unk18_label.setStyleSheet(f"color: {C['fg_muted']};")
        more_layout.addWidget(unk18_label)
        self.unk18_spin = QSpinBox()
        self.unk18_spin.setRange(-999999, 999999)
        self.unk18_spin.setFixedWidth(70)
        self.unk18_spin.valueChanged.connect(self._on_data_changed)
        more_layout.addWidget(self.unk18_spin)
        
        # Unk1C
        unk1c_label = QLabel("Unk1C:")
        unk1c_label.setStyleSheet(f"color: {C['fg_muted']};")
        more_layout.addWidget(unk1c_label)
        self.unk1c_spin = QSpinBox()
        self.unk1c_spin.setRange(-999999, 999999)
        self.unk1c_spin.setFixedWidth(70)
        self.unk1c_spin.valueChanged.connect(self._on_data_changed)
        more_layout.addWidget(self.unk1c_spin)
        
        more_layout.addStretch()
        
        self.more_widget.setVisible(False)
        layout.addWidget(self.more_widget)
    
    def _load_data(self):
        """加载采样器数据到控件"""
        self.path_edit.setText(self._sampler.path)
        self.scale_x.setValue(self._sampler.scale.x)
        self.scale_y.setValue(self._sampler.scale.y)
        self.unk10_spin.setValue(self._sampler.unk10)
        self.unk11_check.setChecked(self._sampler.unk11)
        self.unk14_spin.setValue(self._sampler.unk14)
        self.unk18_spin.setValue(self._sampler.unk18)
        self.unk1c_spin.setValue(self._sampler.unk1c)
    
    def _on_data_changed(self):
        """数据变化"""
        self.dataChanged.emit()
    
    def set_show_more(self, show: bool):
        """设置是否显示更多参数"""
        self._show_more = show
        self.more_widget.setVisible(show)
    
    def get_data(self) -> SamplerData:
        """获取编辑后的采样器数据"""
        return SamplerData(
            type_name=self._sampler.type_name,
            index=self._sampler.index,
            sampler_type=self._sampler.sampler_type,
            sorted_pos=self._sampler.sorted_pos,
            path=self.path_edit.text(),
            scale=Vec2(self.scale_x.value(), self.scale_y.value()),
            unk10=self.unk10_spin.value(),
            unk11=self.unk11_check.isChecked(),
            unk14=self.unk14_spin.value(),
            unk18=self.unk18_spin.value(),
            unk1c=self.unk1c_spin.value(),
        )
    
    def set_data(self, sampler: SamplerData):
        """设置采样器数据"""
        self._sampler = sampler
        self._load_data()


class TextureEditPanel(QWidget):
    """
    纹理编辑面板
    
    按设计文档 6.2 实现
    """
    
    # 信号
    saveRequested = Signal(object)  # MaterialEntry
    cacheUpdated = Signal(dict)     # 缓存数据
    closed = Signal()
    
    # ==================== 帮助类 ====================
    
    class GlowButtonWrapper(QWidget):
        """带有独立发光层的按钮包装器（解决文字模糊问题）"""
        
        def __init__(self, text, object_name, callback, color, parent=None):
            super().__init__(parent)
            self.setObjectName(f"{object_name}_wrapper")
            
            # 使用层叠布局
            layout = QGridLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            
            # 1. 底部发光层（用于应用 DropShadow）
            self.glow_bg = QWidget()
            self.glow_bg.setObjectName(object_name)  # 复用按钮样式
            self.glow_bg.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)  # 不接收鼠标事件
            layout.addWidget(self.glow_bg, 0, 0)
            
            # 2. 顶部按钮层（不应用发光，保持文字清晰）
            from PySide6.QtWidgets import QSizePolicy
            self.btn = QPushButton(text)
            self.btn.setObjectName(object_name)
            self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.btn.clicked.connect(callback)
            layout.addWidget(self.btn, 0, 0)
            
            # 初始化发光效果（应用于底部层）
            from src.gui_qt.theme.qss import apply_glow_effect
            apply_glow_effect(self.glow_bg, color=color, blur_radius=15)
            
            # 事件穿透处理：当鼠标悬停在按钮上时，手动触发底部层的发光效果
            self.btn.installEventFilter(self)
        
        def eventFilter(self, obj, event):
            if obj == self.btn:
                if event.type() == QEvent.Enter:
                    # 鼠标进入按钮 -> 触发底部层的 Enter 事件以显示发光
                    QApplication.sendEvent(self.glow_bg, QEvent(QEvent.Enter))
                elif event.type() == QEvent.Leave:
                    # 鼠标离开按钮 -> 触发底部层的 Leave 事件以隐藏发光
                    QApplication.sendEvent(self.glow_bg, QEvent(QEvent.Leave))
            return super().eventFilter(obj, event)

    def _create_glow_button(self, text, object_name, callback, color=(47, 129, 247)):
        return self.GlowButtonWrapper(text, object_name, callback, color)

    def __init__(
        self,
        parent=None,
        material: MaterialEntry = None,
        material_index: int = -1,
        database_manager=None,
        cached_state: Dict[str, Any] = None,
    ):
        super().__init__(parent)
        
        self._material = material
        self._material_index = material_index
        self._db = database_manager
        self._cached_state = cached_state
        
        self._sampler_cards: List[SamplerCard] = []
        self._is_dirty = False
        
        self._setup_ui()
        self._load_material()
        
        # 恢复缓存状态
        if cached_state:
            self._restore_cache(cached_state)
        
        # 设置窗口属性
        from src.gui_qt.dark_titlebar import apply_dark_titlebar_to_window
        apply_dark_titlebar_to_window(self)
        
        # 设置窗口图标
        try:
            icon_path = get_assets_path("app_icon.png")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass
        
        self.setWindowFlags(Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setMinimumSize(600, 400)
    
    def _setup_ui(self):
        """设置UI"""
        # 设置窗口背景样式
        self.setStyleSheet(f"""
            TextureEditPanel {{
                background-color: {C['bg_primary']};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # 1. 顶部栏（标题 + 批量替换按钮）
        top_bar = QHBoxLayout()
        
        self.title_label = QLabel()
        self.title_label.setStyleSheet(f"""
            font-size: 15px;
            font-weight: bold;
            color: {C['fg_primary']};
        """)
        top_bar.addWidget(self.title_label)
        
        top_bar.addStretch()
        
        # 批量替换入口 (6.3.1.1)
        self.batch_replace_btn = QPushButton(f"🔄 {_('batch_replace_material')}")
        self.batch_replace_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.batch_replace_btn.setObjectName("purple-glass")
        self.batch_replace_btn.clicked.connect(self._on_batch_replace)
        top_bar.addWidget(self.batch_replace_btn)
        
        layout.addLayout(top_bar)
        
        # 通用 GroupBox 样式
        group_style = f"""
            QGroupBox {{
                background-color: rgba(10, 14, 24, 160);
                border: 1px solid rgba(110, 165, 255, 90);
                border-radius: 10px;
                margin-top: 14px;
                padding-top: 8px;
                font-weight: bold;
                color: {C['fg_primary']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                padding: 0 6px;
                color: {C['accent']};
            }}
        """
        
        # 通用输入框样式
        input_style = f"""
            QLineEdit, QComboBox {{
                background-color: {C['input_bg']};
                border: 1px solid {C['input_border']};
                border-radius: 6px;
                padding: 6px 10px;
                color: {C['fg_primary']};
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 1px solid {C['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {C['bg_secondary']};
                border: 1px solid {C['border_strong']};
                selection-background-color: {C['accent']};
                color: {C['fg_primary']};
            }}
            QSpinBox, QDoubleSpinBox {{
                background-color: {C['input_bg']};
                border: 1px solid {C['input_border']};
                border-radius: 4px;
                padding: 2px 6px;
                color: {C['fg_primary']};
            }}
            QSpinBox::up-button, QSpinBox::down-button,
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                width: 0px;
                border: none;
            }}
        """
        
        # 2. 基本信息区域 (6.2.1) - 支持材质搜索
        info_group = QGroupBox(_('basic_info'))
        info_group.setStyleSheet(group_style)
        info_layout = QVBoxLayout(info_group)
        info_layout.setContentsMargins(12, 16, 12, 12)
        info_layout.setSpacing(10)
        
        # 材质路径显示（只读）
        path_row = QHBoxLayout()
        path_label_title = QLabel(_('material_path') + ":")
        path_label_title.setStyleSheet(f"color: {C['fg_secondary']}; font-weight: normal;")
        path_row.addWidget(path_label_title)
        self.path_label = QLabel()
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.path_label.setStyleSheet(f"color: {C['fg_primary']}; font-weight: normal;")
        path_row.addWidget(self.path_label, 1)
        info_layout.addLayout(path_row)
        
        # 材质搜索区域（库下拉+搜索并排）
        search_row = QHBoxLayout()
        
        # 库下拉
        from PySide6.QtWidgets import QComboBox
        self.lib_combo = QComboBox()
        self.lib_combo.setMinimumWidth(120)
        self.lib_combo.setStyleSheet(input_style)
        self._load_lib_combo()
        search_row.addWidget(self.lib_combo)
        
        # 搜索框
        self.material_search = QLineEdit()
        self.material_search.setMinimumHeight(32)
        self.lib_combo.setMinimumHeight(32)
        self.material_search.setPlaceholderText(_('search_material_for_samplers'))
        self.material_search.setStyleSheet(input_style)
        self.material_search.returnPressed.connect(self._on_material_search)
        search_row.addWidget(self.material_search, 1)
        
        # 搜索按钮
        search_wrapper = self._create_glow_button("🔍", "solid-blue", self._on_material_search)
        search_wrapper.setFixedSize(40, 32)
        search_wrapper.btn.setStyleSheet("padding: 0;")
        search_row.addWidget(search_wrapper)
        info_layout.addLayout(search_row)
        
        # 搜索结果列表
        from PySide6.QtWidgets import QListWidget, QListWidgetItem
        self.search_result_list = QListWidget()
        self.search_result_list.setMaximumHeight(120)
        self.search_result_list.setVisible(False)
        self.search_result_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {C['bg_secondary']};
                border: 1px solid {C['border_strong']};
                border-radius: 6px;
                color: {C['fg_primary']};
                outline: none;
            }}
            QListWidget::item {{
                padding: 6px 10px;
                border-bottom: 1px solid {C['border_subtle']};
            }}
            QListWidget::item:hover {{
                background-color: rgba(47, 129, 247, 38);
            }}
            QListWidget::item:selected {{
                background-color: {C['accent']};
                color: {C['fg_primary']};
            }}
        """)
        self.search_result_list.itemClicked.connect(self._on_search_result_clicked)
        info_layout.addWidget(self.search_result_list)
        
        layout.addWidget(info_group)
        
        # 3. 采样器配置区域
        sampler_group = QGroupBox(_('sampler_configuration'))
        sampler_group.setStyleSheet(group_style)
        sampler_layout = QVBoxLayout(sampler_group)
        sampler_layout.setContentsMargins(12, 16, 12, 12)
        
        # 工具栏
        tool_layout = QHBoxLayout()
        self.show_more_check = QCheckBox(_('show_more_parameters'))
        self.show_more_check.setStyleSheet(f"""
            QCheckBox {{
                color: {C['fg_secondary']};
                font-weight: normal;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid {C['accent']};
                background-color: transparent;
            }}
            QCheckBox::indicator:checked {{
                background-color: {C['accent']};
                border-color: {C['accent']};
                image: url({get_assets_path("checkbox_check_white.svg").replace("\\", "/")});
            }}
        """)
        self.show_more_check.stateChanged.connect(self._on_show_more_changed)
        tool_layout.addWidget(self.show_more_check)
        tool_layout.addStretch()
        sampler_layout.addLayout(tool_layout)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: {C['bg_secondary']};
                width: 10px;
                border-radius: 5px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {C['border_strong']};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {C['accent']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 8, 0)
        self.scroll_layout.setSpacing(10)
        self.scroll_layout.addStretch()
        
        scroll.setWidget(self.scroll_content)
        sampler_layout.addWidget(scroll)
        
        layout.addWidget(sampler_group, 1)  # 占用剩余空间
        
        # 4. 底部按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        # 通用按钮样式
        btn_primary_style = f"""
            QPushButton {{
                background-color: {C['accent']};
                color: {C['fg_primary']};
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgba(47, 129, 247, 200);
            }}
            QPushButton:pressed {{
                background-color: rgba(47, 129, 247, 150);
            }}
        """
        
        btn_secondary_style = f"""
            QPushButton {{
                background-color: transparent;
                color: {C['fg_secondary']};
                border: 1px solid {C['border_strong']};
                border-radius: 6px;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background-color: rgba(47, 129, 247, 38);
                border-color: {C['accent']};
                color: {C['fg_primary']};
            }}
        """
        
        # 保存按钮
        save_wrapper = self._create_glow_button(
            f"💾 {_('save_to_texture_edit')}", 
            "solid-blue", 
            lambda: QTimer.singleShot(0, self._on_save)
        )
        self.save_btn = save_wrapper.btn  # Keep reference
        bottom_layout.addWidget(save_wrapper)
        
        self.cancel_btn = QPushButton(_('cancel'))
        self.cancel_btn.setStyleSheet(btn_secondary_style)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.close)
        bottom_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(bottom_layout)
        
    def _load_material(self):
        """加载材质数据"""
        if not self._material:
            return
        
        # 更新标题
        title = f"{_('texture_edit')} - {self._material.name}"
        self.setWindowTitle(title)
        self.title_label.setText(title)
        
        # 更新MTD路径
        # NEW UI uses path_label
        self.path_label.setText(self._material.mtd)
        
        # 创建采样器卡片
        self._clear_sampler_cards()
        
        for sampler in self._material.textures:
            card = SamplerCard(sampler)
            card.dataChanged.connect(self._on_data_changed)
            # New UI passes show_more state
            card.set_show_more(self.show_more_check.isChecked())
            self._sampler_cards.append(card)
            # NEW UI uses scroll_layout
            self.scroll_layout.addWidget(card)
        
        self.scroll_layout.addStretch()
        
        self._update_dirty_state()
    
    def _clear_sampler_cards(self):
        """清除采样器卡片"""
        for card in self._sampler_cards:
            card.setParent(None)
            card.deleteLater()
        self._sampler_cards.clear()
        
    def _on_show_more_changed(self, state):
        """显示/隐藏更多参数"""
        checked = (state == Qt.CheckState.Checked.value)
        for card in self._sampler_cards:
            card.set_show_more(checked)

    def _on_data_changed(self):
        """数据变化"""
        self._is_dirty = True
        self._update_dirty_state()

    def _load_lib_combo(self):
        """加载库下拉选项"""
        self.lib_combo.clear()
        self.lib_combo.addItem(_('all_libraries'), None)
        
        if self._db:
            libraries = self._db.get_libraries()
            for lib in libraries:
                self.lib_combo.addItem(lib['name'], lib['id'])
    
    def _update_dirty_state(self):
        """更新脏状态UI"""
        title = f"{_('texture_edit')} - {self._material.name}"
        if self._is_dirty:
            title += " *"
        self.setWindowTitle(title)
        self.title_label.setText(title)
        
        self.save_btn.setEnabled(self._is_dirty)

    def _emit_cache(self):
        """发送缓存数据"""
        cache = {
            'show_more': self.show_more_check.isChecked(),
            'samplers': [card.get_data().to_dict() for card in self._sampler_cards],
        }
        self.cacheUpdated.emit(cache)
    
    def _restore_cache(self, cache: Dict[str, Any]):
        """恢复缓存"""
        if 'show_more' in cache:
            self.show_more_check.setChecked(cache['show_more'])
        
        if 'samplers' in cache and len(cache['samplers']) == len(self._sampler_cards):
            for i, sampler_dict in enumerate(cache['samplers']):
                sampler = SamplerData.from_dict(sampler_dict, i)
                self._sampler_cards[i].set_data(sampler)
    
    def _on_material_search(self):
        """执行材质搜索"""
        if not self._db:
            return
        
        keyword = self.material_search.text().strip()
        if not keyword:
            self.search_result_list.setVisible(False)
            return
        
        # 搜索数据库（带库筛选）
        lib_id = self.lib_combo.currentData()
        results = self._db.search_materials(
            library_id=lib_id,
            keyword=keyword
        )
        
        # 显示结果
        from PySide6.QtWidgets import QListWidgetItem
        self.search_result_list.clear()
        
        if results:
            for res in results:
                item = QListWidgetItem(f"{res['filename']} ({res.get('file_name', '')})")
                item.setData(Qt.ItemDataRole.UserRole, res['id'])
                item.setToolTip(res.get('filename', ''))
                self.search_result_list.addItem(item)
            self.search_result_list.setVisible(True)
        else:
            self.search_result_list.setVisible(False)
    
    def _on_search_result_clicked(self, item):
        """搜索结果点击 - 完整替换材质配置
        
        按设计文档，搜索功能是单次完整材质替换：
        1. 替换材质路径（MTD）
        2. 替换所有采样器名称和配置
        3. 可选：同时应用贴图路径
        """
        if not self._db:
            return
        
        material_id = item.data(Qt.ItemDataRole.UserRole)
        detail = self._db.get_material_detail(material_id)
        
        if not detail:
            return
        
        # 从数据库材质获取采样器配置
        db_samplers = detail.get('samplers', [])
        
        if not db_samplers:
            return
        
        # 询问用户是否同时应用贴图路径
        from src.gui_qt.standard_dialogs import show_yes_no_cancel_dialog
        reply = show_yes_no_cancel_dialog(
            self,
            _('apply_material'),
            _('apply_texture_path_question'),
        )
        
        if reply is None:  # Cancel
            return
        
        apply_paths = (reply is True)
        
        # 1. 更新材质路径 - 使用 filename 字段（matxml 格式）
        new_mtd = detail.get('filename', '')
        if new_mtd:
            self._material.mtd = new_mtd
            # 更新界面显示
            self.path_label.setText(new_mtd)
        
        # 2. 完整替换采样器配置
        from src.core.sampler_type_parser import parse_sampler_type
        
        # 清除现有采样器卡片
        for card in self._sampler_cards:
            card.deleteLater()
        self._sampler_cards.clear()
        
        # 清除布局中的旧项目
        while self.scroll_layout.count():
            item_to_remove = self.scroll_layout.takeAt(0)
            if item_to_remove.widget():
                item_to_remove.widget().deleteLater()
        
        # 创建新的采样器列表
        new_textures = []
        for i, db_s in enumerate(db_samplers):
            type_name = db_s.get('type', '')
            idx, base_type, _is_generic = parse_sampler_type(type_name)
            
            # 确定路径：如果用户选择应用路径则用数据库路径，否则保留空
            if apply_paths:
                path = db_s.get('path', '')
            else:
                # 尝试保留原有对应位置的路径
                if i < len(self._material.textures):
                    path = self._material.textures[i].path
                else:
                    path = ''
            
            sampler = SamplerData(
                type_name=type_name,
                index=idx,
                sampler_type=base_type,
                sorted_pos=i,
                path=path,
                scale=Vec2(1.0, 1.0),
                unk10=0,
                unk11=False,
                unk14=0,
                unk18=0,
                unk1c=0,
            )
            new_textures.append(sampler)
            
            # 创建卡片
            card = SamplerCard(sampler, self)
            card.dataChanged.connect(self._on_data_changed)
            card.set_show_more(self.show_more_check.isChecked())
            self.scroll_layout.addWidget(card)
            self._sampler_cards.append(card)
        
        # 添加弹性空间
        self.scroll_layout.addStretch()
        
        # 更新材质的采样器列表
        self._material.textures = new_textures
        
        # 标记脏状态
        self._is_dirty = True
        self._update_dirty_state()
        
        # 隐藏搜索结果
        self.search_result_list.setVisible(False)
        self.material_search.clear()
    
    def _on_save(self):
        """保存更改"""
        if not self._material:
            return
        
        # 收集数据
        new_textures = [card.get_data() for card in self._sampler_cards]
        
        new_material = MaterialEntry(
            name=self._material.name,
            mtd=self._material.mtd,
            textures=new_textures,
            gx_index=self._material.gx_index,
            index=self._material.index,
            is_modified=True,
        )
        
        # 发送保存信号
        self.saveRequested.emit(new_material)
        
        # 重置脏状态
        self._is_dirty = False
        self._update_dirty_state()
        
        # 关闭面板
        self.close()
    
    def _on_batch_replace(self):
        """打开批量替换对话框"""
        try:
            from .batch_replace_dialog import BatchReplaceDialog
            
            # 收集当前编辑状态
            current_textures = [card.get_data() for card in self._sampler_cards]
            current_material = MaterialEntry(
                name=self._material.name,
                mtd=self._material.mtd,
                textures=current_textures,
                gx_index=self._material.gx_index,
                index=self._material.index,
            )
            
            # 获取之前的缓存状态（如果有）
            cached_state = getattr(self, '_batch_replace_cache', None)
            
            dialog = BatchReplaceDialog(
                parent=self,
                source_material=current_material,
                database_manager=self._db,
                cached_state=cached_state,
            )
            
            # 连接结果信号
            dialog.resultApplied.connect(self._on_batch_replace_result)
            # 连接缓存更新信号
            dialog.cacheUpdated.connect(self._on_batch_replace_cache_updated)
            
            dialog.show()
        except Exception as e:
            import traceback
            QMessageBox.critical(
                self, 
                _('batch_replace_error_title'), 
                _('batch_replace_open_error').format(error=str(e), trace=traceback.format_exc())
            )
    
    def _on_batch_replace_cache_updated(self, cache: dict):
        """批量替换对话框缓存更新"""
        self._batch_replace_cache = cache
    
    def _on_batch_replace_result(self, result: dict):
        """批量替换结果应用"""
        if not result:
            return
        
        # 获取数据
        new_mtd = result.get('mtd', '')
        new_samplers = result.get('samplers', [])
        
        if not new_samplers:
            return
        
        # 更新材质路径
        if new_mtd:
            self._material.mtd = new_mtd
            self.path_label.setText(new_mtd)
        
        # 更新材质的采样器数据
        self._material.textures = new_samplers
        
        # 重新加载材质显示
        self._load_material()
        
        self._is_dirty = True
        self._update_dirty_state()
    
    def closeEvent(self, event):
        """关闭事件"""
        if self._is_dirty:
            from src.gui_qt.standard_dialogs import show_unsaved_changes_dialog
            from PySide6.QtWidgets import QMessageBox
            result = show_unsaved_changes_dialog(self)
            
            if result == QMessageBox.StandardButton.Save:
                self._on_save()
                return  # _on_save 会关闭窗口
            elif result == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        
        self.closed.emit()
        event.accept()
