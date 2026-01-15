"""
材质替换编辑器主窗口

按设计文档V3第六章 6.1 实现：
- 工具栏（导入/导出/撤销/重做）
- 材质列表（Name/MTD/GXIndex/Index）
- 状态栏
- 窗口状态保持（13.1）
- 非模态窗口（7.5）
"""

import json
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QFileDialog,
    QStatusBar, QToolBar, QSplitter, QFrame, QAbstractItemView, QApplication,
    QMenu, QGridLayout
)
from PySide6.QtCore import Qt, Signal, QSettings, QSize, QEvent
from PySide6.QtGui import QAction, QKeySequence, QIcon, QCloseEvent

from src.core.i18n import _
from src.core.material_replace_models import (
    MaterialEntry, SamplerData, EditorState, ConversionOptions
)
from src.core.material_json_parser import MaterialJsonParser
from src.core.undo_redo_manager import UndoRedoManager, UndoAction, create_undo_action
import os
from src.utils.resource_path import get_assets_path

logger = logging.getLogger(__name__)


class MaterialReplaceEditor(QMainWindow):
    """
    材质替换编辑器主窗口
    
    核心工作流：导入JSON → 材质列表 → 纹理编辑面板 → 批量替换 → 导出JSON
    """
    
    # 信号
    materialSelected = Signal(int)  # 材质选中，参数为索引
    
    # 缓存键
    CACHE_KEY = "material_replace_editor_state"
    
    def __init__(self, parent=None, database_manager=None):
        super().__init__(parent)
        
        self.db = database_manager
        
        # 数据模型
        self._materials: List[MaterialEntry] = []
        self._file_path: Optional[str] = None
        self._undo_manager = UndoRedoManager()
        self._conversion_options = ConversionOptions()
        
        # 搜索过滤索引（None表示显示全部）
        self._filtered_indices: Optional[List[int]] = None
        
        # 纹理编辑面板缓存（按材质索引）
        self._texture_panel_cache: Dict[int, Dict[str, Any]] = {}
        
        # 已打开的子窗口
        self._texture_panels: Dict[int, QWidget] = {}
        
        self._setup_ui()
        self._setup_actions()
        self._setup_toolbar()
        self._setup_statusbar()
        self._connect_signals()
        
        # 恢复窗口状态
        self._restore_window_state()
        self._restore_editor_state()
        
        # 更新UI状态
        self._update_ui_state()
    
    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle(_('material_replace_editor_title'))

        # 应用深色标题栏
        from src.gui_qt.dark_titlebar import apply_dark_titlebar_to_window
        apply_dark_titlebar_to_window(self)
        
        # 设置窗口图标
        try:
            icon_path = get_assets_path("app_icon.png")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass
        
        self.setMinimumSize(900, 600)
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 搜索框（按设计文档6.1.2）
        self._setup_search_bar()
        layout.addWidget(self._search_frame)
        
        # 材质列表
        self._setup_material_list()
        layout.addWidget(self.material_table)
    
    def _setup_search_bar(self):
        """设置搜索框（按设计文档6.1.2）"""
        from PySide6.QtWidgets import QLineEdit
        from PySide6.QtCore import QTimer
        
        self._search_frame = QFrame()
        search_layout = QHBoxLayout(self._search_frame)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(8)
        
        # 搜索输入框
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText(_('search_material_placeholder'))
        self._search_edit.setClearButtonEnabled(True)
        search_layout.addWidget(self._search_edit, 1)
        
        # 搜索防抖定时器（100ms）
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(100)
        self._search_timer.timeout.connect(self._do_search)
        
        # 连接信号
        self._search_edit.textChanged.connect(self._on_search_text_changed)
        self._search_edit.returnPressed.connect(self._do_search)  # Enter立即触发
    
    def _setup_material_list(self):
        """设置材质列表 - 参照 SamplerPanel 样式"""
        # 列宽记忆设置
        self._table_settings = QSettings("FSmatbinBD", "MaterialReplaceEditor")
        self._restoring_columns = False
        
        self.material_table = QTableWidget()
        self.material_table.setColumnCount(6)
        self.material_table.setHorizontalHeaderLabels([
            '#', 
            _('material_name'), 
            _('material_path'), 
            'GXIndex', 
            'Index',
            _('action')
        ])
        
        # === 样式：行间隔 + hover + selected ===
        self.material_table.setAlternatingRowColors(True)
        self.material_table.setStyleSheet("""
            QTableWidget {
                background: rgba(10, 14, 24, 160);
                alternate-background-color: rgba(255, 255, 255, 5);
                gridline-color: rgba(255, 255, 255, 8);
                border: 1px solid rgba(110, 165, 255, 90);
                border-radius: 10px;
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
                color: rgba(245, 248, 255, 235);
                padding: 5px 8px;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 8);
                font-size: 9pt;
                font-weight: 750;
            }
        """)
        
        # === 长文本完整显示：启用自动换行 ===
        self.material_table.setWordWrap(True)
        
        # === 隐藏垂直表头（避免重复序号）===
        self.material_table.verticalHeader().setVisible(False)
        
        # === 列宽配置 ===
        header = self.material_table.horizontalHeader()
        # 允许用户调整列宽
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        # 监听列宽调整
        header.sectionResized.connect(self._on_column_resized)
        
        # 设置默认列宽
        self._apply_column_widths()
        
        # 选择模式
        self.material_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.material_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        
        # 启用编辑（Name/MTD/GXIndex/Index列可编辑）
        self.material_table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        
        # 连接编辑完成信号
        self.material_table.cellChanged.connect(self._on_cell_changed)
        
        # 双击和选择
        self.material_table.selectionModel().selectionChanged.connect(self._on_selection_changed)
    
    def _apply_column_widths(self):
        """应用列宽配置：优先恢复保存的值，用户可调整"""
        header = self.material_table.horizontalHeader()
        
        # 设置行高（增大以便编辑时可见）
        self.material_table.verticalHeader().setDefaultSectionSize(40)
        
        # 所有列使用 Interactive 模式，允许用户调整
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        # 不拉伸最后一列（避免按钮布局异常）
        header.setStretchLastSection(False)
        
        # 默认宽度
        default_widths = [45, 150, 400, 70, 60, 80]
        
        # 尝试恢复保存的宽度
        saved = self._table_settings.value("column_widths")
        if saved:
            try:
                if isinstance(saved, str):
                    widths = [int(p) for p in saved.split(',') if p.strip()]
                else:
                    widths = [int(x) for x in list(saved)]
                
                if len(widths) >= 6:
                    self._restoring_columns = True
                    for col, w in enumerate(widths[:6]):
                        if w > 10:
                            header.resizeSection(col, w)
                    self._restoring_columns = False
                    return
            except Exception:
                pass
        
        # 使用默认宽度
        for col, width in enumerate(default_widths):
            header.resizeSection(col, width)
        
        # MTD 列拉伸填充剩余空间
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    
    def _on_column_resized(self, logicalIndex: int, oldSize: int, newSize: int):
        """列宽调整时保存"""
        if self._restoring_columns:
            return
        self._save_column_widths()
    
    def _save_column_widths(self):
        """保存列宽配置"""
        header = self.material_table.horizontalHeader()
        widths = [header.sectionSize(col) for col in range(6)]
        self._table_settings.setValue("column_widths", ",".join(str(w) for w in widths))
    
    def _setup_actions(self):
        """设置动作"""
        # 导入
        self.action_import = QAction(_('import_json'), self)
        self.action_import.setShortcut(QKeySequence.StandardKey.Open)
        self.action_import.triggered.connect(self._on_import)
        
        # 导出
        self.action_export = QAction(_('export_json'), self)
        self.action_export.setShortcut(QKeySequence.StandardKey.Save)
        self.action_export.triggered.connect(self._on_export)
        
        # 撤销
        self.action_undo = QAction(_('undo'), self)
        self.action_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.action_undo.triggered.connect(self._on_undo)
        
        # 重做
        self.action_redo = QAction(_('redo'), self)
        self.action_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.action_redo.triggered.connect(self._on_redo)
        
        # 打开纹理编辑
        self.action_edit_texture = QAction(_('edit_texture'), self)
        self.action_edit_texture.setShortcut(Qt.Key.Key_Return)
        self.action_edit_texture.triggered.connect(self._on_edit_texture)
    
    # ==================== 帮助类 ====================
    
    class GlowButtonWrapper(QWidget):
        """带有独立发光层的按钮包装器（解决文字模糊问题）"""
        
        def __init__(self, text, object_name, callback, parent=None):
            super().__init__(parent)
            self.setObjectName(f"{object_name}_wrapper")
            
            # 使用层叠布局
            layout = QGridLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            
            # 1. 底部发光层（用于应用 DropShadow）
            self.glow_bg = QWidget()
            self.glow_bg.setObjectName(object_name)  # 复用按钮样式以获得相同的圆角和背景
            self.glow_bg.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)  # 不接收鼠标事件
            layout.addWidget(self.glow_bg, 0, 0)
            
            # 2. 顶部按钮层（不应用发光，保持文字清晰）
            self.btn = QPushButton(text)
            self.btn.setObjectName(object_name)
            self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn.clicked.connect(callback)
            layout.addWidget(self.btn, 0, 0)
            
            # 初始化发光效果（应用于底部层）
            from src.gui_qt.theme.qss import apply_glow_effect
            # 橙色发光 (255, 165, 0)
            apply_glow_effect(self.glow_bg, color=(255, 165, 0), blur_radius=15)
            
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

    def _create_glow_button(self, text, object_name, callback):
        return self.GlowButtonWrapper(text, object_name, callback)

    def _setup_toolbar(self):
        """设置工具栏"""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setObjectName("MaterialReplaceToolbar")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # 导入 - 蓝色玻璃按钮（与主界面"材质匹配"一致）
        import_btn = QPushButton(f"📂 {_('import_json')}")
        import_btn.setObjectName("blue-glass")
        import_btn.clicked.connect(self._on_import)
        toolbar.addWidget(import_btn)
        self.import_btn = import_btn
        
        # 导出 - 黄色警告按钮（与主界面"自动封包"一致）
        export_btn = QPushButton(f"💾 {_('export_json')}")
        export_btn.setObjectName("warning")
        export_btn.clicked.connect(self._on_export)
        toolbar.addWidget(export_btn)
        self.export_btn = export_btn
        
        toolbar.addSeparator()
        
        # 撤销 - 灰色玻璃按钮（与主界面"高级搜索"一致）
        undo_btn = QPushButton(f"↶ {_('undo')}")
        undo_btn.setObjectName("glass")
        undo_btn.clicked.connect(self._on_undo)
        toolbar.addWidget(undo_btn)
        self.undo_btn = undo_btn
        
        # 重做 - 灰色玻璃按钮
        redo_btn = QPushButton(f"↷ {_('redo')}")
        redo_btn.setObjectName("glass")
        redo_btn.clicked.connect(self._on_redo)
        toolbar.addWidget(redo_btn)
        self.redo_btn = redo_btn
        
        toolbar.addSeparator()
        
        # 编辑纹理 - 橙色实心按钮 (使用 GlowButtonWrapper 解决发光模糊文字问题)
        edit_btn_wrapper = self._create_glow_button(f"✏️ {_('edit_texture')}", "solid-orange", self._on_edit_texture)
        toolbar.addWidget(edit_btn_wrapper)
        self.edit_btn = edit_btn_wrapper.btn  # 保存对内部按钮的引用以便启用/禁用
        
        # 应用悬停发光效果（仅对非实心按钮，实心按钮已由 Wrapper 处理）
        from src.gui_qt.theme.qss import apply_glow_effect
        apply_glow_effect(import_btn, color=(47, 129, 247), blur_radius=12)   # 蓝色发光
        apply_glow_effect(export_btn, color=(210, 153, 34), blur_radius=12)   # 黄色发光
    
    def _setup_statusbar(self):
        """设置状态栏"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        # 材质计数
        self.material_count_label = QLabel()
        self.statusbar.addWidget(self.material_count_label)
        
        # 修改计数
        self.modified_count_label = QLabel()
        self.statusbar.addWidget(self.modified_count_label)
        
        # 撤销计数
        self.undo_count_label = QLabel()
        self.statusbar.addPermanentWidget(self.undo_count_label)
    
    def _connect_signals(self):
        """连接信号"""
        self._undo_manager.add_listener(self._update_undo_redo_state)
    
    # ==================== 搜索功能 ====================
    
    def _on_search_text_changed(self, text: str):
        """搜索文本变化（启动防抖定时器）"""
        self._search_timer.stop()
        self._search_timer.start()
    
    def _do_search(self):
        """
        执行搜索（按设计文档6.1.2）
        支持：文件名 / MTD路径 / 采样器类型 / 采样器路径的模糊搜索
        """
        self._search_timer.stop()
        keyword = self._search_edit.text().strip().lower()
        
        if not keyword:
            # 空搜索显示所有
            self._filtered_indices = None
            self._refresh_table()
            return
        
        # 搜索材质列表
        matched_indices = []
        for idx, material in enumerate(self._materials):
            if self._match_material(material, keyword):
                matched_indices.append(idx)
        
        # 保存过滤结果并刷新
        self._filtered_indices = matched_indices if keyword else None
        self._refresh_table_filtered()
        
        # 状态栏提示
        if keyword:
            self.statusbar.showMessage(
                _('search_result_count').format(count=len(matched_indices), total=len(self._materials)),
                3000
            )
    
    def _match_material(self, material: MaterialEntry, keyword: str) -> bool:
        """检查材质是否匹配搜索关键词"""
        # 匹配材质名
        if keyword in material.name.lower():
            return True
        
        # 匹配MTD路径
        if keyword in material.mtd.lower():
            return True
        
        # 匹配采样器类型和路径
        for sampler in material.textures:
            if keyword in sampler.type.lower():
                return True
            if keyword in sampler.path.lower():
                return True
        
        return False
    
    def _refresh_table_filtered(self):
        """刷新过滤后的材质列表"""
        if self._filtered_indices is None:
            self._refresh_table()
            return
        
        indices = self._filtered_indices
        self.material_table.setRowCount(len(indices))
        
        for row, mat_idx in enumerate(indices):
            material = self._materials[mat_idx]
            
            # 序号（显示原始序号）
            item = QTableWidgetItem(str(mat_idx + 1))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setData(Qt.ItemDataRole.UserRole, mat_idx)  # 存储原始索引
            self.material_table.setItem(row, 0, item)
            
            # 名称
            name = material.name
            if material.is_modified:
                name = f"* {name}"
            self.material_table.setItem(row, 1, QTableWidgetItem(name))
            
            # MTD路径
            mtd_display = self._simplify_path(material.mtd)
            self.material_table.setItem(row, 2, QTableWidgetItem(mtd_display))
            
            # GXIndex
            item = QTableWidgetItem(str(material.gx_index))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.material_table.setItem(row, 3, item)
            
            # Index
            item = QTableWidgetItem(str(material.index))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # 操作列（编辑按钮）- 使用橙色实心按钮样式 (使用 GlowButtonWrapper)
            # 使用闭包捕获当前材质的索引
            callback = lambda checked=False, idx=mat_idx: self._on_edit_material_at(idx)
            edit_btn_wrapper = self._create_glow_button(f"✏️ {_('edit')}", "solid-orange", callback)
            
            # 将按钮放入一个 Widget 中以方便布局
            # GlowButtonWrapper 本身就是 Widget，但为了对齐可能还需要一层 Layout，
            # 不过 GlowButtonWrapper 内部已经是 GridLayout，或许可以直接用？
            # 为了保险起见保持原有结构
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            btn_layout.addWidget(edit_btn_wrapper)
            self.material_table.setCellWidget(row, 5, btn_widget)
        
        self._update_status_bar()
    
    # ==================== 数据操作 ====================
    
    def _refresh_table(self):
        """刷新材质列表"""
        self.material_table.setRowCount(len(self._materials))
        
        for row, material in enumerate(self._materials):
            # 序号（不可编辑）
            item = QTableWidgetItem(str(row + 1))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.material_table.setItem(row, 0, item)
            
            # 名称（如果已修改，添加标记）
            name = material.name
            if material.is_modified:
                name = f"* {name}"
            self.material_table.setItem(row, 1, QTableWidgetItem(name))
            
            # MTD路径（显示完整路径）
            mtd_item = QTableWidgetItem(material.mtd)
            mtd_item.setToolTip(material.mtd)
            self.material_table.setItem(row, 2, mtd_item)
            
            # GXIndex
            item = QTableWidgetItem(str(material.gx_index))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.material_table.setItem(row, 3, item)
            
            # Index
            item = QTableWidgetItem(str(material.index))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.material_table.setItem(row, 4, item)
            
            # 操作列（编辑按钮）- 使用橙色实心按钮样式 (使用 GlowButtonWrapper)
            # 使用闭包捕获当前材质的索引
            callback = lambda checked=False, idx=row: self._on_edit_material_at(idx)
            edit_btn_wrapper = self._create_glow_button(f"✏️ {_('edit')}", "solid-orange", callback)
            
            # 将按钮放入一个 Widget 中以方便布局
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            btn_layout.addWidget(edit_btn_wrapper)
            self.material_table.setCellWidget(row, 5, btn_widget)
        
        self._update_status_bar()
    
    def _simplify_path(self, path: str) -> str:
        """简化路径显示"""
        if not path:
            return ""
        # 只显示文件名
        return Path(path).name
    
    def _update_ui_state(self):
        """更新UI状态"""
        has_materials = len(self._materials) > 0
        has_selection = self.material_table.currentRow() >= 0
        
        self.export_btn.setEnabled(has_materials)
        self.edit_btn.setEnabled(has_selection)
        
        self._update_undo_redo_state()
        self._update_status_bar()
    
    def _on_cell_changed(self, row: int, column: int):
        """表格单元格编辑完成回调"""
        if row < 0 or row >= len(self._materials):
            return
        
        # 列0(序号)和列5(操作)不处理
        if column in (0, 5):
            return
        
        item = self.material_table.item(row, column)
        if not item:
            return
        
        new_value = item.text()
        material = self._materials[row]
        old_material = material.copy()
        
        # 根据列更新对应字段
        if column == 1:  # Name
            # 去掉修改标记
            if new_value.startswith("* "):
                new_value = new_value[2:]
            material.name = new_value
        elif column == 2:  # MTD路径
            old_mtd = material.mtd
            material.mtd = new_value
            
            # 如果MTD路径有变化，询问是否从数据库加载采样器配置
            if old_mtd != new_value and self.db:
                self._offer_load_samplers_from_mtd(row, new_value)
        elif column == 3:  # GXIndex
            try:
                material.gx_index = int(new_value)
            except ValueError:
                item.setText(str(material.gx_index))
                return
        elif column == 4:  # Index
            try:
                material.index = int(new_value)
            except ValueError:
                item.setText(str(material.index))
                return
        
        # 标记为已修改
        material.is_modified = True
        
        # 更新UI状态
        self._update_ui_state()
    
    def _offer_load_samplers_from_mtd(self, row: int, mtd_path: str):
        """询问是否从数据库加载采样器配置"""
        if not self.db or not mtd_path:
            return
        
        # 从数据库查询匹配的材质（使用材质路径搜索）
        try:
            # 提取文件名作为搜索关键词
            from pathlib import Path
            mtd_filename = Path(mtd_path).stem
            results = self.db.search_materials(keyword=mtd_filename)
            
            if not results:
                return
            
            # 获取第一个匹配项名称
            first_name = results[0].get('name', mtd_filename) if results else mtd_filename
            
            # 询问用户是否加载
            from src.gui_qt.standard_dialogs import show_confirm_dialog
            confirmed = show_confirm_dialog(
                self,
                _('load_sampler_config'),
                _('load_sampler_config_confirm').format(count=len(results), name=first_name),
            )
            
            if confirmed:
                # 加载第一个匹配结果的采样器
                target_material = results[0]
                self._load_samplers_from_database_material(row, target_material)
        except Exception as e:
            logger.warning(f"Failed to query MTD: {e}")
    
    def _load_samplers_from_database_material(self, row: int, db_material: dict):
        """从数据库材质加载采样器配置到当前材质"""
        if row < 0 or row >= len(self._materials):
            return
        
        material = self._materials[row]
        
        # 从数据库材质获取采样器
        samplers_data = db_material.get('samplers', [])
        if not samplers_data:
            logger.info(f"No samplers found in database material")
            return
        
        # 转换为 SamplerData 列表
        from src.core.material_replace_models import SamplerData, Vec2
        new_samplers = []
        for idx, s in enumerate(samplers_data):
            sampler = SamplerData(
                type_name=s.get('type', ''),
                index=idx,
                sampler_type=s.get('sampler_type', ''),
                sorted_pos=idx,
                path=s.get('path', ''),
                scale=Vec2(1.0, 1.0),
            )
            new_samplers.append(sampler)
        
        # 更新材质的采样器
        material.textures = new_samplers
        material.is_modified = True
        
        logger.info(f"Loaded {len(new_samplers)} samplers from database")
        self._update_status_bar()
        
        # 如果该材质的纹理编辑面板已打开，刷新面板显示
        if row in self._texture_panels:
            panel = self._texture_panels[row]
            panel._load_material()  # 重新加载材质数据到面板
    
    def _update_undo_redo_state(self):
        """更新撤销/重做按钮状态"""
        can_undo = self._undo_manager.can_undo()
        can_redo = self._undo_manager.can_redo()
        
        self.undo_btn.setEnabled(can_undo)
        self.redo_btn.setEnabled(can_redo)
        
        # 更新提示
        undo_desc = self._undo_manager.get_undo_description()
        redo_desc = self._undo_manager.get_redo_description()
        
        self.undo_btn.setToolTip(f"{_('undo')}: {undo_desc}" if undo_desc else _('undo'))
        self.redo_btn.setToolTip(f"{_('redo')}: {redo_desc}" if redo_desc else _('redo'))
        
        # 状态栏
        self.undo_count_label.setText(
            f"{_('undo_steps')}: {self._undo_manager.undo_count()}"
        )
    
    def _update_status_bar(self):
        """更新状态栏"""
        total = len(self._materials)
        modified = sum(1 for m in self._materials if m.is_modified)
        
        self.material_count_label.setText(f"{_('loaded_materials')}: {total}")
        self.modified_count_label.setText(f"{_('modified')}: {modified}")
    
    # ==================== 导入/导出 ====================
    
    def _on_import(self):
        """导入JSON"""
        # 检查未保存更改
        if self._has_unsaved_changes():
            from src.gui_qt.standard_dialogs import show_unsaved_changes_dialog
            result = show_unsaved_changes_dialog(self)
            
            if result == QMessageBox.StandardButton.Save:
                if not self._on_export():
                    return
            elif result == QMessageBox.StandardButton.Cancel:
                return
        
        # 选择文件
        file_path, _filter = QFileDialog.getOpenFileName(
            self,
            _('select_json_file'),
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
        
        self._load_file(file_path)
    
    def _load_file(self, file_path: str):
        """加载JSON文件"""
        materials, error = MaterialJsonParser.parse_file(file_path)
        
        if error:
            QMessageBox.critical(
                self,
                _('import_error'),
                f"{_('import_failed')}: {error}"
            )
            logger.error(f"Import failed: {error}")
            return
        
        # 更新数据
        self._materials = materials
        self._file_path = file_path
        
        # 清空撤销栈和缓存（按设计文档 10.2）
        self._undo_manager.clear()
        self._texture_panel_cache.clear()
        
        # 关闭所有打开的纹理编辑面板
        for panel in list(self._texture_panels.values()):
            panel.close()
        self._texture_panels.clear()
        
        # 刷新UI
        self._refresh_table()
        self._update_ui_state()
        
        self.setWindowTitle(f"{_('material_replace_editor_title')} - {Path(file_path).name}")
        self.statusbar.showMessage(f"{_('import_success')}: {len(materials)} {_('materials')}", 3000)
    
    def _on_export(self) -> bool:
        """
        导出JSON
        
        Returns:
            是否成功
        """
        if not self._materials:
            QMessageBox.warning(self, _('warning'), _('no_materials_to_export'))
            return False
        
        # 选择保存路径
        default_path = self._file_path or ""
        file_path, _filter = QFileDialog.getSaveFileName(
            self,
            _('save_json_file'),
            default_path,
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return False
        
        # 确保有.json后缀
        if not file_path.lower().endswith('.json'):
            file_path += '.json'
        
        # 导出
        error = MaterialJsonParser.export_to_file(self._materials, file_path)
        
        if error:
            QMessageBox.critical(
                self,
                _('export_error'),
                f"{_('export_failed')}: {error}"
            )
            logger.error(f"Export failed: {error}")
            return False
        
        # 更新状态
        self._file_path = file_path
        
        # 清除修改标记
        for material in self._materials:
            material.is_modified = False
        
        # 清空撤销栈和缓存（按设计文档 10.3）
        self._undo_manager.clear()
        self._texture_panel_cache.clear()
        self._clear_editor_state_cache()
        
        # 刷新UI
        self._refresh_table()
        self._update_ui_state()
        
        self.setWindowTitle(f"{_('material_replace_editor_title')} - {Path(file_path).name}")
        self.statusbar.showMessage(_('export_success'), 3000)
        
        return True
    
    # ==================== 撤销/重做 ====================
    
    def _on_undo(self):
        """撤销"""
        action = self._undo_manager.undo()
        if action:
            # 恢复状态
            if 0 <= action.material_index < len(self._materials):
                self._materials[action.material_index] = action.before_state.copy()
                self._refresh_table()
            self.statusbar.showMessage(f"{_('undo')}: {action.description}", 2000)
    
    def _on_redo(self):
        """重做"""
        action = self._undo_manager.redo()
        if action:
            # 应用状态
            if 0 <= action.material_index < len(self._materials):
                self._materials[action.material_index] = action.after_state.copy()
                self._refresh_table()
            self.statusbar.showMessage(f"{_('redo')}: {action.description}", 2000)
    
    # ==================== 纹理编辑 ====================
    
    def _on_material_double_clicked(self, index):
        """材质双击"""
        self._on_edit_texture()
    
    def _on_selection_changed(self):
        """选择变化"""
        self._update_ui_state()
        row = self.material_table.currentRow()
        if row >= 0:
            self.materialSelected.emit(row)
    
    def _open_texture_panel(self, index: int):
        """所选索引打开纹理编辑面板"""
        if index < 0 or index >= len(self._materials):
            return
        
        # 检查是否已打开
        if index in self._texture_panels:
            panel = self._texture_panels[index]
            panel.raise_()
            panel.activateWindow()
            return
        
        # 创建纹理编辑面板
        from .texture_edit_panel import TextureEditPanel
        
        material = self._materials[index]
        panel = TextureEditPanel(
            parent=None,  # 非模态，独立窗口
            material=material,
            material_index=index,
            database_manager=self.db,
            cached_state=self._texture_panel_cache.get(index),
        )
        
        # 连接信号
        panel.saveRequested.connect(lambda data, idx=index: self._on_texture_panel_save(idx, data))
        panel.cacheUpdated.connect(lambda data, idx=index: self._on_texture_panel_cache(idx, data))
        panel.closed.connect(lambda idx=index: self._on_texture_panel_closed(idx))
        
        self._texture_panels[index] = panel
        panel.show()

    def _on_edit_texture(self):
        """打开纹理编辑面板"""
        row = self.material_table.currentRow()
        self._open_texture_panel(row)
    
    def _on_texture_panel_save(self, material_index: int, new_material: MaterialEntry):
        """
        纹理编辑面板保存
        
        按设计文档 10.2：点击"保存到纹理编辑"才入主撤销栈（一次保存算一步）
        """
        if material_index < 0 or material_index >= len(self._materials):
            return
        
        old_material = self._materials[material_index]
        
        # 创建撤销动作
        action = create_undo_action(
            action_type='save_to_texture_edit',
            description=f"{_('save_texture_edit')}: {old_material.name}",
            material_index=material_index,
            before_state=old_material,
            after_state=new_material,
        )
        self._undo_manager.push(action)
        
        # 更新数据
        new_material.is_modified = True
        self._materials[material_index] = new_material
        
        # 清除该材质的面板缓存
        if material_index in self._texture_panel_cache:
            del self._texture_panel_cache[material_index]
        
        # 刷新UI
        self._refresh_table()
        self.statusbar.showMessage(f"{_('saved')}: {new_material.name}", 2000)
    
    def _on_texture_panel_cache(self, material_index: int, cache_data: Dict[str, Any]):
        """纹理编辑面板缓存更新"""
        self._texture_panel_cache[material_index] = cache_data
    
    def _on_texture_panel_closed(self, material_index: int):
        """纹理编辑面板关闭"""
        if material_index in self._texture_panels:
            del self._texture_panels[material_index]
    
    # ==================== 状态保持 ====================
    
    def _has_unsaved_changes(self) -> bool:
        """是否有未保存的更改"""
        return any(m.is_modified for m in self._materials)
    
    def _save_window_state(self):
        """保存窗口状态"""
        settings = QSettings()
        settings.setValue("material_replace_editor/geometry", self.saveGeometry())
        settings.setValue("material_replace_editor/state", self.saveState())
    
    def _restore_window_state(self):
        """恢复窗口状态"""
        settings = QSettings()
        geometry = settings.value("material_replace_editor/geometry")
        state = settings.value("material_replace_editor/state")
        
        if geometry:
            self.restoreGeometry(geometry)
        if state:
            self.restoreState(state)
    
    def _save_editor_state(self):
        """
        保存编辑器状态（按设计文档 13.1）
        
        窗口关闭时保存：已导入文件、材质列表、撤销历史、选中行、滚动位置、转换选项
        """
        settings = QSettings()
        
        state = EditorState(
            file_path=self._file_path,
            materials=self._materials,
            conversion_options=self._conversion_options,
            selected_row=self.material_table.currentRow(),
            scroll_position=self.material_table.verticalScrollBar().value(),
        )
        
        settings.setValue(
            self.CACHE_KEY,
            json.dumps(state.to_dict(), ensure_ascii=False)
        )
        
        # 保存撤销栈
        settings.setValue(
            f"{self.CACHE_KEY}_undo",
            json.dumps(self._undo_manager.to_dict(), ensure_ascii=False)
        )
        
        # 保存纹理面板缓存
        settings.setValue(
            f"{self.CACHE_KEY}_texture_cache",
            json.dumps(self._texture_panel_cache, ensure_ascii=False)
        )
    
    def _restore_editor_state(self):
        """恢复编辑器状态"""
        settings = QSettings()
        
        state_json = settings.value(self.CACHE_KEY)
        if not state_json:
            return
        
        try:
            state_dict = json.loads(state_json)
            state = EditorState.from_dict(state_dict)
            
            self._materials = state.materials
            self._file_path = state.file_path
            self._conversion_options = state.conversion_options
            
            # 恢复撤销栈
            undo_json = settings.value(f"{self.CACHE_KEY}_undo")
            if undo_json:
                undo_dict = json.loads(undo_json)
                self._undo_manager = UndoRedoManager.from_dict(undo_dict, MaterialEntry)
                self._undo_manager.add_listener(self._update_undo_redo_state)
            
            # 恢复纹理面板缓存
            cache_json = settings.value(f"{self.CACHE_KEY}_texture_cache")
            if cache_json:
                self._texture_panel_cache = json.loads(cache_json)
            
            # 刷新UI
            self._refresh_table()
            
            # 恢复选中行和滚动位置
            if state.selected_row >= 0:
                self.material_table.selectRow(state.selected_row)
            if state.scroll_position > 0:
                self.material_table.verticalScrollBar().setValue(state.scroll_position)
            
            # 更新窗口标题
            if self._file_path:
                self.setWindowTitle(
                    f"{_('material_replace_editor_title')} - {Path(self._file_path).name}"
                )
            
            logger.info("Editor state restored")
        except Exception as e:
            logger.error(f"Failed to restore editor state: {e}")
    
    def _clear_editor_state_cache(self):
        """清除编辑器状态缓存（导出成功后）"""
        settings = QSettings()
        settings.remove(self.CACHE_KEY)
        settings.remove(f"{self.CACHE_KEY}_undo")
        settings.remove(f"{self.CACHE_KEY}_texture_cache")
    
    # ==================== 关闭事件 ====================
    
    def closeEvent(self, event: QCloseEvent):
        """关闭事件"""
        # 检查未保存更改
        if self._has_unsaved_changes():
            from src.gui_qt.standard_dialogs import show_unsaved_changes_dialog
            result = show_unsaved_changes_dialog(self)
            
            if result == QMessageBox.StandardButton.Save:
                if not self._on_export():
                    event.ignore()
                    return
            elif result == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            # StandardButton.Discard -> 继续关闭
        
        # 保存窗口状态
        self._save_window_state()
        
        # 保存编辑器状态（只在有数据时保存）
        if self._materials:
            self._save_editor_state()
        
        # 关闭所有子窗口（安全地处理已删除的面板）
        for panel in list(self._texture_panels.values()):
            try:
                if panel is not None:
                    panel.close()
            except RuntimeError:
                # 面板已被删除，忽略
                pass
        
        event.accept()
    
    # ==================== 公共方法 ====================
    
    def get_material(self, index: int) -> Optional[MaterialEntry]:
        """获取材质"""
        if 0 <= index < len(self._materials):
            return self._materials[index]
        return None
    
    def get_materials(self) -> List[MaterialEntry]:
        """获取所有材质"""
        return self._materials.copy()
    
    def update_material(self, index: int, material: MaterialEntry, create_undo: bool = True):
        """
        更新材质
        
        Args:
            index: 材质索引
            material: 新的材质数据
            create_undo: 是否创建撤销记录
        """
        if index < 0 or index >= len(self._materials):
            return
        
        old_material = self._materials[index]
        
        if create_undo:
            action = create_undo_action(
                action_type='update_material',
                description=f"{_('update_material')}: {old_material.name}",
                material_index=index,
                before_state=old_material,
                after_state=material,
            )
            self._undo_manager.push(action)
        
        material.is_modified = True
        self._materials[index] = material
        self._refresh_table()
    
    def _on_edit_material_at(self, index: int):
        """编辑指定索引的材质"""
        self._open_texture_panel(index)
