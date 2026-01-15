from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHeaderView, QFrame, QHBoxLayout, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt
from PySide6.QtCore import QSettings

from src.core.i18n import _
from .smooth_scroll import SmoothTableView


class SamplerPanel(QFrame):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("SamplerSection")
        # 外层统一“深色卡片”风格（贴近参考图）
        self.setStyleSheet(
            "QFrame#SamplerSection {"
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
            "stop:0 rgba(22, 30, 46, 235),"
            "stop:1 rgba(12, 16, 28, 235));"
            # 外层边框压暗，避免出现明显的“白边框”
            "border: 1px solid rgba(255,255,255,8);"
            "border-radius: 18px;"
            "}"
        )

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(36)
        shadow.setOffset(0, 14)
        shadow.setColor(Qt.black)
        self.setGraphicsEffect(shadow)

        # 列宽记忆
        self._settings = QSettings("FSmatbinBD", "SamplerPanel")
        self._restoring_columns = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 12)
        layout.setSpacing(6)

        # 标题 + 备注同一行（减少占用高度）
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        title = QLabel("🖼 " + _('sampler_panel_title'))  # Icon + title
        title.setStyleSheet(
            "font-weight: 800; font-size: 12pt; color: #f1f5ff;"
            "background: transparent; border: none; padding: 0px;"
        )
        header_row.addWidget(title)
        self.sampler_title_label = title  # Store reference for i18n refresh

        self.count_label = QLabel("")
        self.count_label.setStyleSheet(
            "color: rgba(190,200,220,175); font-size: 9pt;"
            "background: transparent; border: none; padding: 0px;"
        )
        header_row.addWidget(self.count_label)

        header_row.addStretch()

        self.hint_label = QLabel(_('sampler_panel_hint'))
        self.hint_label.setStyleSheet(
            "color: rgba(190,200,220,175); font-size: 9pt;"
            "background: transparent; border: none; padding: 0px;"
        )
        header_row.addWidget(self.hint_label)

        layout.addLayout(header_row)

        # 表格（使用平滑滚动）
        self.table = SmoothTableView()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(SmoothTableView.SelectRows)
        self.table.setSelectionMode(SmoothTableView.SingleSelection)
        self.table.setStyleSheet("""
            QTableView {
                background: rgba(10, 14, 24, 160);
                alternate-background-color: rgba(255, 255, 255, 5);
                gridline-color: rgba(255, 255, 255, 8);
                border: 1px solid rgba(110, 165, 255, 90);
                border-radius: 14px;
                font-size: 9pt;
            }
            QTableView::item {
                padding: 6px 10px;
            }
            QTableView::item:hover {
                background-color: rgba(47, 129, 247, 18);
            }
            QTableView::item:selected {
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
        
        # 配置表头
        header = self.table.horizontalHeader()
        # 表格铺满整个区域
        header.setStretchLastSection(False)
        # 默认 Interactive，具体列的模式在 _apply_column_widths 中设置
        header.setSectionResizeMode(QHeaderView.Interactive)

        # 监听用户拖拽调整列宽并持久化
        header.sectionResized.connect(self._on_section_resized)
        
        self.table.verticalHeader().setDefaultSectionSize(26)
        self.table.setMaximumHeight(200)
        
        # 双击复制功能
        self.table.doubleClicked.connect(self._on_double_click)
        
        layout.addWidget(self.table, 1)

    def _settings_key(self) -> str:
        return "column_widths"

    def _restore_column_widths(self):
        """恢复用户保存的所有列宽度"""
        header = self.table.horizontalHeader() if hasattr(self, 'table') else None
        model = self.table.model() if hasattr(self, 'table') else None
        if header is None or model is None:
            return False

        saved = self._settings.value(self._settings_key())
        if not saved:
            return False

        try:
            if isinstance(saved, str):
                parts = [p for p in saved.split(',') if p.strip()]
                widths = [int(p) for p in parts]
            else:
                widths = [int(x) for x in list(saved)]
        except Exception:
            return False

        if not widths:
            return False

        self._restoring_columns = True
        try:
            col_count = model.columnCount()
            # 恢复所有列的宽度
            for i, w in enumerate(widths):
                if i < col_count and w > 10:
                    header.resizeSection(i, w)
            return True
        finally:
            self._restoring_columns = False

    def _save_column_widths(self):
        """保存所有列的宽度"""
        header = self.table.horizontalHeader() if hasattr(self, 'table') else None
        model = self.table.model() if hasattr(self, 'table') else None
        if header is None or model is None:
            return

        col_count = model.columnCount()
        # 保存所有列的宽度
        widths = []
        for col in range(col_count):
            widths.append(header.sectionSize(col))
        if widths:
            self._settings.setValue(self._settings_key(), ",".join(str(w) for w in widths))

    def _on_section_resized(self, logicalIndex: int, oldSize: int, newSize: int):
        # 恢复阶段会触发 resize，不应写回
        if self._restoring_columns:
            return
        # newSize=0 可能来自隐藏列；这里保持容错
        self._save_column_widths()

    def _on_double_click(self, index):
        """双击单元格复制内容到剪贴板"""
        if not index.isValid():
            return
        
        from PySide6.QtWidgets import QApplication
        text = str(index.data())
        QApplication.clipboard().setText(text)
        
        # 更新提示信息
        self.count_label.setText(_('sampler_copied_hint').format(text[:30]))
        
        # 3秒后恢复
        from PySide6.QtCore import QTimer
        QTimer.singleShot(3000, self._restore_hint)
    
    def _restore_hint(self):
        """恢复提示信息"""
        if hasattr(self, 'table') and self.table.model():
            count = self.table.model().rowCount()
            self.count_label.setText(_('sampler_layout_count').format(count))

    def set_model(self, model):
        self.table.setModel(model)
        # 初始化时 model 可能没数据，列宽设置留到 on_data_loaded
        if model and model.rowCount() > 0:
            self.count_label.setText(_('sampler_layout_count').format(model.rowCount()))
            self._apply_column_widths()
        else:
            self.count_label.setText("")

    def on_data_loaded(self):
        """当 model 数据加载完成后调用，用于设置列宽"""
        model = self.table.model()
        if model and model.rowCount() > 0:
            self.count_label.setText(_('sampler_layout_count').format(model.rowCount()))
            self._apply_column_widths()

    def _apply_column_widths(self):
        """应用列宽：所有列均可调整宽度，路径列显示完整内容"""
        model = self.table.model()
        if not model:
            return
            
        col_count = model.columnCount()
        if col_count == 0:
            return
        
        header = self.table.horizontalHeader()
        
        # 列顺序: 类型(0), 路径(1), Key(2), X(3), Y(4)
        # 所有列均使用 Interactive 模式，允许用户调整宽度
        # 设置合理的默认宽度，路径列给予较大宽度以显示完整路径
        
        # 默认列宽设置
        default_widths = {
            0: 200,   # 类型 - 较大宽度
            1: 300,   # 路径 - 更大宽度以显示完整路径
            2: 100,   # Key
            3: 45,    # X
            4: 45,    # Y
        }
        
        # 所有列均使用 Interactive 模式（用户可调整）
        for col in range(col_count):
            header.setSectionResizeMode(col, QHeaderView.Interactive)
        
        # 尝试恢复用户保存的列宽度（所有列）
        restored = self._restore_column_widths()
        
        # 如果没有恢复保存的宽度，应用默认宽度
        if not restored:
            for col, width in default_widths.items():
                if col < col_count:
                    header.resizeSection(col, width)
        
        # 最后一列不自动拉伸，保持用户设定的宽度
        header.setStretchLastSection(False)
        
        # 强制刷新视图
        self.table.viewport().update()

    def clear(self):
        self.table.setModel(None)
        self.count_label.setText("")
    
    def refresh_translations(self):
        """刷新翻译文本（语言切换时调用）"""
        # 标题和提示
        if hasattr(self, 'sampler_title_label') and self.sampler_title_label:
            self.sampler_title_label.setText("🖼 " + _('sampler_panel_title'))
        self.hint_label.setText(_('sampler_panel_hint'))
        # 计数标签需要根据当前数据刷新
        if hasattr(self, 'table') and self.table.model():
            count = self.table.model().rowCount()
            self.count_label.setText(_('sampler_layout_count').format(count))

