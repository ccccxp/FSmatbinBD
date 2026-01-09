#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级搜索对话框 (Qt版本)
Advanced Search Dialog for Qt
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QCheckBox, QRadioButton, QButtonGroup,
    QScrollArea, QWidget, QFrame, QSpinBox, QDoubleSpinBox, QGroupBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from typing import Dict, List, Any, Optional
import os

from src.core.i18n import _
from src.utils.resource_path import get_assets_path
from src.gui_qt.standard_dialogs import apply_button_style



class SearchConditionWidget(QFrame):
    """单个搜索条件组件"""
    
    deleted = Signal(object)  # 删除信号
    
    def __init__(self, index: int, parent=None):
        super().__init__(parent)
        self.index = index
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """设置UI"""
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(25, 33, 45, 220),
                    stop:1 rgba(20, 28, 40, 220));
                border: 1px solid rgba(110, 165, 255, 120);
                border-radius: 10px;
                padding: 4px 10px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(6, 6, 6, 6)
        
        # 标题行 - 加粗白色字体
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel(_('advanced_search_condition_title').format(self.index + 1))
        title_label.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                color: rgba(255, 255, 255, 0.92);
                font-size: 14px;
                font-weight: bold;
                padding: 0px;
            }
        """)
        title_row.addWidget(title_label)
        title_row.addStretch()
        
        # 删除按钮
        self.delete_btn = QPushButton(_('delete_button_icon'))
        from src.gui_qt.standard_dialogs import apply_button_style
        apply_button_style(self.delete_btn, 'danger')
        self.delete_btn.setFixedWidth(85)
        title_row.addWidget(self.delete_btn)
        layout.addLayout(title_row)
        
        # 获取chevron_down.svg图标路径（使用资源路径辅助模块）
        icon_path = get_assets_path("chevron_down.svg")
        
        # 第一行：搜索类型和内容 - 更紧凑的布局
        first_row = QHBoxLayout()
        first_row.setSpacing(8)
        
        # 搜索类型 - 带左侧蓝色竖线装饰的小标题
        type_label_container = self._create_label_with_decoration(_('search_type'))
        first_row.addWidget(type_label_container)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            _('material_name'),
            _('shader_search'),
            _('sampler_search'),
            _('parameter_search')
        ])
        self.type_combo.setFixedWidth(120)
        self.type_combo.setFixedHeight(26)
        self.type_combo.setCursor(Qt.PointingHandCursor)
        self.type_combo.setStyleSheet(f"""
            QComboBox {{
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 13px;
                padding: 3px 26px 3px 10px;
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
                width: 20px;
                border: none;
            }}
            QComboBox::down-arrow {{
                image: url({icon_path.replace(chr(92), '/')});
                width: 12px;
                height: 12px;
                border: none;
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
        """)
        first_row.addWidget(self.type_combo)
        
        first_row.addSpacing(15)
        
        # 搜索内容 - 带左侧蓝色竖线装饰的小标题
        content_label_container = self._create_label_with_decoration(_('search_content'))
        first_row.addWidget(content_label_container)
        
        self.content_edit = QLineEdit()
        self.content_edit.setPlaceholderText(_('search_placeholder_full'))
        first_row.addWidget(self.content_edit, 1)
        
        layout.addLayout(first_row)
        
        # 第二行：采样器高级选项
        self.sampler_frame = QWidget()
        self.sampler_frame.setStyleSheet("QWidget { background: transparent; }")
        sampler_layout = QVBoxLayout(self.sampler_frame)
        sampler_layout.setContentsMargins(0, 5, 0, 0)
        sampler_layout.setSpacing(5)
        
        # 指定搜索模式
        self.sampler_specific_check = QCheckBox(_('sampler_search_specific'))
        self.sampler_specific_check.setStyleSheet("QCheckBox { background: transparent; padding: 2px; }")
        sampler_layout.addWidget(self.sampler_specific_check)
        
        # 采样器详情输入 - 紧凑布局
        sampler_details = QHBoxLayout()
        sampler_details.setSpacing(8)
        
        # 类型 - 带左侧蓝色竖线装饰
        type_label_container = self._create_label_with_decoration(_('sampler_type'))
        sampler_details.addWidget(type_label_container)
        
        self.sampler_type_edit = QLineEdit()
        self.sampler_type_edit.setPlaceholderText(_('sampler_type_placeholder'))
        self.sampler_type_edit.setEnabled(False)
        sampler_details.addWidget(self.sampler_type_edit, 1)
        
        sampler_details.addSpacing(8)
        
        # 路径 - 带左侧蓝色竖线装饰
        path_label_container = self._create_label_with_decoration(_('library_path_column'))
        sampler_details.addWidget(path_label_container)
        
        self.sampler_path_edit = QLineEdit()
        self.sampler_path_edit.setPlaceholderText(_('sampler_path_placeholder'))
        self.sampler_path_edit.setEnabled(False)
        sampler_details.addWidget(self.sampler_path_edit, 1)
        
        sampler_layout.addLayout(sampler_details)
        self.sampler_frame.setVisible(False)
        layout.addWidget(self.sampler_frame)
        
        # 第三行：参数高级选项
        self.param_frame = QWidget()
        self.param_frame.setStyleSheet("QWidget { background: transparent; }")
        param_layout = QVBoxLayout(self.param_frame)
        param_layout.setContentsMargins(0, 5, 0, 0)
        param_layout.setSpacing(5)
        
        # 参数值输入 - 紧凑布局
        param_value_row = QHBoxLayout()
        param_value_row.setSpacing(8)
        
        # 参数值 - 带左侧蓝色竖线装饰
        value_label_container = self._create_label_with_decoration(_('param_value_label'))
        param_value_row.addWidget(value_label_container)
        
        self.param_value_edit = QLineEdit()
        self.param_value_edit.setPlaceholderText(_('param_value_placeholder'))
        param_value_row.addWidget(self.param_value_edit, 1)
        param_layout.addLayout(param_value_row)
        
        # 数值范围搜索
        self.range_check = QCheckBox(_('enable_range_search'))
        self.range_check.setStyleSheet("QCheckBox { background: transparent; padding: 2px; }")
        param_layout.addWidget(self.range_check)
        
        # 范围输入 - 紧凑布局
        range_inputs = QHBoxLayout()
        range_inputs.setSpacing(8)
        
        # 最小值 - 带左侧蓝色竖线装饰
        min_label_container = self._create_label_with_decoration(_('min_value'))
        range_inputs.addWidget(min_label_container)
        
        self.min_spin = QDoubleSpinBox()
        self.min_spin.setRange(-999999, 999999)
        self.min_spin.setDecimals(4)
        self.min_spin.setEnabled(False)
        range_inputs.addWidget(self.min_spin, 1)
        
        range_inputs.addSpacing(8)
        
        # 最大值 - 带左侧蓝色竖线装饰
        max_label_container = self._create_label_with_decoration(_('max_value'))
        range_inputs.addWidget(max_label_container)
        
        self.max_spin = QDoubleSpinBox()
        self.max_spin.setRange(-999999, 999999)
        self.max_spin.setDecimals(4)
        self.max_spin.setEnabled(False)
        range_inputs.addWidget(self.max_spin, 1)
        
        param_layout.addLayout(range_inputs)
        self.param_frame.setVisible(False)
        layout.addWidget(self.param_frame)
    
    def _create_label_with_decoration(self, text: str) -> QWidget:
        """创建带左侧蓝色竖线装饰的标签
        
        Args:
            text: 标签文字
            
        Returns:
            包含装饰和文字的QWidget容器
        """
        container = QWidget()
        container.setStyleSheet("QWidget { background: transparent; border: none; }")
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(6)
        
        # 左侧竖线装饰
        line = QLabel()
        line.setFixedSize(2, 14)
        line.setStyleSheet("""
            background: rgba(110, 165, 255, 255);
            border-radius: 1px;
        """)
        container_layout.addWidget(line)
        
        # 标签文字
        label = QLabel(text)
        label.setStyleSheet("""
            background: transparent;
            border: none;
            color: rgba(255, 255, 255, 0.92);
            font-size: 12px;
            padding: 0px;
        """)
        container_layout.addWidget(label)
        container_layout.addStretch()
        
        return container
    
    def _connect_signals(self):
        """连接信号"""
        self.delete_btn.clicked.connect(lambda: self.deleted.emit(self))
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        self.sampler_specific_check.toggled.connect(self._on_sampler_mode_changed)
        self.range_check.toggled.connect(self._on_range_check_changed)
    
    def _on_type_changed(self, text: str):
        """搜索类型改变"""
        # 隐藏所有高级选项
        self.sampler_frame.setVisible(False)
        self.param_frame.setVisible(False)
        
        # 根据类型显示相应选项
        if text == _('sampler_search'):
            self.sampler_frame.setVisible(True)
        elif text == _('parameter_search'):
            self.param_frame.setVisible(True)
    
    def _on_sampler_mode_changed(self, checked: bool):
        """采样器模式切换"""
        if checked:
            # 指定搜索：禁用内容输入，启用类型和路径
            self.content_edit.setEnabled(False)
            self.content_edit.clear()
            self.sampler_type_edit.setEnabled(True)
            self.sampler_path_edit.setEnabled(True)
        else:
            # 常规搜索：启用内容输入，禁用类型和路径
            self.content_edit.setEnabled(True)
            self.sampler_type_edit.setEnabled(False)
            self.sampler_path_edit.setEnabled(False)
            self.sampler_type_edit.clear()
            self.sampler_path_edit.clear()
    
    def _on_range_check_changed(self, checked: bool):
        """范围检查切换"""
        self.min_spin.setEnabled(checked)
        self.max_spin.setEnabled(checked)
        if not checked:
            self.min_spin.setValue(0)
            self.max_spin.setValue(0)
    
    def get_condition_data(self) -> Optional[Dict[str, Any]]:
        """获取条件数据"""
        search_type_text = self.type_combo.currentText()
        content = self.content_edit.text().strip()
        
        # 基本条件检查
        has_basic_content = bool(content)
        has_sampler_details = (search_type_text == _('sampler_search') and
                              (self.sampler_type_edit.text().strip() or
                               self.sampler_path_edit.text().strip()))
        has_param_details = (search_type_text == _('parameter_search') and
                           (self.param_value_edit.text().strip() or
                            self.range_check.isChecked()))
        
        if not (has_basic_content or has_sampler_details or has_param_details):
            return None
        
        # 转换搜索类型
        type_map = {
            _('material_name'): "material_name",
            _('shader_search'): "shader",
            _('sampler_search'): "sampler",
            _('parameter_search'): "parameter"
        }
        
        condition_data = {
            'type': type_map.get(search_type_text, 'material_name'),
            'content': content,
            'fuzzy': True
        }
        
        # 采样器搜索的额外数据
        if search_type_text == _('sampler_search'):
            if self.sampler_specific_check.isChecked():
                condition_data['sampler_type'] = self.sampler_type_edit.text().strip()
                condition_data['sampler_path'] = self.sampler_path_edit.text().strip()
                condition_data['specific_search'] = True
        
        # 参数搜索的额外数据
        if search_type_text == _('parameter_search'):
            param_value = self.param_value_edit.text().strip()
            if param_value:
                condition_data['param_value'] = param_value
            
            if self.range_check.isChecked():
                condition_data['range'] = {
                    'min': self.min_spin.value() if self.min_spin.value() != 0 else None,
                    'max': self.max_spin.value() if self.max_spin.value() != 0 else None
                }
        
        return condition_data


class AdvancedSearchDialogQt(QDialog):
    """高级搜索对话框 (Qt版本)"""
    
    # 信号：搜索执行完成，参数为结果数量
    search_completed = Signal(int)
    
    def __init__(self, database, on_search_callback, parent=None):
        super().__init__(parent)
        
        # 应用深色标题栏
        from .dark_titlebar import apply_dark_titlebar_to_dialog
        apply_dark_titlebar_to_dialog(self)
        
        self.database = database
        self.on_search_callback = on_search_callback
        self.condition_widgets: List[SearchConditionWidget] = []
        
        self._setup_ui()
        self._add_condition()  # 添加第一个条件
    
    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle(_('advanced_search_window_title'))
        self.setMinimumSize(850, 700)
        self.resize(900, 750)
        
        # 应用深色主题（参考材质匹配对话框）
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(15, 20, 30, 245),
                    stop:1 rgba(10, 15, 25, 245));
                color: #e0e0e0;
            }
            QLabel {
                color: rgba(245, 248, 255, 235);
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background: rgba(30, 38, 50, 200);
                color: rgba(245, 248, 255, 235);
                border: 1px solid rgba(110, 165, 255, 90);
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 9pt;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border: 1px solid rgba(110, 165, 255, 180);
                background: rgba(35, 43, 55, 220);
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid rgba(110, 165, 255, 200);
                margin-right: 8px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(47, 129, 247, 200),
                    stop:1 rgba(37, 109, 227, 200));
                color: white;
                border: 1px solid rgba(70, 150, 255, 120);
                border-radius: 6px;
                padding: 7px 18px;
                font-weight: bold;
                font-size: 9pt;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(57, 139, 255, 230),
                    stop:1 rgba(47, 129, 247, 230));
                border: 1px solid rgba(80, 160, 255, 180);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(37, 119, 237, 255),
                    stop:1 rgba(27, 99, 217, 255));
            }
            QRadioButton, QCheckBox {
                color: rgba(245, 248, 255, 235);
                spacing: 8px;
                font-size: 9pt;
            }
            QRadioButton::indicator, QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 8px;
                border: 2px solid rgba(110, 165, 255, 150);
                background: rgba(30, 38, 50, 180);
            }
            QRadioButton::indicator:checked {
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                    fx:0.5, fy:0.5,
                    stop:0 rgba(47, 129, 247, 255),
                    stop:0.7 rgba(47, 129, 247, 255),
                    stop:1 rgba(30, 38, 50, 180));
                border: 2px solid rgba(80, 160, 255, 200);
            }
            QCheckBox::indicator {
                border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                background: rgba(47, 129, 247, 220);
                border: 2px solid rgba(80, 160, 255, 200);
            }
            QGroupBox {
                color: rgba(110, 165, 255, 220);
                border: 1px solid rgba(110, 165, 255, 90);
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                font-weight: bold;
                font-size: 9pt;
                background: rgba(20, 28, 40, 120);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
            QScrollBar:vertical {
                background: rgba(20, 28, 40, 150);
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: rgba(110, 165, 255, 150);
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(110, 165, 255, 200);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 标题
        title_label = QLabel(_('advanced_search_title'))
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #6ea5ff;")
        layout.addWidget(title_label)
        
        # 提示信息
        hint_label = QLabel(_('advanced_search_hint'))
        hint_label.setStyleSheet("color: #999; font-size: 10px;")
        layout.addWidget(hint_label)
        
        # 搜索条件滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
        """)
        
        self.conditions_container = QWidget()
        self.conditions_layout = QVBoxLayout(self.conditions_container)
        self.conditions_layout.setSpacing(10)
        self.conditions_layout.addStretch()
        
        scroll_area.setWidget(self.conditions_container)
        layout.addWidget(scroll_area, 1)
        
        # 搜索模式区域 - 使用按钮样式（移除说明文字，按钮本身已包含说明）
        mode_group = QGroupBox(_('search_mode'))
        mode_layout = QHBoxLayout(mode_group)
        mode_layout.setSpacing(12)
        
        # 精确匹配按钮（包含说明在按钮内）
        self.and_btn = QPushButton(_('match_mode_and'))
        self.and_btn.setCheckable(True)
        self.and_btn.setChecked(True)
        self.and_btn.setMinimumHeight(40)
        apply_button_style(self.and_btn, 'green-toggle')
        self.and_btn.clicked.connect(lambda: self._set_search_mode(True))
        mode_layout.addWidget(self.and_btn, 1)
        
        # 模糊匹配按钮（包含说明在按钮内）
        self.or_btn = QPushButton(_('match_mode_or'))
        self.or_btn.setCheckable(True)
        self.or_btn.setMinimumHeight(40)
        apply_button_style(self.or_btn, 'pink-toggle')
        self.or_btn.clicked.connect(lambda: self._set_search_mode(False))
        mode_layout.addWidget(self.or_btn, 1)
        
        layout.addWidget(mode_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        # 左侧按钮
        add_btn = QPushButton(_('add_condition_button'))
        apply_button_style(add_btn, 'blue-transparent')
        add_btn.clicked.connect(self._add_condition)
        button_layout.addWidget(add_btn)
        
        clear_btn = QPushButton(_('clear_all_button'))
        apply_button_style(clear_btn, 'danger')
        clear_btn.clicked.connect(self._clear_all)
        button_layout.addWidget(clear_btn)
        
        button_layout.addStretch()
        
        # 右侧按钮
        cancel_btn = QPushButton("✕ " + _('cancel'))
        apply_button_style(cancel_btn, 'danger')
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        search_btn = QPushButton(_('search_button_icon'))
        apply_button_style(search_btn, 'solid-blue')
        search_btn.clicked.connect(self._execute_search)
        button_layout.addWidget(search_btn)
        
        layout.addLayout(button_layout)
        
        # 状态标签
        self.status_label = QLabel(_('search_ready'))
        self.status_label.setStyleSheet("""
            color: rgba(110, 165, 255, 220); 
            font-size: 9pt;
            padding: 5px;
        """)
        layout.addWidget(self.status_label)
    
    def _set_search_mode(self, is_and: bool):
        """设置搜索模式"""
        if is_and:
            self.and_btn.setChecked(True)
            self.or_btn.setChecked(False)
        else:
            self.and_btn.setChecked(False)
            self.or_btn.setChecked(True)
    
    def _add_condition(self):
        """添加搜索条件"""
        # 在stretch之前插入
        index = len(self.condition_widgets)
        widget = SearchConditionWidget(index, self)
        widget.deleted.connect(self._remove_condition)
        
        self.condition_widgets.append(widget)
        self.conditions_layout.insertWidget(index, widget)
        
        self._update_status(_('search_added').format(index + 1))
    
    def _remove_condition(self, widget: SearchConditionWidget):
        """移除搜索条件"""
        if widget in self.condition_widgets:
            self.condition_widgets.remove(widget)
            widget.deleteLater()
            
            # 更新索引
            for i, w in enumerate(self.condition_widgets):
                w.index = i
                # 更新标题
                title_label = w.findChild(QLabel)
                if title_label:
                    title_label.setText(_('advanced_search_condition_title').format(i + 1))
            
            self._update_status(_('search_deleted').format(len(self.condition_widgets)))
            
            # 如果没有条件了，添加一个新的
            if not self.condition_widgets:
                self._add_condition()
    
    def _clear_all(self):
        """清空所有条件"""
        for widget in self.condition_widgets[:]:
            widget.deleteLater()
        self.condition_widgets.clear()
        self._add_condition()
        self._update_status(_('search_cleared'))
    
    def _execute_search(self):
        """执行搜索"""
        # 收集搜索条件
        conditions = []
        for widget in self.condition_widgets:
            condition_data = widget.get_condition_data()
            if condition_data:
                conditions.append(condition_data)
        
        if not conditions:
            self._update_status(_('search_error_no_condition'))
            return
        
        # 构建搜索条件（使用按钮状态）
        criteria = {
            'conditions': conditions,
            'match_mode': 'all' if self.and_btn.isChecked() else 'any',
            'fuzzy_search': True
        }
        
        try:
            self._update_status(f"正在搜索... (共 {len(conditions)} 个条件)")
            
            # 执行搜索回调
            result_count = self.on_search_callback(criteria)
            
            if result_count is not None:
                self._update_status(f"✓ 搜索完成：找到 {result_count} 个结果")
                self.search_completed.emit(result_count)
            else:
                self._update_status("✓ 搜索完成")
                
        except Exception as e:
            self._update_status(f"❌ 搜索失败：{str(e)}")
    
    def _update_status(self, text: str):
        """更新状态显示"""
        self.status_label.setText(text)
