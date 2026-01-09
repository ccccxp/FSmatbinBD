"""
材质替换对话框

按设计文档 V3 第六章实现：
- 状态机：Ready/Running/Completed/Canceled/Failed
- 顶部 Banner + 对话框内 Inline 反馈
- 左右对称预览区
- 转换选项面板
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import json
import time

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QFrame, QGroupBox, QComboBox, QLineEdit,
    QCheckBox, QScrollArea, QSplitter, QTreeWidget, QTreeWidgetItem,
    QProgressBar, QMessageBox, QSizePolicy, QFormLayout, QSpinBox,
    QApplication, QToolButton, QMenu
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer, QSettings
from PySide6.QtGui import QFont, QColor

from src.core.i18n import _
from src.core.material_replacer import (
    MaterialReplacer, Material, Sampler, ConversionOptions,
    MatchStatus, STATUS_ICONS, MatchResult, ReplaceResult, apply_replacement
)


class DialogState(Enum):
    """对话框状态"""
    READY = 'ready'
    RUNNING = 'running'
    COMPLETED = 'completed'
    CANCELED = 'canceled'
    FAILED = 'failed'


class ReplaceWorker(QThread):
    """替换工作线程"""
    progress = Signal(int, int)  # current, total
    finished = Signal(object)   # ReplaceResult or Exception
    
    def __init__(self, replacer: MaterialReplacer, source: Material, target: Material):
        super().__init__()
        self.replacer = replacer
        self.source = source
        self.target = target
        self._canceled = False
    
    def run(self):
        try:
            # 模拟进度（实际替换很快，但为了展示状态机）
            self.progress.emit(0, 1)
            result = self.replacer.replace(self.source, self.target)
            if self._canceled:
                return
            self.progress.emit(1, 1)
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit(e)
    
    def cancel(self):
        self._canceled = True


class BannerWidget(QFrame):
    """顶部 Banner 组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("banner")
        self._setup_ui()
        self.hide()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        
        self.icon_label = QLabel()
        self.icon_label.setFixedWidth(24)
        layout.addWidget(self.icon_label)
        
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label, 1)
        
        self.action_btn = QPushButton()
        self.action_btn.setVisible(False)
        layout.addWidget(self.action_btn)
        
        self.close_btn = QToolButton()
        self.close_btn.setText("×")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.clicked.connect(self.hide)
        layout.addWidget(self.close_btn)
    
    def show_info(self, message: str, icon: str = "ℹ️", closable: bool = True):
        self._set_style("info")
        self.icon_label.setText(icon)
        self.message_label.setText(message)
        self.close_btn.setVisible(closable)
        self.action_btn.setVisible(False)
        self.show()
    
    def show_success(self, message: str, icon: str = "✓"):
        self._set_style("success")
        self.icon_label.setText(icon)
        self.message_label.setText(message)
        self.close_btn.setVisible(True)
        self.action_btn.setVisible(False)
        self.show()
    
    def show_warning(self, message: str, icon: str = "⚠", action_text: str = "", action_callback=None):
        self._set_style("warning")
        self.icon_label.setText(icon)
        self.message_label.setText(message)
        self.close_btn.setVisible(True)
        if action_text and action_callback:
            self.action_btn.setText(action_text)
            self.action_btn.setVisible(True)
            try:
                self.action_btn.clicked.disconnect()
            except:
                pass
            self.action_btn.clicked.connect(action_callback)
        else:
            self.action_btn.setVisible(False)
        self.show()
    
    def show_error(self, message: str, icon: str = "✖"):
        self._set_style("error")
        self.icon_label.setText(icon)
        self.message_label.setText(message)
        self.close_btn.setVisible(False)  # 错误不可关闭
        self.action_btn.setVisible(False)
        self.show()
    
    def show_progress(self, message: str, icon: str = "⏳"):
        self._set_style("progress")
        self.icon_label.setText(icon)
        self.message_label.setText(message)
        self.close_btn.setVisible(False)
        self.action_btn.setVisible(False)
        self.show()
    
    def _set_style(self, style_type: str):
        styles = {
            "info": "background: rgba(88, 166, 255, 0.15); border: 1px solid rgba(88, 166, 255, 0.4); border-radius: 6px;",
            "success": "background: rgba(63, 185, 80, 0.15); border: 1px solid rgba(63, 185, 80, 0.4); border-radius: 6px;",
            "warning": "background: rgba(210, 153, 34, 0.15); border: 1px solid rgba(210, 153, 34, 0.4); border-radius: 6px;",
            "error": "background: rgba(248, 81, 73, 0.15); border: 1px solid rgba(248, 81, 73, 0.4); border-radius: 6px;",
            "progress": "background: rgba(136, 136, 136, 0.15); border: 1px solid rgba(136, 136, 136, 0.4); border-radius: 6px;",
        }
        self.setStyleSheet(f"QFrame#banner {{ {styles.get(style_type, styles['info'])} }}")


class SamplerPreviewItem(QFrame):
    """单个采样器预览项"""
    
    def __init__(self, sampler: Sampler, match_result: Optional[MatchResult] = None, is_target: bool = False, parent=None):
        super().__init__(parent)
        self.sampler = sampler
        self.match_result = match_result
        self.is_target = is_target
        self._setup_ui()
    
    def _setup_ui(self):
        self.setObjectName("samplerItem")
        self.setStyleSheet("""
            QFrame#samplerItem {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                margin: 2px;
            }
            QFrame#samplerItem:hover {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.12);
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        
        # 第一行：状态图标 + 序号 + 类型
        header = QHBoxLayout()
        
        # 状态图标
        status_icon = ""
        if self.match_result:
            status_icon = STATUS_ICONS.get(self.match_result.status, "")
        elif self.is_target:
            if not self.sampler.has_path:
                status_icon = STATUS_ICONS[MatchStatus.EMPTY]
        
        if status_icon:
            icon_label = QLabel(status_icon)
            icon_label.setFixedWidth(20)
            header.addWidget(icon_label)
        
        # 序号和类型 - 显示完整的 type_name
        type_text = self.sampler.type_name
        type_label = QLabel(type_text)
        type_label.setStyleSheet("font-weight: 500; color: rgba(255, 255, 255, 0.9);")
        header.addWidget(type_label, 1)
        
        # 顺序调整标记
        if self.match_result and self.match_result.order_adjusted:
            warn_label = QLabel("⚠")
            warn_label.setToolTip(self.match_result.adjustment_detail or _('replace_order_adjusted'))
            header.addWidget(warn_label)
        
        layout.addLayout(header)
        
        # 第二行：路径
        path_text = self.sampler.path if self.sampler.path else _('replace_empty_path')
        path_label = QLabel(path_text)
        path_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 9pt;")
        path_label.setWordWrap(True)
        path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(path_label)
        
        # 第三行：Scale（如果非默认）
        if self.sampler.scale_x != 1.0 or self.sampler.scale_y != 1.0:
            scale_label = QLabel(f"Scale: X={self.sampler.scale_x}, Y={self.sampler.scale_y}")
            scale_label.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 8pt;")
            layout.addWidget(scale_label)


class MaterialReplaceDialog(QDialog):
    """材质替换对话框"""
    
    def __init__(self, parent, database_manager, 
                 initial_source_library_id: Optional[int] = None,
                 initial_material_name: str = "",
                 current_material_data: Optional[Dict] = None):
        super().__init__(parent)
        self.db = database_manager
        self.initial_source_library_id = initial_source_library_id
        self.initial_material_name = initial_material_name
        self.current_material_data = current_material_data
        
        # 状态
        self._state = DialogState.READY
        self._worker: Optional[ReplaceWorker] = None
        self._result: Optional[ReplaceResult] = None
        self._applied_material: Optional[Material] = None
        self._has_manual_edits = False
        
        # 选项
        self._options = ConversionOptions()
        
        # 设置
        self._settings = QSettings("FSmatbinBD", "MaterialLibrary")
        
        # 应用深色标题栏
        try:
            from .dark_titlebar import apply_dark_titlebar_to_dialog
            apply_dark_titlebar_to_dialog(self)
        except:
            pass
        
        self.setWindowTitle(_('replace_dialog_title'))
        self.setModal(False)
        self.resize(1100, 750)
        
        self._build_ui()
        self._load_libraries()
        self._load_options()
        self._update_state(DialogState.READY)
    
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)
        
        # ===== 顶部 Banner =====
        self.banner = BannerWidget()
        root.addWidget(self.banner)
        
        # ===== 替换配置区 =====
        config_group = QGroupBox(_('replace_config_section'))
        config_layout = QHBoxLayout(config_group)
        
        # 左侧：当前材质
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel(_('replace_current_material')))
        
        self.current_material_label = QLabel()
        self.current_material_label.setStyleSheet("font-weight: 500; padding: 8px; background: rgba(255,255,255,0.05); border-radius: 4px;")
        self.current_material_label.setWordWrap(True)
        left_panel.addWidget(self.current_material_label)
        
        self.current_library_combo = QComboBox()
        self.current_library_combo.setEnabled(False)
        left_panel.addWidget(self.current_library_combo)
        
        config_layout.addLayout(left_panel, 1)
        
        # 中间：箭头
        arrow_label = QLabel("═══>")
        arrow_label.setStyleSheet("font-size: 16px; color: rgba(255,255,255,0.5);")
        arrow_label.setAlignment(Qt.AlignCenter)
        config_layout.addWidget(arrow_label)
        
        # 右侧：目标材质
        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel(_('replace_target_material')))
        
        self.target_search_edit = QLineEdit()
        self.target_search_edit.setPlaceholderText(_('replace_search_target'))
        self.target_search_edit.textChanged.connect(self._on_search_target)
        right_panel.addWidget(self.target_search_edit)
        
        self.target_library_combo = QComboBox()
        self.target_library_combo.currentIndexChanged.connect(self._on_target_library_changed)
        right_panel.addWidget(self.target_library_combo)
        
        self.target_material_combo = QComboBox()
        self.target_material_combo.setMaxVisibleItems(15)
        right_panel.addWidget(self.target_material_combo)
        
        config_layout.addLayout(right_panel, 1)
        
        root.addWidget(config_group)
        
        # ===== 转换选项区 =====
        options_group = QGroupBox(_('replace_options_section'))
        options_layout = QVBoxLayout(options_group)
        
        # 基础选项（始终显示）
        basic_options = QHBoxLayout()
        
        self.opt_simplify_texture = QCheckBox(_('replace_opt_simplify_texture'))
        self.opt_simplify_texture.setChecked(self._options.simplify_texture_path)
        basic_options.addWidget(self.opt_simplify_texture)
        
        self.opt_simplify_material = QCheckBox(_('replace_opt_simplify_material'))
        self.opt_simplify_material.setChecked(self._options.simplify_material_path)
        basic_options.addWidget(self.opt_simplify_material)
        
        self.opt_migrate_params = QCheckBox(_('replace_opt_migrate_params'))
        self.opt_migrate_params.setChecked(self._options.migrate_parameters)
        basic_options.addWidget(self.opt_migrate_params)
        
        basic_options.addStretch()
        options_layout.addLayout(basic_options)
        
        # 高级选项（可折叠）
        self.advanced_toggle = QCheckBox(_('replace_show_advanced'))
        self.advanced_toggle.toggled.connect(self._toggle_advanced_options)
        options_layout.addWidget(self.advanced_toggle)
        
        self.advanced_frame = QFrame()
        self.advanced_frame.setVisible(False)
        advanced_layout = QHBoxLayout(self.advanced_frame)
        advanced_layout.setContentsMargins(20, 0, 0, 0)
        
        self.opt_prefer_perfect = QCheckBox(_('replace_opt_prefer_perfect'))
        self.opt_prefer_perfect.setChecked(self._options.prefer_perfect_match)
        advanced_layout.addWidget(self.opt_prefer_perfect)
        
        self.opt_prefer_marked = QCheckBox(_('replace_opt_prefer_marked'))
        self.opt_prefer_marked.setChecked(self._options.prefer_marked_coverage)
        advanced_layout.addWidget(self.opt_prefer_marked)
        
        self.opt_allow_adjust = QCheckBox(_('replace_opt_allow_adjust'))
        self.opt_allow_adjust.setChecked(self._options.allow_order_adjustment)
        advanced_layout.addWidget(self.opt_allow_adjust)
        
        self.opt_strict_order = QCheckBox(_('replace_opt_strict_order'))
        self.opt_strict_order.setChecked(self._options.strict_order_validation)
        self.opt_strict_order.setToolTip(_('replace_opt_strict_order_hint'))
        advanced_layout.addWidget(self.opt_strict_order)
        
        advanced_layout.addStretch()
        options_layout.addWidget(self.advanced_frame)
        
        root.addWidget(options_group)
        
        # ===== 按钮区 =====
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton(_('replace_btn_start'))
        self.start_btn.setObjectName("primary")
        self.start_btn.clicked.connect(self._on_start)
        btn_layout.addWidget(self.start_btn)
        
        self.cancel_btn = QPushButton(_('replace_btn_cancel'))
        self.cancel_btn.clicked.connect(self._on_cancel)
        self.cancel_btn.setVisible(False)
        btn_layout.addWidget(self.cancel_btn)
        
        self.apply_btn = QPushButton(_('replace_btn_apply'))
        self.apply_btn.setObjectName("primary")
        self.apply_btn.clicked.connect(self._on_apply)
        self.apply_btn.setVisible(False)
        btn_layout.addWidget(self.apply_btn)
        
        btn_layout.addStretch()
        
        self.close_btn = QPushButton(_('replace_btn_close'))
        self.close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.close_btn)
        
        root.addLayout(btn_layout)
        
        # ===== 预览区 =====
        preview_group = QGroupBox(_('replace_preview_section'))
        preview_layout = QHBoxLayout(preview_group)
        
        # 左侧：源采样器列表
        left_preview = QVBoxLayout()
        left_preview.addWidget(QLabel(_('replace_source_samplers')))
        
        self.source_scroll = QScrollArea()
        self.source_scroll.setWidgetResizable(True)
        self.source_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.source_container = QWidget()
        self.source_layout = QVBoxLayout(self.source_container)
        self.source_layout.setAlignment(Qt.AlignTop)
        self.source_scroll.setWidget(self.source_container)
        left_preview.addWidget(self.source_scroll, 1)
        
        preview_layout.addLayout(left_preview, 1)
        
        # 右侧：目标采样器列表
        right_preview = QVBoxLayout()
        right_preview.addWidget(QLabel(_('replace_target_samplers')))
        
        self.target_scroll = QScrollArea()
        self.target_scroll.setWidgetResizable(True)
        self.target_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.target_container = QWidget()
        self.target_layout = QVBoxLayout(self.target_container)
        self.target_layout.setAlignment(Qt.AlignTop)
        self.target_scroll.setWidget(self.target_container)
        right_preview.addWidget(self.target_scroll, 1)
        
        preview_layout.addLayout(right_preview, 1)
        
        root.addWidget(preview_group, 1)
        
        # ===== 图例 =====
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(QLabel(_('replace_legend')))
        legend_layout.addWidget(QLabel(f"{STATUS_ICONS[MatchStatus.PERFECT_MATCH]} {_('status_perfect_match')}"))
        legend_layout.addWidget(QLabel(f"{STATUS_ICONS[MatchStatus.ADJACENT_MATCH]} {_('status_adjacent_match')}"))
        legend_layout.addWidget(QLabel(f"{STATUS_ICONS[MatchStatus.UNMATCHED]} {_('status_unmatched')}"))
        legend_layout.addWidget(QLabel(f"{STATUS_ICONS[MatchStatus.UNCOVERED]} {_('status_uncovered')}"))
        legend_layout.addWidget(QLabel(f"{STATUS_ICONS[MatchStatus.EMPTY]} {_('status_empty')}"))
        legend_layout.addStretch()
        root.addLayout(legend_layout)
    
    def _load_libraries(self):
        """加载材质库列表"""
        try:
            libraries = self.db.get_all_libraries()
            
            self.current_library_combo.clear()
            self.target_library_combo.clear()
            
            initial_source_index = 0
            for i, lib in enumerate(libraries):
                lib_id = lib.get('id', lib.get('library_id', 0))
                lib_name = lib.get('name', lib.get('library_name', ''))
                self.current_library_combo.addItem(lib_name, lib_id)
                self.target_library_combo.addItem(lib_name, lib_id)
                
                # 设置初始源库
                if self.initial_source_library_id and lib_id == self.initial_source_library_id:
                    initial_source_index = i
            
            # 设置当前库选择
            if initial_source_index > 0:
                self.current_library_combo.setCurrentIndex(initial_source_index)
            
            # 如果没有传入当前材质数据，尝试通过初始材质名搜索
            if not self.current_material_data and self.initial_material_name:
                self._search_and_load_initial_material()
            elif self.current_material_data:
                # 设置当前材质信息
                name = self.current_material_data.get('Name', self.current_material_data.get('name', ''))
                mtd = self.current_material_data.get('MTD', self.current_material_data.get('mtd_path', ''))
                self.current_material_label.setText(f"{name}\n{mtd}")
                # 加载源采样器预览
                self._load_source_preview()
            else:
                self.current_material_label.setText(_('replace_no_source_selected'))
                
        except Exception as e:
            self.banner.show_error(f"{_('replace_load_error')}: {e}")
    
    def _search_and_load_initial_material(self):
        """搜索并加载初始材质"""
        if not self.initial_material_name:
            return
        
        try:
            lib_id = self.current_library_combo.currentData()
            if lib_id:
                # 在指定库中搜索
                results = self.db.search_materials(self.initial_material_name, library_id=lib_id)
            else:
                # 全局搜索
                results = self.db.search_materials(self.initial_material_name)
            
            if results:
                # 获取第一个匹配结果的详细信息
                mat = results[0]
                mat_id = mat.get('id', mat.get('material_id', 0))
                self.current_material_data = self.db.get_material_detail(mat_id)
                
                if self.current_material_data:
                    name = self.current_material_data.get('Name', self.current_material_data.get('name', ''))
                    mtd = self.current_material_data.get('MTD', self.current_material_data.get('mtd_path', ''))
                    self.current_material_label.setText(f"{name}\n{mtd}")
                    self._load_source_preview()
                else:
                    self.current_material_label.setText(_('replace_no_source_selected'))
            else:
                self.current_material_label.setText(f"{_('replace_material_not_found')}: {self.initial_material_name}")
        except Exception as e:
            self.current_material_label.setText(f"{_('replace_load_error')}: {e}")
    
    def _load_source_preview(self):
        """加载源材质采样器预览"""
        # 清空
        while self.source_layout.count():
            item = self.source_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self.current_material_data:
            return
        
        textures = self.current_material_data.get('Textures', [])
        for i, tex in enumerate(textures):
            sampler = Sampler.from_dict(tex, i)
            item = SamplerPreviewItem(sampler, is_target=False)
            self.source_layout.addWidget(item)
        
        self.source_layout.addStretch()
    
    def _on_target_library_changed(self, index: int):
        """目标库改变时更新材质列表"""
        lib_id = self.target_library_combo.currentData()
        if lib_id is None:
            return
        
        try:
            materials = self.db.get_materials_by_library(lib_id)
            self.target_material_combo.clear()
            
            for mat in materials:
                mat_name = mat.get('name', mat.get('Name', ''))
                mat_id = mat.get('id', mat.get('material_id', 0))
                self.target_material_combo.addItem(mat_name, mat_id)
        except Exception as e:
            self.banner.show_error(f"{_('replace_load_materials_error')}: {e}")
    
    def _on_search_target(self, text: str):
        """搜索目标材质"""
        # 简单过滤（实际可以做模糊搜索）
        for i in range(self.target_material_combo.count()):
            item_text = self.target_material_combo.itemText(i)
            # 这里只是简单示例，实际可以用正则或模糊匹配
    
    def _toggle_advanced_options(self, checked: bool):
        """切换高级选项显示"""
        self.advanced_frame.setVisible(checked)
    
    def _load_options(self):
        """从设置加载选项"""
        try:
            self._options.simplify_texture_path = self._settings.value("replace/simplify_texture", False, type=bool)
            self._options.simplify_material_path = self._settings.value("replace/simplify_material", False, type=bool)
            self._options.migrate_parameters = self._settings.value("replace/migrate_params", True, type=bool)
            self._options.prefer_perfect_match = self._settings.value("replace/prefer_perfect", True, type=bool)
            self._options.prefer_marked_coverage = self._settings.value("replace/prefer_marked", True, type=bool)
            self._options.allow_order_adjustment = self._settings.value("replace/allow_adjust", True, type=bool)
            self._options.strict_order_validation = self._settings.value("replace/strict_order", True, type=bool)
            
            # 更新 UI
            self.opt_simplify_texture.setChecked(self._options.simplify_texture_path)
            self.opt_simplify_material.setChecked(self._options.simplify_material_path)
            self.opt_migrate_params.setChecked(self._options.migrate_parameters)
            self.opt_prefer_perfect.setChecked(self._options.prefer_perfect_match)
            self.opt_prefer_marked.setChecked(self._options.prefer_marked_coverage)
            self.opt_allow_adjust.setChecked(self._options.allow_order_adjustment)
            self.opt_strict_order.setChecked(self._options.strict_order_validation)
        except:
            pass
    
    def _save_options(self):
        """保存选项到设置"""
        self._settings.setValue("replace/simplify_texture", self.opt_simplify_texture.isChecked())
        self._settings.setValue("replace/simplify_material", self.opt_simplify_material.isChecked())
        self._settings.setValue("replace/migrate_params", self.opt_migrate_params.isChecked())
        self._settings.setValue("replace/prefer_perfect", self.opt_prefer_perfect.isChecked())
        self._settings.setValue("replace/prefer_marked", self.opt_prefer_marked.isChecked())
        self._settings.setValue("replace/allow_adjust", self.opt_allow_adjust.isChecked())
        self._settings.setValue("replace/strict_order", self.opt_strict_order.isChecked())
    
    def _collect_options(self) -> ConversionOptions:
        """从 UI 收集选项"""
        return ConversionOptions(
            simplify_texture_path=self.opt_simplify_texture.isChecked(),
            simplify_material_path=self.opt_simplify_material.isChecked(),
            migrate_parameters=self.opt_migrate_params.isChecked(),
            prefer_perfect_match=self.opt_prefer_perfect.isChecked(),
            prefer_marked_coverage=self.opt_prefer_marked.isChecked(),
            allow_order_adjustment=self.opt_allow_adjust.isChecked(),
            strict_order_validation=self.opt_strict_order.isChecked(),
        )
    
    def _update_state(self, new_state: DialogState):
        """更新对话框状态"""
        self._state = new_state
        
        # 更新按钮可见性
        self.start_btn.setVisible(new_state == DialogState.READY)
        self.cancel_btn.setVisible(new_state == DialogState.RUNNING)
        self.apply_btn.setVisible(new_state == DialogState.COMPLETED)
        
        # 更新控件可用性
        enable_config = new_state == DialogState.READY
        self.target_library_combo.setEnabled(enable_config)
        self.target_material_combo.setEnabled(enable_config)
        self.target_search_edit.setEnabled(enable_config)
        self.opt_simplify_texture.setEnabled(enable_config)
        self.opt_simplify_material.setEnabled(enable_config)
        self.opt_migrate_params.setEnabled(enable_config)
        self.opt_prefer_perfect.setEnabled(enable_config)
        self.opt_prefer_marked.setEnabled(enable_config)
        self.opt_allow_adjust.setEnabled(enable_config)
        self.opt_strict_order.setEnabled(enable_config)
        
        # 更新 Banner
        if new_state == DialogState.READY:
            self.banner.show_info(_('replace_ready_hint'), "💡")
        elif new_state == DialogState.RUNNING:
            self.banner.show_progress(_('replace_running'), "⏳")
        elif new_state == DialogState.COMPLETED:
            if self._result:
                ok = sum(1 for r in self._result.results if r.status in (MatchStatus.PERFECT_MATCH, MatchStatus.ADJACENT_MATCH))
                warn = sum(1 for r in self._result.results if r.order_adjusted)
                fail = sum(1 for r in self._result.results if r.status == MatchStatus.UNMATCHED)
                msg = _('replace_completed_summary').format(ok=ok, warn=warn, fail=fail)
                
                if warn > 0 or self._result.global_repair_triggered:
                    self.banner.show_warning(msg, "⚠")
                else:
                    self.banner.show_success(msg, "✓")
        elif new_state == DialogState.CANCELED:
            self.banner.show_info(_('replace_canceled'), "⛔")
        elif new_state == DialogState.FAILED:
            self.banner.show_error(_('replace_failed'))
    
    def _on_start(self):
        """开始转换"""
        if not self.current_material_data:
            QMessageBox.warning(self, _('replace_warning'), _('replace_no_source'))
            return
        
        target_mat_id = self.target_material_combo.currentData()
        if target_mat_id is None:
            QMessageBox.warning(self, _('replace_warning'), _('replace_no_target'))
            return
        
        # 获取目标材质详情
        try:
            target_data = self.db.get_material_detail(target_mat_id)
            if not target_data:
                QMessageBox.warning(self, _('replace_warning'), _('replace_target_not_found'))
                return
        except Exception as e:
            QMessageBox.critical(self, _('replace_error'), str(e))
            return
        
        # 构建材质对象
        source = Material.from_dict(self.current_material_data)
        target = Material.from_dict(target_data)
        
        # 收集选项
        options = self._collect_options()
        self._save_options()
        
        # 创建替换器并启动工作线程
        replacer = MaterialReplacer(options)
        
        self._worker = ReplaceWorker(replacer, source, target)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        
        self._update_state(DialogState.RUNNING)
        self._worker.start()
    
    def _on_cancel(self):
        """取消转换"""
        if self._worker:
            from src.gui_qt.standard_dialogs import show_confirm_dialog
            confirmed = show_confirm_dialog(
                self, _('replace_confirm'),
                _('replace_cancel_confirm'),
                confirm_style='danger'
            )
            if confirmed:
                self._worker.cancel()
                self._worker.wait()
                self._update_state(DialogState.CANCELED)
                self._clear_target_preview()
    
    def _on_progress(self, current: int, total: int):
        """更新进度"""
        if total > 0:
            msg = _('replace_progress').format(current=current, total=total)
            self.banner.show_progress(msg, "⏳")
    
    def _on_finished(self, result):
        """转换完成"""
        if isinstance(result, Exception):
            self._update_state(DialogState.FAILED)
            self.banner.show_error(f"{_('replace_error')}: {result}")
            return
        
        self._result = result
        self._update_state(DialogState.COMPLETED)
        self._render_result_preview()
    
    def _render_result_preview(self):
        """渲染替换结果预览"""
        if not self._result:
            return
        
        # 清空目标预览
        self._clear_target_preview()
        
        # 重新渲染源采样器（带匹配结果）
        while self.source_layout.count():
            item = self.source_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        source = self._result.source_material
        for i, sampler in enumerate(source.samplers):
            match_result = self._result.results[i] if i < len(self._result.results) else None
            item = SamplerPreviewItem(sampler, match_result, is_target=False)
            self.source_layout.addWidget(item)
        self.source_layout.addStretch()
        
        # 渲染目标采样器
        target = self._result.target_material
        matched_targets = set()
        
        for mr in self._result.results:
            if mr.target_pos is not None:
                matched_targets.add(mr.target_pos)
        
        for i, sampler in enumerate(target.samplers):
            # 查找对应的匹配结果
            match_result = None
            for mr in self._result.results:
                if mr.target_pos == i:
                    match_result = mr
                    break
            
            # 如果未被匹配且有路径，标记为 UNCOVERED
            if match_result is None and sampler.has_path:
                match_result = MatchResult(
                    source_pos=-1,
                    target_pos=i,
                    status=MatchStatus.UNCOVERED,
                    reason=_('replace_uncovered_reason'),
                )
            elif match_result is None and not sampler.has_path:
                match_result = MatchResult(
                    source_pos=-1,
                    target_pos=i,
                    status=MatchStatus.EMPTY,
                    reason="",
                )
            
            item = SamplerPreviewItem(sampler, match_result, is_target=True)
            self.target_layout.addWidget(item)
        
        self.target_layout.addStretch()
    
    def _clear_target_preview(self):
        """清空目标预览"""
        while self.target_layout.count():
            item = self.target_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _on_apply(self):
        """应用到纹理编辑"""
        if not self._result:
            return
        
        try:
            # 应用替换结果
            new_material = apply_replacement(
                self._result.source_material,
                self._result.target_material,
                self._result
            )
            self._applied_material = new_material
            
            # 发送信号给父窗口（这里简化处理，实际需要通过信号机制）
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, _('replace_error'), str(e))
    
    def get_applied_material(self) -> Optional[Dict[str, Any]]:
        """获取应用后的材质数据"""
        if self._applied_material:
            return self._applied_material.to_dict()
        return None
    
    def keyPressEvent(self, event):
        """处理快捷键"""
        if event.key() == Qt.Key_Escape:
            if self._state == DialogState.RUNNING:
                self._on_cancel()
            elif self._state == DialogState.COMPLETED and self._has_manual_edits:
                from src.gui_qt.standard_dialogs import show_confirm_dialog
                confirmed = show_confirm_dialog(
                    self, _('replace_confirm'),
                    _('replace_discard_edits'),
                    confirm_style='danger'
                )
                if confirmed:
                    self.reject()
            else:
                self.reject()
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if self._state == DialogState.READY:
                self._on_start()
            elif self._state == DialogState.COMPLETED:
                self._on_apply()
        elif event.key() == Qt.Key_F and event.modifiers() & Qt.ControlModifier:
            self.target_search_edit.setFocus()
            self.target_search_edit.selectAll()
        else:
            super().keyPressEvent(event)
    
    def closeEvent(self, event):
        """关闭事件"""
        if self._state == DialogState.RUNNING:
            from src.gui_qt.standard_dialogs import show_confirm_dialog
            confirmed = show_confirm_dialog(
                self, _('replace_confirm'),
                _('replace_close_while_running'),
                confirm_style='danger'
            )
            if not confirmed:
                event.ignore()
                return
            if self._worker:
                self._worker.cancel()
                self._worker.wait()
        
        super().closeEvent(event)
