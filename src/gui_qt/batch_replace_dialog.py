"""
批量替换材质对话框

按设计文档V3第六章 6.3 实现：
- 左右对称配置区
- 转换选项
- 状态机（Ready/Running/Completed/Canceled/Failed）
- 顶部Banner + 对话框内Inline反馈
- 预览区
"""

from typing import Optional, Dict, Any, List
from enum import Enum
import time

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QFrame, QGroupBox, QComboBox, QLineEdit,
    QCheckBox, QScrollArea, QSplitter, QTreeWidget, QTreeWidgetItem,
    QProgressBar, QMessageBox, QSizePolicy, QFormLayout, QSpinBox, QDoubleSpinBox,
    QApplication, QToolButton, QCompleter, QHeaderView,
    QListWidget, QListWidgetItem, QGridLayout
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer, QStringListModel, QEvent
from PySide6.QtGui import QFont, QColor, QIcon
import os
from src.utils.resource_path import get_assets_path

from src.core.i18n import _
from src.core.material_replace_models import (
    MaterialEntry, SamplerData, Vec2, ConversionOptions, MatchStatus, STATUS_ICONS,
    ReplaceResult as UIReplaceResult, MatchResult as UIMatchResult
)
from src.core.sampler_type_parser import get_sampler_display_name
from src.core.material_replacer import (
    MaterialReplacer, Material as CoreMaterial, Sampler as CoreSampler, 
    MatchResult as CoreMatchResult, ReplaceResult as CoreReplaceResult
)
from src.gui_qt.theme.palette import COLORS

# 从主题获取颜色
C = COLORS


class DialogState(Enum):
    """对话框状态（按设计文档 6.3.2.1）"""
    READY = 'ready'
    RUNNING = 'running'
    COMPLETED = 'completed'
    CANCELED = 'canceled'
    FAILED = 'failed'


class ReplaceWorker(QThread):
    """替换工作线程"""
    progress = Signal(int, int, str)  # current, total, current_item
    finished = Signal(object)          # CoreReplaceResult or Exception
    
    def __init__(self, source_material: MaterialEntry, target_material: MaterialEntry, options: ConversionOptions):
        super().__init__()
        self.source = source_material
        self.target = target_material
        self.options = options
        self._canceled = False
    
    def run(self):
        try:
            # 1. 转换模型 UI -> Core
            source_core = self._convert_to_core(self.source)
            target_core = self._convert_to_core(self.target)
            
            # 2. 执行替换
            self.replacer = MaterialReplacer(self.options)  # 存储到实例属性以便后续获取日志
            
            # 模拟进度 (MaterialReplacer 是同步的，这里只能做一个简单的模拟或者修改 replacer 支持 callback)
            # 由于 Core 逻辑是原子的，我们只能在开始前和结束后发送信号
            # 如果需要细粒度进度，需要修改 MaterialReplacer 支持 callback
            
            self.progress.emit(0, len(source_core.samplers), "Starting...")
            
            result = self.replacer.replace(source_core, target_core)
            
            time.sleep(0.5) # 稍微展示一下 Loading
            self.progress.emit(len(source_core.samplers), len(source_core.samplers), "Done")
            
            if self._canceled:
                return
            
            self.finished.emit(result)
            
        except Exception as e:
            self.finished.emit(e)
            
    def _convert_to_core(self, entry: MaterialEntry) -> CoreMaterial:
        from src.core.sampler_type_parser import parse_sampler_type
        samplers = []
        for s in entry.textures:
            core_sampler = CoreSampler(
                type_name=s.type_name,
                path=s.path,
                scale_x=s.scale.x,
                scale_y=s.scale.y,
                unk10=s.unk10,
                unk11=s.unk11,
                unk14=s.unk14,
                unk18=s.unk18,
                unk1c=s.unk1c,
                sorted_pos=s.sorted_pos
            )
            # 使用 parse_sampler_type 正确设置 index, base_type, is_legacy
            core_sampler.index, core_sampler.base_type, core_sampler.is_legacy = parse_sampler_type(s.type_name)
            samplers.append(core_sampler)
            
        return CoreMaterial(
            name=entry.name,
            mtd_path=entry.mtd,
            samplers=samplers,
            gx_index=entry.gx_index,
            index=entry.index
        )
    
    def cancel(self):
        self._canceled = True


class BannerWidget(QFrame):
    """顶部 Banner 组件（按设计文档 6.0.3）- 使用主题配色"""
    
    actionClicked = Signal()
    
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
        self.action_btn.clicked.connect(self.actionClicked.emit)
        layout.addWidget(self.action_btn)
        
        self.close_btn = QToolButton()
        self.close_btn.setText("×")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setStyleSheet(f"""
            QToolButton {{
                background: transparent;
                color: {C['fg_secondary']};
                border: none;
                font-size: 14px;
            }}
            QToolButton:hover {{
                color: {C['fg_primary']};
            }}
        """)
        self.close_btn.clicked.connect(self.hide)
        layout.addWidget(self.close_btn)
    
    def _set_style(self, style_type: str):
        """设置样式 - 使用主题配色"""
        colors = {
            'info': (C['accent'], 'rgba(47, 129, 247, 0.15)'),
            'success': (C['success'], 'rgba(63, 185, 80, 0.15)'),
            'warning': (C['warning'], 'rgba(227, 179, 65, 0.15)'),
            'error': (C['danger'], 'rgba(248, 81, 73, 0.15)'),
            'progress': (C['accent'], 'rgba(47, 129, 247, 0.15)'),
        }
        text_color, bg_color = colors.get(style_type, colors['info'])
        self.setStyleSheet(f"""
            QFrame#banner {{
                background-color: {bg_color};
                border: 1px solid {text_color};
                border-radius: 6px;
            }}
            QLabel {{
                color: {text_color};
                background: transparent;
            }}
        """)
    
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
    
    def show_warning(self, message: str, icon: str = "⚠", action_text: str = ""):
        self._set_style("warning")
        self.icon_label.setText(icon)
        self.message_label.setText(message)
        self.close_btn.setVisible(True)
        if action_text:
            self.action_btn.setText(action_text)
            self.action_btn.setVisible(True)
        else:
            self.action_btn.setVisible(False)
        self.show()
    
    def show_error(self, message: str, icon: str = "✖"):
        self._set_style("error")
        self.icon_label.setText(icon)
        self.message_label.setText(message)
        self.close_btn.setVisible(False)
        self.action_btn.setVisible(False)
        self.show()
    
    def show_progress(self, message: str, icon: str = "⏳"):
        self._set_style("progress")
        self.icon_label.setText(icon)
        self.message_label.setText(message)
        self.close_btn.setVisible(False)
        self.action_btn.setVisible(False)
        self.show()


class MaterialSearchWidget(QFrame):
    """
    统一的材质搜索组件（用于左右两侧）- 使用主题配色
    
    布局：
    - 第1行: [库下拉▼] [搜索框] [🔍] [🔄自动匹配（可选）]
    - 第2行: 搜索结果列表（选择后隐藏）
    - 第3行: 已选状态 + 路径显示
    """
    
    materialSelected = Signal(dict)  # 材质选择信号
    
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

    def __init__(self, db_manager=None, show_auto_match=False, parent=None):
        super().__init__(parent)
        self._db = db_manager
        self._show_auto_match = show_auto_match
        self._selected_material = None
        self._setup_ui()
        self._setup_style()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # 第1行：库下拉 + 搜索框 + 按钮
        search_row = QHBoxLayout()
        search_row.setSpacing(6)
        
        # 库下拉
        self.lib_combo = QComboBox()
        self.lib_combo.setMinimumWidth(80)
        self.lib_combo.setMinimumHeight(32)
        self.lib_combo.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        search_row.addWidget(self.lib_combo)
        
        # 搜索框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(_('search_material_placeholder'))
        self.search_edit.setMinimumHeight(32)
        self.search_edit.returnPressed.connect(self._perform_search)
        self.search_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        search_row.addWidget(self.search_edit, 1)
        
        # 搜索按钮
        search_wrapper = self.GlowButtonWrapper("🔍", "solid-blue", self._perform_search, color=(47, 129, 247))
        search_wrapper.setFixedSize(32, 32)
        search_wrapper.btn.setStyleSheet("padding: 0; font-size: 14px;") # 保持 font-size
        search_row.addWidget(search_wrapper)
        
        # 自动匹配按钮（可选）
        if self._show_auto_match:
            self.auto_match_btn = QPushButton("🔄")
            self.auto_match_btn.setFixedSize(28, 28)
            self.auto_match_btn.setToolTip(_('auto_match'))
            self.auto_match_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.auto_match_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {C['bg_tertiary']};
                    border: 1px solid {C['border_subtle']};
                    border-radius: 4px;
                    font-size: 14px;
                    padding: 0;
                }}
                QPushButton:hover {{
                    background-color: {C['accent_soft']};
                    border: 1px solid {C['accent']};
                }}
            """)
            search_row.addWidget(self.auto_match_btn)
        
        layout.addLayout(search_row)
        
        # 第2行：搜索结果列表（选择后隐藏）
        self.result_list = QListWidget()
        self.result_list.setMaximumHeight(100)
        self.result_list.setVisible(False)
        self.result_list.itemClicked.connect(self._on_result_selected)
        self.result_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.result_list.setStyleSheet(f"""
            QListWidget {{
                background: {C['bg_tertiary']};
                border: 1px solid {C['border_subtle']};
                border-radius: 4px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 4px 8px;
                color: {C['fg_primary']};
            }}
            QListWidget::item:hover {{
                background-color: {C['accent_soft']};
            }}
            QListWidget::item:selected {{
                background-color: {C['accent']};
                color: #ffffff;
            }}
        """)
        layout.addWidget(self.result_list)
        
        # 第3行：已选状态 + 路径
        status_layout = QVBoxLayout()
        status_layout.setSpacing(2)
        
        self.status_label = QLabel()
        status_layout.addWidget(self.status_label)
        
        self.path_label = QLabel()
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        status_layout.addWidget(self.path_label)
        
        layout.addLayout(status_layout)
    
    def _setup_style(self):
        """设置主题样式"""
        # 设置对象名以便根据ID设置样式
        self.setObjectName("MaterialSearchWidget")
        
        # 设置透明背景，去边框（仅针对自身）
        self.setStyleSheet("#MaterialSearchWidget { background: transparent; border: none; }")
        
        # 设置搜索框和下拉框样式
        self.lib_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {C['input_bg']};
                border: 1px solid {C['input_border']};
                border-radius: 4px;
                padding: 4px 8px;
                color: {C['fg_primary']};
            }}
            QComboBox:hover {{
                border: 1px solid {C['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {C['bg_secondary']};
                border: 1px solid {C['border_subtle']};
                selection-background-color: {C['accent']};
                selection-color: #ffffff;
            }}
        """)
        self.search_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {C['input_bg']};
                border: 1px solid {C['input_border']};
                border-radius: 4px;
                padding: 4px 8px;
                color: {C['fg_primary']};
            }}
            QLineEdit:focus {{
                border: 1px solid {C['accent']};
            }}
        """)
    
    def load_libraries(self, libraries: List[dict]):
        """加载库列表"""
        self.lib_combo.clear()
        self.lib_combo.addItem(_('all_libraries'), None)
        for lib in libraries:
            self.lib_combo.addItem(lib['name'], lib['id'])
    
    def set_search_text(self, text: str):
        """设置搜索框文本"""
        self.search_edit.setText(text)
    
    def set_status(self, matched: bool, text: str = ""):
        """设置匹配状态"""
        if matched:
            self.status_label.setText(f"✅ {text or _('matched')}")
            self.status_label.setStyleSheet(f"font-weight: bold; color: {C['success']}; border: none;")
        else:
            self.status_label.setText(f"❓ {text or _('not_found')}")
            self.status_label.setStyleSheet(f"font-weight: bold; color: {C['warning']}; border: none;")
    
    def set_path(self, path: str):
        """设置路径显示"""
        self.path_label.setText(f"{_('path')}: {path}")
        self.path_label.setStyleSheet(f"color: {C['fg_muted']}; font-size: 10px; border: none;")
    
    def set_selected(self, name: str, path: str):
        """设置已选材质"""
        self.status_label.setText(f"✅ {_('selected')}: {name}")
        self.status_label.setStyleSheet(f"font-weight: bold; color: {C['success']}; border: none;")
        self.path_label.setText(f"{_('path')}: {path}")
        self.path_label.setStyleSheet(f"color: {C['fg_muted']}; font-size: 10px; border: none;")
        self.result_list.setVisible(False)
    
    def _perform_search(self):
        """执行搜索"""
        if not self._db:
            return
        
        keyword = self.search_edit.text().strip()
        if not keyword:
            self.result_list.setVisible(False)
            return
        
        lib_id = self.lib_combo.currentData()
        results = self._db.search_materials(library_id=lib_id, keyword=keyword)
        
        self.result_list.clear()
        if results:
            for res in results[:20]:  # 限制20条
                item = QListWidgetItem(f"{res['filename']} ({res.get('library_name', '')})")
                item.setData(Qt.ItemDataRole.UserRole, res)
                item.setToolTip(res.get('filename', ''))
                self.result_list.addItem(item)
            # 动态调整高度
            item_height = 24
            list_height = min(len(results), 5) * item_height + 10
            self.result_list.setMaximumHeight(list_height)
            self.result_list.setVisible(True)
        else:
            self.result_list.setVisible(False)
            self.set_status(False)
    
    def _on_result_selected(self, item: QListWidgetItem):
        """选择搜索结果"""
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            self._selected_material = data
            name = data.get('filename', '')
            # 显示材质文件名（如 C[c2030]_AM.matxml），而非着色器路径
            # filename 就是材质文件名，这是用户期望看到的路径
            path = data.get('filename', '') or data.get('source_path', '')
            self.set_selected(name, path)
            self.materialSelected.emit(data)
    
    def get_selected_material(self) -> Optional[dict]:
        """获取已选材质"""
        return self._selected_material


class EditableSamplerCard(QFrame):
    """
    可编辑采样器卡片（按设计文档6.3.3）- 使用主题配色
    
    简化布局：
    1. 采样器类型名称
    2. 路径输入框
    3. X/Y缩放值（紧凑显示）
    4. 更多参数（默认隐藏）
    
    使用边框颜色表示匹配状态
    """
    
    dataChanged = Signal()
    
    # 状态对应的边框颜色
    STATUS_BORDER_COLORS = {
        MatchStatus.PERFECT_MATCH: C['success'],      # 绿色 - 完美匹配
        MatchStatus.ADJACENT_MATCH: C['warning'],     # 黄色 - 相邻匹配
        MatchStatus.UNMATCHED: C['danger'],           # 红色 - 未匹配
        MatchStatus.UNCOVERED: C['accent'],           # 蓝色 - 未覆盖
        MatchStatus.EMPTY: C['fg_muted'],             # 灰色 - 空
    }
    
    def __init__(self, sampler: SamplerData, match_status: MatchStatus = None, editable: bool = True, parent=None):
        super().__init__(parent)
        self._sampler = sampler
        self._match_status = match_status
        self._editable = editable
        self._show_more = False
        self._setup_ui()
        self._setup_style()
        self._load_data()
    
    def _get_border_color(self) -> str:
        """获取当前状态对应的边框颜色"""
        return self.STATUS_BORDER_COLORS.get(self._match_status, C['border_subtle'])
    
    def _setup_style(self):
        """设置卡片样式 - 使用边框颜色表示状态"""
        border_color = self._get_border_color()
        border_width = "2px" if self._match_status else "1px"
        
        self.setStyleSheet(f"""
            EditableSamplerCard {{
                background-color: {C['bg_tertiary']};
                border: {border_width} solid {border_color};
                border-radius: 8px;
            }}
            EditableSamplerCard:hover {{
                background-color: rgba(47, 129, 247, 18);
            }}
            QLabel {{
                color: {C['fg_primary']};
                background: transparent;
                border: none;
            }}
            QLineEdit {{
                background-color: {C['input_bg']};
                border: 1px solid {C['input_border']};
                border-radius: 4px;
                padding: 3px 6px;
                color: {C['fg_primary']};
                font-size: 9pt;
            }}
            QLineEdit:focus {{
                border: 1px solid {C['accent']};
            }}
            QLineEdit:read-only {{
                background-color: {C['bg_secondary']};
                border: 1px solid {C['border_subtle']};
                color: {C['fg_secondary']};
            }}
            QLineEdit[placeholderText] {{
                color: {C['fg_muted']};
            }}
            QDoubleSpinBox, QSpinBox {{
                background-color: {C['input_bg']};
                border: 1px solid {C['input_border']};
                border-radius: 4px;
                padding: 2px 4px;
                color: {C['fg_primary']};
                font-size: 9pt;
            }}
            QDoubleSpinBox:focus, QSpinBox:focus {{
                border: 1px solid {C['accent']};
            }}
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 0px;
                border: none;
            }}
            QCheckBox {{
                color: {C['fg_secondary']};
                background: transparent;
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border: 2px solid {C['accent']};
                border-radius: 3px;
                background: transparent;
            }}
            QCheckBox::indicator:checked {{
                background: {C['accent']};
            }}
        """)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(4)
        
        # 第1行：采样器类型名称（显示完整名称，与纹理编辑窗口一致）
        row1 = QHBoxLayout()
        row1.setSpacing(6)
        
        # 显示采样器类型名称（黄色），旧版采样器带中文备注
        from src.core.sampler_type_parser import parse_sampler_type, LEGACY_SAMPLER_ANNOTATIONS
        _idx, base_type, is_legacy = parse_sampler_type(self._sampler.type_name)
        if is_legacy and base_type:
            annotation = LEGACY_SAMPLER_ANNOTATIONS.get(base_type, '')
            display_name = f"{self._sampler.type_name}({annotation})" if annotation else self._sampler.type_name
        else:
            display_name = self._sampler.type_name  # 保持完整的采样器类型名
        self.name_label = QLabel(display_name)
        self.name_label.setStyleSheet(f"font-weight: bold; color: {C['warning']};")  # 使用黄色
        self.name_label.setToolTip(self._sampler.type_name)  # 完整名称作为提示
        row1.addWidget(self.name_label)
        row1.addStretch()
        layout.addLayout(row1)
        
        # 第2行：路径输入框（带标签）
        row2 = QHBoxLayout()
        row2.setSpacing(4)
        
        path_label = QLabel(_('path') + ":")
        path_label.setStyleSheet(f"color: {C['fg_muted']}; font-size: 9pt;")
        path_label.setFixedWidth(32)
        row2.addWidget(path_label)
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText(_('texture_path_placeholder') if self._editable else '')
        self.path_edit.setReadOnly(not self._editable)
        self.path_edit.textChanged.connect(self._on_data_changed)
        row2.addWidget(self.path_edit, 1)
        
        # XY值紧凑显示（直接用只读编辑框，没有上下按钮）
        x_label = QLabel("X:")
        x_label.setStyleSheet(f"color: {C['fg_muted']}; font-size: 9pt;")
        x_label.setFixedWidth(14)
        row2.addWidget(x_label)
        
        self.scale_x = QDoubleSpinBox()
        self.scale_x.setRange(-1000, 1000)
        self.scale_x.setDecimals(2)  # 保留2位小数以便手动输入
        self.scale_x.setSingleStep(1)  # 默认按整数递增/递减
        self.scale_x.setFixedWidth(55)
        self.scale_x.setReadOnly(not self._editable)
        self.scale_x.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.scale_x.valueChanged.connect(self._on_data_changed)
        row2.addWidget(self.scale_x)
        
        y_label = QLabel("Y:")
        y_label.setStyleSheet(f"color: {C['fg_muted']}; font-size: 9pt;")
        y_label.setFixedWidth(14)
        row2.addWidget(y_label)
        
        self.scale_y = QDoubleSpinBox()
        self.scale_y.setRange(-1000, 1000)
        self.scale_y.setDecimals(2)  # 保留2位小数以便手动输入
        self.scale_y.setSingleStep(1)  # 默认按整数递增/递减
        self.scale_y.setFixedWidth(55)
        self.scale_y.setReadOnly(not self._editable)
        self.scale_y.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.scale_y.valueChanged.connect(self._on_data_changed)
        row2.addWidget(self.scale_y)
        
        layout.addLayout(row2)
        
        # 第3行：更多参数（默认隐藏）
        self.more_widget = QWidget()
        more_layout = QHBoxLayout(self.more_widget)
        more_layout.setContentsMargins(0, 2, 0, 0)
        more_layout.setSpacing(6)
        
        # Unk10
        more_layout.addWidget(QLabel("Unk10:"))
        self.unk10_spin = QSpinBox()
        self.unk10_spin.setRange(-999999, 999999)
        self.unk10_spin.setFixedWidth(60)
        self.unk10_spin.setReadOnly(not self._editable)
        self.unk10_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.unk10_spin.valueChanged.connect(self._on_data_changed)
        more_layout.addWidget(self.unk10_spin)
        
        # Unk11
        self.unk11_check = QCheckBox("Unk11")
        self.unk11_check.setEnabled(self._editable)
        self.unk11_check.stateChanged.connect(self._on_data_changed)
        more_layout.addWidget(self.unk11_check)
        
        # Unk14
        more_layout.addWidget(QLabel("Unk14:"))
        self.unk14_spin = QSpinBox()
        self.unk14_spin.setRange(-999999, 999999)
        self.unk14_spin.setFixedWidth(60)
        self.unk14_spin.setReadOnly(not self._editable)
        self.unk14_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.unk14_spin.valueChanged.connect(self._on_data_changed)
        more_layout.addWidget(self.unk14_spin)
        
        # Unk18
        more_layout.addWidget(QLabel("Unk18:"))
        self.unk18_spin = QSpinBox()
        self.unk18_spin.setRange(-999999, 999999)
        self.unk18_spin.setFixedWidth(60)
        self.unk18_spin.setReadOnly(not self._editable)
        self.unk18_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.unk18_spin.valueChanged.connect(self._on_data_changed)
        more_layout.addWidget(self.unk18_spin)
        
        # Unk1C
        more_layout.addWidget(QLabel("Unk1C:"))
        self.unk1c_spin = QSpinBox()
        self.unk1c_spin.setRange(-999999, 999999)
        self.unk1c_spin.setFixedWidth(60)
        self.unk1c_spin.setReadOnly(not self._editable)
        self.unk1c_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
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
        self.dataChanged.emit()
    
    def set_show_more(self, show: bool):
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
    
    def set_match_status(self, status: MatchStatus):
        """更新匹配状态并刷新样式"""
        self._match_status = status
        self._setup_style()
        # 名称标签保持黄色不变，与纹理编辑窗口一致
    
    def set_path_source(self, from_user: bool):
        """设置路径来源提示
        
        Args:
            from_user: True=来自用户JSON, False=来自数据库
        """
        if from_user:
            # 默认样式
            self.path_edit.setStyleSheet(f"""
                background-color: {C['input_bg']};
                border: 1px solid {C['input_border']};
                border-radius: 4px;
                padding: 3px 6px;
                color: {C['fg_primary']};
            """)
            self.path_edit.setToolTip(_('path_from_user'))
        else:
            # 绿色字体表示来自数据库
            self.path_edit.setStyleSheet(f"""
                background-color: {C['input_bg']};
                border: 1px solid {C['input_border']};
                border-radius: 4px;
                padding: 3px 6px;
                color: {C['success']};
            """)
            self.path_edit.setToolTip(_('path_from_database'))


class BatchReplaceDialog(QDialog):
    """
    批量替换材质对话框
    
    按设计文档 6.3 实现
    """
    
    # 信号
    resultApplied = Signal(dict)  # {'mtd': str, 'samplers': List[SamplerData]}
    cacheUpdated = Signal(dict)   # 缓存更新信号
    
    def __init__(
        self,
        parent=None,
        source_material: MaterialEntry = None,
        database_manager=None,
        cached_state: Dict[str, Any] = None,  # 缓存状态
    ):
        super().__init__(parent)
        
        self._source_material = source_material
        self._db = database_manager
        self._cached_state = cached_state
        
        self._state = DialogState.READY
        self._worker: Optional[ReplaceWorker] = None
        self._result: Optional[UIReplaceResult] = None
        self._conversion_options = ConversionOptions()
        
        self._target_material: Optional[MaterialEntry] = None
        self._current_library_id: Optional[int] = None
        self._db_source_entry: Optional[MaterialEntry] = None  # 数据库中的源材质信息
        self._original_user_material: Optional[MaterialEntry] = source_material  # 保存原始用户材质
        self._initial_source_material: Optional[MaterialEntry] = None  # 首次进入时的源材质状态（用于还原）
        
        self._setup_ui()
        self._load_libraries()
        self._update_state(DialogState.READY)
        
        # 设置窗口属性
        self.setWindowTitle(_('batch_replace_material'))
        
        # 应用深色标题栏
        from src.gui_qt.dark_titlebar import apply_dark_titlebar_to_dialog
        apply_dark_titlebar_to_dialog(self)
        
        # 设置窗口图标
        try:
            icon_path = get_assets_path("app_icon.png")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass
        
        self.setMinimumSize(960, 700)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Window)
    
    def _setup_ui(self):
        """设置UI布局 - 使用主题配色"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)
        
        # ========== 顶部状态栏 ==========
        self.banner = BannerWidget()
        self.banner.actionClicked.connect(self._on_banner_action)
        layout.addWidget(self.banner)
        
        # ========== 顶部配置区（水平布局，两侧材质选择） ==========
        config_layout = QHBoxLayout()
        config_layout.setSpacing(16)
        
        # 左侧：源材质
        source_frame = QFrame()
        source_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {C['bg_secondary']};
                border: 1px solid {C['border_subtle']};
                border-radius: 8px;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        source_frame_layout = QVBoxLayout(source_frame)
        source_frame_layout.setContentsMargins(10, 8, 10, 8)
        source_frame_layout.setSpacing(4)
        
        source_title = QLabel(f"📦 {_('current_material')}")
        source_title.setStyleSheet(f"font-weight: bold; color: {C['warning']}; background: transparent; border: none;")
        source_frame_layout.addWidget(source_title)
        
        self.source_search_widget = MaterialSearchWidget(
            db_manager=self._db, show_auto_match=False, parent=self
        )
        self.source_search_widget.materialSelected.connect(self._on_source_material_selected)
        source_frame_layout.addWidget(self.source_search_widget)
        config_layout.addWidget(source_frame, 1)
        
        # 中间：箭头
        arrow_label = QLabel("→")
        arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow_label.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {C['accent']}; background: transparent;")
        arrow_label.setFixedWidth(40)
        config_layout.addWidget(arrow_label)
        
        # 右侧：目标材质
        target_frame = QFrame()
        target_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {C['bg_secondary']};
                border: 1px solid {C['border_subtle']};
                border-radius: 8px;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        target_frame_layout = QVBoxLayout(target_frame)
        target_frame_layout.setContentsMargins(10, 8, 10, 8)
        target_frame_layout.setSpacing(4)
        
        target_title = QLabel(f"✨ {_('replace_with')}")
        target_title.setStyleSheet(f"font-weight: bold; color: {C['success']}; background: transparent; border: none;")
        target_frame_layout.addWidget(target_title)
        
        self.target_search_widget = MaterialSearchWidget(
            db_manager=self._db, show_auto_match=False, parent=self
        )
        self.target_search_widget.materialSelected.connect(self._on_target_material_selected)
        target_frame_layout.addWidget(self.target_search_widget)
        config_layout.addWidget(target_frame, 1)
        
        layout.addLayout(config_layout)
        
        # ========== 预览区（占据大部分空间） ==========
        preview_frame = QFrame()
        preview_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {C['bg_secondary']};
                border: 1px solid {C['border_subtle']};
                border-radius: 8px;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        preview_frame_layout = QVBoxLayout(preview_frame)
        preview_frame_layout.setContentsMargins(10, 8, 10, 8)
        preview_frame_layout.setSpacing(6)
        
        # 预览标题栏
        preview_header = QHBoxLayout()
        preview_header.setSpacing(12)
        
        preview_title = QLabel(f"📋 {_('replacement_preview')}")
        preview_title.setStyleSheet(f"font-weight: bold; color: {C['accent']}; background: transparent; border: none;")
        preview_header.addWidget(preview_title)
        
        preview_header.addStretch()
        
        self.show_more_check = QCheckBox(_('show_more_parameters'))
        self.show_more_check.setStyleSheet(f"""
            QCheckBox {{
                color: {C['fg_secondary']};
                background: transparent;
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 2px solid {C['accent']};
                border-radius: 3px;
                background: transparent;
            }}
            QCheckBox::indicator:checked {{
                background: {C['accent']};
                image: url(src/gui_qt/assets/checkbox_check_white.svg);
            }}
        """)
        self.show_more_check.stateChanged.connect(self._on_show_more_changed)
        preview_header.addWidget(self.show_more_check)
        
        self.restore_btn = QPushButton("↩ " + _('restore_source'))
        self.restore_btn.setObjectName("danger")
        self.restore_btn.clicked.connect(self._on_restore_source)
        self.restore_btn.setEnabled(False)
        preview_header.addWidget(self.restore_btn)
        
        preview_frame_layout.addLayout(preview_header)
        
        # 双栏预览（使用 Splitter 可调整）
        preview_splitter = QSplitter(Qt.Orientation.Horizontal)
        preview_splitter.setHandleWidth(3)
        preview_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {C['border_subtle']};
            }}
            QSplitter::handle:hover {{
                background-color: {C['accent']};
            }}
        """)
        
        # 左侧预览：源材质采样器
        left_panel = QWidget()
        left_panel.setStyleSheet(f"""
            QWidget {{
                background: {C['bg_tertiary']};
                border-radius: 6px;
            }}
        """)
        left_panel_layout = QVBoxLayout(left_panel)
        left_panel_layout.setContentsMargins(8, 8, 8, 8)
        left_panel_layout.setSpacing(4)
        
        left_header = QLabel(f"📦 {_('source_samplers')}")
        left_header.setStyleSheet(f"font-weight: bold; color: {C['warning']}; padding: 4px; background: transparent; border: none;")
        left_panel_layout.addWidget(left_header)
        
        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.left_scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: {C['bg_secondary']};
                width: 8px;
                border-radius: 4px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {C['border_strong']};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {C['accent']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)
        self.left_preview_container = QWidget()
        self.left_preview_container.setStyleSheet("background: transparent;")
        self.left_preview_layout = QVBoxLayout(self.left_preview_container)
        self.left_preview_layout.setContentsMargins(0, 0, 0, 0)
        self.left_preview_layout.setSpacing(6)
        self.left_scroll.setWidget(self.left_preview_container)
        left_panel_layout.addWidget(self.left_scroll, 1)
        
        preview_splitter.addWidget(left_panel)
        
        # 右侧预览：结果采样器
        right_panel = QWidget()
        right_panel.setStyleSheet(f"""
            QWidget {{
                background: {C['bg_tertiary']};
                border-radius: 6px;
            }}
        """)
        right_panel_layout = QVBoxLayout(right_panel)
        right_panel_layout.setContentsMargins(8, 8, 8, 8)
        right_panel_layout.setSpacing(4)
        
        right_header = QLabel(f"✨ {_('result_samplers')}")
        right_header.setStyleSheet(f"font-weight: bold; color: {C['success']}; padding: 4px; background: transparent; border: none;")
        right_panel_layout.addWidget(right_header)
        
        self.right_scroll = QScrollArea()
        self.right_scroll.setWidgetResizable(True)
        self.right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.right_scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: {C['bg_secondary']};
                width: 8px;
                border-radius: 4px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {C['border_strong']};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {C['accent']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)
        self.right_preview_container = QWidget()
        self.right_preview_container.setStyleSheet("background: transparent;")
        self.right_preview_layout = QVBoxLayout(self.right_preview_container)
        self.right_preview_layout.setContentsMargins(0, 0, 0, 0)
        self.right_preview_layout.setSpacing(6)
        self.right_scroll.setWidget(self.right_preview_container)
        right_panel_layout.addWidget(self.right_scroll, 1)
        
        preview_splitter.addWidget(right_panel)
        preview_splitter.setSizes([500, 500])  # 初始均等宽度
        
        preview_frame_layout.addWidget(preview_splitter, 1)
        
        # 图例（使用边框颜色示例）
        legend_layout = QHBoxLayout()
        legend_layout.setSpacing(12)
        legend_label = QLabel(_('legend') + ":")
        legend_label.setStyleSheet(f"color: {C['fg_muted']}; background: transparent; border: none;")
        legend_layout.addWidget(legend_label)
        
        # 图例项目 - 使用翻译后的中文标签
        legend_items = [
            (C['success'], _('perfect_match')),
            (C['warning'], _('adjacent_match')),
            (C['danger'], _('unmatched')),
            (C['accent'], _('uncovered')),
            (C['fg_muted'], _('empty')),
        ]
        for color, text in legend_items:
            # 创建一个小的颜色块
            color_block = QFrame()
            color_block.setFixedSize(12, 12)
            color_block.setStyleSheet(f"""
                QFrame {{
                    background-color: {color};
                    border-radius: 2px;
                }}
            """)
            legend_layout.addWidget(color_block)
            
            lbl = QLabel(text)
        # 修复：标签边框
            lbl.setStyleSheet(f"color: {C['fg_secondary']}; font-size: 11px; background: transparent; border: none;")  
            legend_layout.addWidget(lbl)
        
        legend_layout.addStretch()
        
        # 显示日志按钮
        self.show_log_btn = QPushButton("📜 " + _('show_log'))
        self.show_log_btn.setObjectName("glass")
        self.show_log_btn.clicked.connect(self._on_show_log_clicked)
        legend_layout.addWidget(self.show_log_btn)
        
        preview_frame_layout.addLayout(legend_layout)
        
        layout.addWidget(preview_frame, 1)  # 预览区占据剩余空间
        
        # ========== 底部按钮区 ==========
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        # 左侧：选项复选框
        options_layout = QHBoxLayout()
        options_layout.setSpacing(16)
        
        checkbox_style = f"""
            QCheckBox {{
                color: {C['fg_secondary']};
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border: 2px solid {C['accent']};
                border-radius: 3px;
                background: transparent;
            }}
            QCheckBox::indicator:checked {{
                background: {C['accent']};
            }}
        """
        
        self.simplify_texture_check = QCheckBox(_('simplify_texture_path'))
        self.simplify_texture_check.setStyleSheet(checkbox_style)
        options_layout.addWidget(self.simplify_texture_check)
        
        self.simplify_material_check = QCheckBox(_('simplify_material_path'))
        self.simplify_material_check.setStyleSheet(checkbox_style)
        options_layout.addWidget(self.simplify_material_check)
        
        self.migrate_params_check = QCheckBox(_('migrate_parameters'))
        self.migrate_params_check.setChecked(True)
        self.migrate_params_check.setStyleSheet(checkbox_style)
        options_layout.addWidget(self.migrate_params_check)
        
        btn_layout.addLayout(options_layout)
        btn_layout.addStretch()
        
        # 应用按钮 (开始替换)
        self.apply_btn = QPushButton(f"▶ {_('start_replace')}")
        self.apply_btn.setObjectName("primary")
        self.apply_btn.clicked.connect(self._apply_result)
        
        # ... (other code)

        # 右侧：按钮
        self.main_btn = QPushButton()
        self.main_btn.setObjectName("primary")
        self.main_btn.setMinimumWidth(140)
        self.main_btn.setMinimumHeight(32)
        self.main_btn.clicked.connect(self._on_main_btn_clicked)
        btn_layout.addWidget(self.main_btn)
        
        self.cancel_btn = QPushButton(_('cancel'))
        self.cancel_btn.setObjectName("glass")
        self.cancel_btn.setMinimumHeight(32)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        
        # 初始化结果卡片列表
        self._result_cards = []
        
        # 加载源材质信息并自动显示预览
        if self._source_material:
            # 从材质路径中提取文件名作为搜索关键词
            import os
            mtd_path = self._source_material.mtd
            filename = os.path.basename(mtd_path)
            if filename.endswith('.matxml'):
                filename = filename[:-7]
            
            self.source_search_widget.set_search_text(filename)
            self.source_search_widget.set_path(mtd_path)
            self._auto_search_source()
            
            # 首次进入时自动显示左侧预览（根据用户JSON是否有路径决定数据来源）
            self._init_source_preview()
        
        # 恢复缓存状态
        if self._cached_state:
            self._restore_cache(self._cached_state)
    
    def _restore_cache(self, cache: Dict[str, Any]):
        """恢复缓存状态"""
        try:
            # 恢复目标材质搜索文本
            if 'target_search_text' in cache:
                self.target_search_widget.set_search_text(cache['target_search_text'])
            
            # 恢复选项
            if 'simplify_texture' in cache:
                self.simplify_texture_check.setChecked(cache['simplify_texture'])
            if 'simplify_material' in cache:
                self.simplify_material_check.setChecked(cache['simplify_material'])
            if 'migrate_params' in cache:
                self.migrate_params_check.setChecked(cache['migrate_params'])
            if 'show_more' in cache:
                self.show_more_check.setChecked(cache['show_more'])
            
            # 恢复目标材质并重新执行替换
            if 'target_material_id' in cache and self._db:
                detail = self._db.get_material_detail(cache['target_material_id'])
                if detail:
                    self._target_material = self._convert_db_to_entry(detail)
                    # 设置目标搜索框状态
                    self.target_search_widget.set_selected(
                        self._target_material.name, 
                        self._target_material.mtd
                    )
                    # 自动执行替换预览
                    self._auto_preview()
            
            # 恢复编辑后的采样器数据
            if 'edited_samplers' in cache and self._result_cards:
                for i, sampler_dict in enumerate(cache['edited_samplers']):
                    if i < len(self._result_cards):
                        sampler = SamplerData.from_dict(sampler_dict, i)
                        card = self._result_cards[i]
                        card.path_edit.setText(sampler.path)
                        card.scale_x.setValue(sampler.scale.x)
                        card.scale_y.setValue(sampler.scale.y)
        except Exception as e:
            print(f"[BatchReplaceDialog] 恢复缓存失败: {e}")
    
    def _get_cache_state(self) -> Dict[str, Any]:
        """获取当前状态用于缓存"""
        cache = {
            'target_search_text': self.target_search_widget.search_edit.text(),
            'simplify_texture': self.simplify_texture_check.isChecked(),
            'simplify_material': self.simplify_material_check.isChecked(),
            'migrate_params': self.migrate_params_check.isChecked(),
            'show_more': self.show_more_check.isChecked(),
        }
        
        # 保存目标材质ID
        if self._target_material:
            selected = self.target_search_widget.get_selected_material()
            if selected and 'id' in selected:
                cache['target_material_id'] = selected['id']
        
        # 保存编辑后的采样器数据
        if self._result_cards:
            cache['edited_samplers'] = []
            for card in self._result_cards:
                sampler = card.get_data()
                cache['edited_samplers'].append(sampler.to_dict())
        
        return cache

    def _load_libraries(self):
        """加载库列表到两个搜索组件"""
        if not self._db:
            return
        
        libraries = self._db.get_libraries()
        self.source_search_widget.load_libraries(libraries)
        self.target_search_widget.load_libraries(libraries)
    
    def _auto_search_source(self):
        """自动搜索源材质"""
        if not self._db or not self._source_material:
            return
        
        # 从材质路径中提取文件名作为搜索关键词
        import os
        mtd_path = self._source_material.mtd
        filename = os.path.basename(mtd_path)
        if filename.endswith('.matxml'):
            filename = filename[:-7]
        
        # 设置搜索框文本
        self.source_search_widget.set_search_text(filename)
        self.source_search_widget.set_path(mtd_path)
        
        # 按文件名搜索
        results = self._db.search_materials(keyword=filename)
        
        if results:
            self.source_search_widget.set_status(True)
        else:
            self.source_search_widget.set_status(False)
    
    def _init_source_preview(self):
        """首次进入时初始化左侧（源材质）预览
        
        规则：
        1. 如果用户在纹理编辑界面有任何路径（JSON有路径或手动修改过）→ 直接使用用户的数据
        2. 如果用户材质中所有采样器都没有路径 → 从数据库搜索对应材质并显示
        
        保存初始状态用于"还原材质"功能
        """
        if not self._source_material:
            return
        
        # 检查用户材质是否有任何路径
        user_has_any_path = any(s.path for s in self._source_material.textures)
        
        if user_has_any_path:
            # 用户有路径（来自JSON或纹理编辑界面的修改），直接使用
            # 保存初始状态用于还原
            self._initial_source_material = self._clone_material_entry(self._source_material)
            self._show_left_preview_only()
        else:
            # 用户没有路径，尝试从数据库获取
            if self._db:
                import os
                mtd_path = self._source_material.mtd
                filename = os.path.basename(mtd_path)
                if filename.endswith('.matxml'):
                    filename = filename[:-7]
                
                results = self._db.search_materials(keyword=filename)
                if results:
                    # 使用第一个匹配结果
                    detail = self._db.get_material_detail(results[0]['id'])
                    if detail:
                        db_entry = self._convert_db_to_entry(detail)
                        self._db_source_entry = db_entry
                        # 使用数据库的采样器配置
                        self._source_material = db_entry
                        # 保存初始状态用于还原
                        self._initial_source_material = self._clone_material_entry(db_entry)
                        self._show_left_preview_only()
                        return
            
            # 如果数据库也没有，显示用户的空数据
            self._initial_source_material = self._clone_material_entry(self._source_material)
            self._show_left_preview_only()
    
    def _clone_material_entry(self, entry: MaterialEntry) -> MaterialEntry:
        """深拷贝 MaterialEntry"""
        new_textures = []
        for s in entry.textures:
            new_sampler = SamplerData(
                type_name=s.type_name,
                index=s.index,
                sampler_type=s.sampler_type,
                sorted_pos=s.sorted_pos,
                path=s.path,
                scale=Vec2(s.scale.x, s.scale.y),
                unk10=s.unk10,
                unk11=s.unk11,
                unk14=s.unk14,
                unk18=s.unk18,
                unk1c=s.unk1c,
            )
            new_textures.append(new_sampler)
        
        return MaterialEntry(
            name=entry.name,
            mtd=entry.mtd,
            textures=new_textures,
            gx_index=entry.gx_index,
            index=entry.index,
        )
    
    def _on_source_material_selected(self, data: dict):
        """源材质选择回调（用户在批量替换界面重新搜索选择）
        
        当用户手动选择源材质时：
        完全从数据库获取采样器配置和路径，不保留用户原有数据
        """
        if not self._db:
            return
        
        material_id = data.get('id')
        if not material_id:
            return
        
        detail = self._db.get_material_detail(material_id)
        if not detail:
            return
        
        db_entry = self._convert_db_to_entry(detail)
        
        # 保存数据库材质
        self._db_source_entry = db_entry
        
        # 完全使用数据库的采样器配置和路径
        self._source_material = db_entry
        
        # 只刷新左侧（源材质）预览
        self._show_left_preview_only()
    
    def _on_target_material_selected(self, data: dict):
        """目标材质选择回调 - 更新右侧预览"""
        if not self._db:
            return
        
        material_id = data.get('id')
        if not material_id:
            return
        
        detail = self._db.get_material_detail(material_id)
        if detail:
            self._target_material = self._convert_db_to_entry(detail)
            self._update_state(DialogState.READY)
            # 更新右侧（目标材质）预览
            self._show_right_preview_only()
    
    def _convert_db_to_entry(self, data: Dict[str, Any]) -> MaterialEntry:
        """
        数据库字典转为 MaterialEntry
        
        数据库 samplers 字段：
        - type: 采样器类型名称（如 C_DetailBlend_Rich__snp_Texture2D_7_AlbedoMap）
        - path: 贴图路径
        - key_value: 原始key
        - unk14: {'X': ..., 'Y': ...}
        """
        from src.core.sampler_type_parser import parse_sampler_type
        
        textures = []
        for i, s in enumerate(data.get('samplers', [])):
            type_name = s.get('type', '')
            
            # 解析采样器类型得到 index 和 base_type
            idx, base_type, is_generic = parse_sampler_type(type_name)
            
            # 处理 Scale - 数据库中可能没有完整的 Scale，使用默认值
            # 但如果数据库有 unk14，可以用作参考
            unk14_data = s.get('unk14', {})
            if isinstance(unk14_data, dict):
                unk14_x = unk14_data.get('X', 0)
                unk14_y = unk14_data.get('Y', 0)
            else:
                unk14_x = 0
                unk14_y = 0
            
            sampler = SamplerData(
                type_name=type_name,
                index=idx,
                sampler_type=base_type,
                sorted_pos=i,
                path=s.get('path', ''),
                scale=Vec2(1.0, 1.0),  # 数据库中通常没有完整 Scale，保持默认
                unk10=0,
                unk11=False,
                unk14=unk14_x,  # 使用 unk14.X
                unk18=unk14_y,  # 使用 unk14.Y (根据数据库 schema)
                unk1c=0,
            )
            
            textures.append(sampler)
            
        return MaterialEntry(
            name=data.get('filename', ''),
            mtd=data.get('filename', ''),
            textures=textures,
            gx_index=0,
            index=0
        )

    def _update_state(self, state: DialogState):
        """更新对话框状态"""
        self._state = state
        
        if state == DialogState.READY:
            self.banner.hide()
            self.main_btn.setText(f"🔄 {_('start_replace')}")
            self.main_btn.setEnabled(self._target_material is not None)
            self.cancel_btn.setText(_('cancel'))
            self._enable_config(True)
            
        elif state == DialogState.RUNNING:
            self.banner.show_progress(f"⏳ {_('processing')}...")
            self.main_btn.setText(_('cancel'))
            self.main_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
            self._enable_config(False)
            
        elif state == DialogState.COMPLETED:
            if self._result:
                # 统计结果
                ok_count = sum(1 for r in self._result.results if r.status == MatchStatus.PERFECT_MATCH)
                warn_count = sum(1 for r in self._result.results if r.status == MatchStatus.ADJACENT_MATCH)
                fail_count = sum(1 for r in self._result.results if r.status == MatchStatus.UNMATCHED)
                
                self.banner.show_success(
                    f"✓ {_('completed')}: {ok_count} {_('success')}, {warn_count} {_('warnings')}, {fail_count} {_('failures')}"
                )
            self.main_btn.setText(f"💾 {_('apply_to_texture_edit')}")
            self.main_btn.setEnabled(True)
            self.cancel_btn.setText(_('close'))
            self.cancel_btn.setEnabled(True)
            self._enable_config(False)
            
        elif state == DialogState.CANCELED:
            self.banner.show_warning(f"⛔ {_('canceled')}")
            self.main_btn.setText(f"🔄 {_('start_replace')}")
            self.main_btn.setEnabled(self._target_material is not None)
            self.cancel_btn.setText(_('cancel'))
            self.cancel_btn.setEnabled(True)
            self._enable_config(True)
            self._clear_preview()
            
        elif state == DialogState.FAILED:
            self.banner.show_error(f"✖ {_('failed')}")
            self.main_btn.setText(f"🔄 {_('retry')}")
            self.main_btn.setEnabled(True)
            self.cancel_btn.setText(_('close'))
            self.cancel_btn.setEnabled(True)
            self._enable_config(True)
    
    def _enable_config(self, enabled: bool):
        """启用/禁用配置区"""
        self.source_search_widget.setEnabled(enabled)
        self.target_search_widget.setEnabled(enabled)
        self.simplify_texture_check.setEnabled(enabled)
        self.simplify_material_check.setEnabled(enabled)
        self.migrate_params_check.setEnabled(enabled)
    
    def _auto_preview(self):
        """自动预览 - 此方法已禁用，用户需要手动点击"开始转换"按钮"""
        # 不再自动执行替换预览，保持按钮交互完整
        pass
    
    def _on_main_btn_clicked(self):
        """主按钮点击"""
        if self._state == DialogState.READY:
            self._start_replace()
        elif self._state == DialogState.RUNNING:
            self._cancel_replace()
        elif self._state == DialogState.COMPLETED:
            self._apply_result()
        elif self._state in (DialogState.CANCELED, DialogState.FAILED):
            self._update_state(DialogState.READY)
    
    def _on_cancel_clicked(self):
        """取消按钮点击"""
        if self._state == DialogState.RUNNING:
            self._cancel_replace()
        else:
            self.close()
    
    def _on_banner_action(self):
        """Banner动作按钮点击"""
        pass
    
    def _start_replace(self):
        """开始替换"""
        if not self._source_material or not self._target_material:
            return
        
        # 更新选项
        self._conversion_options.simplify_texture_path = self.simplify_texture_check.isChecked()
        self._conversion_options.simplify_material_path = self.simplify_material_check.isChecked()
        self._conversion_options.migrate_parameters = self.migrate_params_check.isChecked()
        
        # 清除预览
        self._clear_preview()
        
        # 创建工作线程
        self._worker = ReplaceWorker(
            self._source_material,
            self._target_material,
            self._conversion_options,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        
        self._update_state(DialogState.RUNNING)
        self._worker.start()
    
    def _cancel_replace(self):
        """取消替换"""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait()
        
        self._update_state(DialogState.CANCELED)
    
    def _on_progress(self, current: int, total: int, item: str):
        """进度更新"""
        self.banner.show_progress(f"⏳ {_('processing')}... {current}/{total} ({item})")
    
    def _convert_result(self, core_result: CoreReplaceResult) -> UIReplaceResult:
        """核心结果转换为UI模型"""
        ui_results = []
        for r in core_result.results:
            # 安全地映射状态
            try:
                ui_status = MatchStatus[r.status.name]
            except KeyError:
                ui_status = MatchStatus.UNMATCHED
                
            ui_results.append(UIMatchResult(
                source_pos=r.source_pos,
                target_pos=r.target_pos,
                status=ui_status,
                reason=r.reason
            ))
            
        return UIReplaceResult(
            source_material=self._source_material,
            target_material=self._target_material,
            results=ui_results,
            warnings=core_result.warnings,
            order_adjustments_count=core_result.order_adjustments_count,
            global_repair_triggered=core_result.global_repair_triggered
        )

    def _on_finished(self, result):
        """完成"""
        if isinstance(result, Exception):
            self.banner.show_error(f"✖ {_('error')}: {str(result)}")
            self._update_state(DialogState.FAILED)
            return
        
        # 转换为 UI 结果
        self._result = self._convert_result(result)
        self._show_preview()
        self._update_state(DialogState.COMPLETED)
    
    def _show_left_preview_only(self):
        """只更新左侧（源材质/当前材质）预览"""
        if not self._source_material:
            return
        
        # 只清除左侧
        while self.left_preview_layout.count():
            item = self.left_preview_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        show_more = self.show_more_check.isChecked()
        
        for sampler in self._source_material.textures:
            left_card = EditableSamplerCard(
                sampler=sampler,
                match_status=None,  # 无状态
                editable=False
            )
            left_card.set_show_more(show_more)
            self.left_preview_layout.addWidget(left_card)
        
        self.left_preview_layout.addStretch()
    
    def _show_right_preview_only(self):
        """只更新右侧（目标材质/待替换材质）预览"""
        if not self._target_material:
            return
        
        # 只清除右侧
        while self.right_preview_layout.count():
            item = self.right_preview_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        show_more = self.show_more_check.isChecked()
        
        for sampler in self._target_material.textures:
            right_card = EditableSamplerCard(
                sampler=sampler,
                match_status=None,  # 无状态，等执行替换后再显示状态
                editable=False
            )
            right_card.set_show_more(show_more)
            self.right_preview_layout.addWidget(right_card)
        
        self.right_preview_layout.addStretch()
    
    def _show_source_preview(self):
        """显示源材质预览（兼容旧调用，实际调用 _show_left_preview_only）"""
        self._show_left_preview_only()
    
    def _clear_preview(self):
        """清除预览（双栏）"""
        # 清除左侧
        while self.left_preview_layout.count():
            item = self.left_preview_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        # 清除右侧
        while self.right_preview_layout.count():
            item = self.right_preview_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        # 清除卡片列表
        self._result_cards = []
    
    def _show_preview(self):
        """显示替换结果预览（双栏）
        
        核心替换逻辑：
        - 左侧：源材质的采样器（提供贴图路径）
        - 右侧：目标材质的采样器（提供采样器类型/名称）
        
        替换结果：
        - 采样器类型/名称：来自目标材质
        - 贴图路径：来自源材质（按匹配关系映射）
        """
        if not self._result:
            return
        
        self._clear_preview()
        self._result_cards = []
        
        show_more = self.show_more_check.isChecked()
        
        # 构建匹配映射：target_pos -> source_pos
        match_map = {}
        for result in self._result.results:
            if result.target_pos is not None:
                match_map[result.target_pos] = result
        
        # 左侧：显示源材质的所有采样器
        for i, source_sampler in enumerate(self._source_material.textures):
            # 找到这个源采样器对应的匹配结果
            match_result = None
            for result in self._result.results:
                if result.source_pos == i:
                    match_result = result
                    break
            
            status = match_result.status if match_result else None
            
            left_card = EditableSamplerCard(
                sampler=source_sampler,
                match_status=status,
                editable=False
            )
            left_card.set_show_more(show_more)
            self.left_preview_layout.addWidget(left_card)
        
        # 右侧：显示目标材质的所有采样器，并填入匹配到的源路径
        for j, target_sampler in enumerate(self._target_material.textures):
            # 检查这个目标采样器是否有匹配的源
            if j in match_map:
                result = match_map[j]
                source_sampler = self._source_material.textures[result.source_pos]
                
                # 创建替换后的采样器：
                # - 类型/名称：来自目标材质
                # - 路径：来自源材质
                # - 其他参数：来自源材质（参数迁移）
                replaced_sampler = SamplerData(
                    type_name=target_sampler.type_name,  # 目标的采样器类型
                    index=target_sampler.index,
                    sampler_type=target_sampler.sampler_type,
                    sorted_pos=j,
                    path=source_sampler.path,  # 源的贴图路径
                    scale=source_sampler.scale,  # 源的缩放参数
                    unk10=source_sampler.unk10,
                    unk11=source_sampler.unk11,
                    unk14=source_sampler.unk14,
                    unk18=source_sampler.unk18,
                    unk1c=source_sampler.unk1c,
                )
                
                # 确定状态
                final_status = result.status
                if not source_sampler.path or not source_sampler.path.strip():
                    final_status = MatchStatus.EMPTY
                
                right_card = EditableSamplerCard(
                    sampler=replaced_sampler,
                    match_status=final_status,
                    editable=True
                )
            else:
                # 这个目标采样器没有匹配到源
                # 如果原本有路径，标记为 UNCOVERED；否则标记为 EMPTY
                # 同时清除数据库中的原始路径，只保留类型信息
                cleared_sampler = SamplerData(
                    type_name=target_sampler.type_name,
                    index=target_sampler.index,
                    sampler_type=target_sampler.sampler_type,
                    sorted_pos=j,
                    path='',  # 清除数据库路径
                    scale=target_sampler.scale,
                    unk10=target_sampler.unk10,
                    unk11=target_sampler.unk11,
                    unk14=target_sampler.unk14,
                    unk18=target_sampler.unk18,
                    unk1c=target_sampler.unk1c,
                )
                uncovered_status = MatchStatus.UNCOVERED if target_sampler.has_path else MatchStatus.EMPTY
                right_card = EditableSamplerCard(
                    sampler=cleared_sampler,
                    match_status=uncovered_status,
                    editable=True
                )
            
            right_card.set_show_more(show_more)
            right_card.dataChanged.connect(self._on_preview_data_changed)
            self.right_preview_layout.addWidget(right_card)
            self._result_cards.append(right_card)
        
        self.left_preview_layout.addStretch()
        self.right_preview_layout.addStretch()
        
        # 启用还原按钮
        self.restore_btn.setEnabled(True)
    
    def _on_show_more_changed(self, state: int):
        """显示更多参数切换"""
        show = state == Qt.CheckState.Checked.value
        # 更新所有卡片
        for i in range(self.left_preview_layout.count() - 1):  # -1 排除stretch
            widget = self.left_preview_layout.itemAt(i).widget()
            if isinstance(widget, EditableSamplerCard):
                widget.set_show_more(show)
        for card in self._result_cards:
            card.set_show_more(show)
    
    def _on_restore_source(self):
        """还原源材质 - 恢复到首次进入时的状态"""
        if not self._initial_source_material:
            return
        
        # 恢复源材质为初始状态
        self._source_material = self._clone_material_entry(self._initial_source_material)
        
        # 刷新左侧预览
        self._show_left_preview_only()
    
    def _on_preview_data_changed(self):
        """预览数据变更"""
        # 标记为已修改
        pass
    
    def _apply_result(self):
        """应用结果（从可编辑卡片获取数据）"""
        if not self._result_cards:
            return
        
        # 从可编辑卡片获取数据
        new_samplers = []
        for card in self._result_cards:
            new_samplers.append(card.get_data())
        
        # 获取目标材质路径
        new_mtd = self._target_material.mtd if self._target_material else ''
        
        # 发送结果 - 包含材质路径和采样器
        self.resultApplied.emit({
            'mtd': new_mtd,
            'samplers': new_samplers
        })
        self.close()
    
    def closeEvent(self, event):
        """关闭事件"""
        if self._state == DialogState.RUNNING:
            from src.gui_qt.standard_dialogs import show_confirm_dialog
            confirmed = show_confirm_dialog(
                self,
                _('confirm'),
                _('cancel_running_confirm'),
                confirm_style='danger'
            )
            if confirmed:
                self._cancel_replace()
            else:
                event.ignore()
                return
        
        # 发送缓存更新信号
        try:
            cache = self._get_cache_state()
            self.cacheUpdated.emit(cache)
        except Exception as e:
            print(f"[BatchReplaceDialog] 获取缓存状态失败: {e}")
        
        event.accept()
    
    def _on_show_log_clicked(self):
        """显示匹配日志弹窗"""
        # 获取最近一次替换的日志（从worker的replacer获取）
        log_lines = []
        if hasattr(self, '_worker') and self._worker and hasattr(self._worker, 'replacer'):
            log_lines = self._worker.replacer.get_log()
        
        if not log_lines:
            log_lines = ["(暂无日志 - 请先执行一次替换预览)"]
        
        # 创建日志对话框
        log_dialog = QDialog(self)
        log_dialog.setWindowTitle(_('matching_log'))
        log_dialog.setMinimumSize(600, 400)
        log_dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {C['bg_primary']};
            }}
            QTextEdit {{
                background-color: {C['bg_secondary']};
                color: {C['fg_primary']};
                border: 1px solid {C['border_subtle']};
                border-radius: 6px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                padding: 8px;
            }}
            QPushButton {{
                background-color: {C['accent']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                background-color: #4a9aff;
            }}
        """)
        
        layout = QVBoxLayout(log_dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # 日志文本框
        from PySide6.QtWidgets import QTextEdit
        log_text = QTextEdit()
        log_text.setReadOnly(True)
        log_text.setPlainText("\n".join(log_lines))
        layout.addWidget(log_text, 1)
        
        # 关闭按钮
        close_btn = QPushButton(_('close'))
        close_btn.clicked.connect(log_dialog.close)
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_layout.addWidget(close_btn)
        layout.addLayout(close_layout)
        
        log_dialog.exec()
