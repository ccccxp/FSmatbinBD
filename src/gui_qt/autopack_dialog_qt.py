from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableView,
    QHeaderView,
    QFileDialog,
    QLineEdit,
    QMessageBox,
    QAbstractItemView,
    QWidget,
    QGroupBox,
)

from src.core.autopack_manager import AutoPackManager
from src.core.i18n import _


@dataclass
class AutoPackItem:
    id: int
    filename: str
    xml_file: str
    matbin_file: str
    target_path: str
    added_time: str


class _AutoPackTableModel(QAbstractTableModel):
    # 新增 "选择" 列作为第一列，"来源" 列显示来源信息
    COLS = ["select", "ID", "menu_file", "source", "target_path_column", "added_time_column"]

    def __init__(self, items: Optional[List[Dict[str, Any]]] = None):
        super().__init__()
        self._items: List[Dict[str, Any]] = items or []
        self._checked: List[bool] = []  # 选中状态
    
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._items)
    
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.COLS)
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            if 0 <= section < len(self.COLS):
                key = self.COLS[section]
                if key == "select": return _('select')
                if key == "ID": return _('autopack_id')
                if key == "menu_file": return _('menu_file')
                if key == "source": return _('source')
                if key == "target_path_column": return _('target_path_column')
                if key == "added_time_column": return _('added_time_column')
                return key
        return None

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        item = self._items[index.row()]
        col = index.column()

        if role == Qt.CheckStateRole:
            if col == 0:  # 选择列
                return Qt.Checked if self._checked[index.row()] else Qt.Unchecked
        
        if role == Qt.DisplayRole:
            if col == 0:  # 选择列不显示文本
                return None
            if col == 1:
                return str(item.get("id", ""))
            if col == 2:
                return str(item.get("filename", ""))
            if col == 3:
                # 来源：数据库或文件路径
                if item.get("material_id") and not item.get("xml_file"):
                    return _('from_database')
                elif item.get("xml_file"):
                    return str(item.get("xml_file", ""))
                else:
                    return "-"
            if col == 4:
                return str(item.get("target_path", ""))
            if col == 5:
                return str(item.get("added_time", ""))

        if role == Qt.TextAlignmentRole:
            if col in [0, 1]:
                return Qt.AlignCenter
            return Qt.AlignVCenter | Qt.AlignLeft

        return None
    
    def setData(self, index: QModelIndex, value, role: int = Qt.EditRole) -> bool:
        if not index.isValid():
            return False
        if role == Qt.CheckStateRole and index.column() == 0:
            self._checked[index.row()] = (value == Qt.Checked)
            self.dataChanged.emit(index, index, [role])
            return True
        return False

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.NoItemFlags
        if index.column() == 0:  # 选择列可勾选
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def get_item(self, row: int) -> Optional[Dict[str, Any]]:
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def get_selected_ids(self, selection_model) -> List[int]:
        """获取表格选中行的ID（用于行选择）"""
        rows = sorted({idx.row() for idx in selection_model.selectedRows()})
        ids: List[int] = []
        for r in rows:
            item = self.get_item(r)
            if item and isinstance(item.get("id"), int):
                ids.append(item["id"])
        return ids
    
    def get_checked_ids(self) -> List[int]:
        """获取复选框勾选的项目ID（用于封包）"""
        ids: List[int] = []
        for i, checked in enumerate(self._checked):
            if checked:
                item = self.get_item(i)
                if item and isinstance(item.get("id"), int):
                    ids.append(item["id"])
        return ids
    
    def select_all(self, checked: bool = True):
        """全选/全不选"""
        for i in range(len(self._checked)):
            self._checked[i] = checked
        if self._items:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self._items) - 1, 0),
                [Qt.CheckStateRole]
            )
    
    def load(self, items: List[Dict[str, Any]]):
        """加载新数据"""
        self.beginResetModel()
        self._items = items or []
        self._checked = [False] * len(self._items)  # 初始化选中状态
        self.endResetModel()


class AutoPackDialogQt(QDialog):
    """Qt版自动封包管理器（替代Tkinter AutoPackDialog）。

    目标：解决Qt/Tkinter混用导致的grab冲突，并提供可用的封包队列管理能力。
    """

    def __init__(self, parent: Optional[QWidget], manager: Optional[AutoPackManager] = None):
        super().__init__(parent)
        
        # 应用深色标题栏
        from .dark_titlebar import apply_dark_titlebar_to_dialog
        apply_dark_titlebar_to_dialog(self)
        
        self.setWindowTitle(_('autopack_dialog_title'))
        self.setModal(True)
        self.resize(980, 640)

        self.manager = manager or AutoPackManager()
        self.model = _AutoPackTableModel([])

        self._build_ui()
        self.reload()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 统计区
        stats_box = QGroupBox(_('statistics_info'))
        stats_box.setStyleSheet(
            """
            QGroupBox {
                background-color: #0d1222;
                border: 1px solid #313b5c;
                border-radius: 10px;
                margin-top: 12px;
                padding: 12px;
                color: #f5f7ff;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                background-color: #0d1222;
            }
            """
        )
        stats_layout = QHBoxLayout(stats_box)
        stats_layout.setContentsMargins(10, 12, 10, 10)

        self.stats_label = QLabel("-")
        self.stats_label.setStyleSheet("color:#9ca9c5; font-size:11px;")
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch(1)

        self.base_pack_dir_edit = QLineEdit()
        self.base_pack_dir_edit.setPlaceholderText(_('pack_base_dir'))
        self.base_pack_dir_edit.setMinimumWidth(420)
        stats_layout.addWidget(self.base_pack_dir_edit)

        browse_btn = QPushButton(_('browse_button'))
        from src.gui_qt.standard_dialogs import apply_button_style
        apply_button_style(browse_btn, 'orange-transparent')
        browse_btn.clicked.connect(self._choose_base_dir)
        stats_layout.addWidget(browse_btn)

        layout.addWidget(stats_box)

        # 表格
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.verticalHeader().setDefaultSectionSize(26)
        # 连接点击信号以切换复选框
        self.table.clicked.connect(self._on_table_clicked)
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
        layout.addWidget(self.table, 1)

        # 操作区
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        # 全选/取消全选按钮
        # 全选/取消全选按钮
        select_all_btn = QPushButton(_('select_all'))
        apply_button_style(select_all_btn, 'glass')
        select_all_btn.clicked.connect(lambda: self.model.select_all(True))
        btn_row.addWidget(select_all_btn)

        deselect_all_btn = QPushButton(_('deselect_all'))
        apply_button_style(deselect_all_btn, 'glass')
        deselect_all_btn.clicked.connect(lambda: self.model.select_all(False))
        btn_row.addWidget(deselect_all_btn)

        add_xml_btn = QPushButton(_('add_xml_button_text'))
        apply_button_style(add_xml_btn, 'glass')
        add_xml_btn.clicked.connect(self._add_xml)
        btn_row.addWidget(add_xml_btn)

        set_target_btn = QPushButton(_('set_selected'))
        apply_button_style(set_target_btn, 'glass')
        set_target_btn.clicked.connect(self._set_target_path)
        btn_row.addWidget(set_target_btn)

        remove_btn = QPushButton(_('remove_selected'))
        apply_button_style(remove_btn, 'danger')
        remove_btn.clicked.connect(self._remove_selected)
        btn_row.addWidget(remove_btn)

        btn_row.addStretch(1)

        refresh_btn = QPushButton(_('menu_refresh'))
        apply_button_style(refresh_btn, 'glass')
        refresh_btn.clicked.connect(self.reload)
        btn_row.addWidget(refresh_btn)

        exec_btn = QPushButton(_('execute_pack'))
        apply_button_style(exec_btn, 'solid-blue')
        exec_btn.clicked.connect(self._execute)
        btn_row.addWidget(exec_btn)

        close_btn = QPushButton(_('close'))
        apply_button_style(close_btn, 'glass')
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    def _choose_base_dir(self):
        folder = QFileDialog.getExistingDirectory(self, _('select_base_pack_dir'))
        if folder:
            self.base_pack_dir_edit.setText(folder)
    
    def _on_table_clicked(self, index: QModelIndex):
        """处理表格点击，切换复选框状态"""
        if index.column() == 0:  # 第一列是复选框列
            current_state = self.model._checked[index.row()]
            new_state = Qt.Unchecked if current_state else Qt.Checked
            self.model.setData(index, new_state, Qt.CheckStateRole)

    def reload(self):
        items = self.manager.get_pending_list()
        self.model.load(items)
        stats = self.manager.get_statistics()
        self.stats_label.setText(
            _('autopack_pending').format(stats.get('total_pending', 0), stats.get('with_target_path', 0), stats.get('without_target_path', 0))
        )
        self.table.resizeColumnsToContents()

    def _add_xml(self):
        files, _unused = QFileDialog.getOpenFileNames(self, _('select_xml_to_pack'), filter="XML Files (*.xml)")
        if not files:
            return
        ok = 0
        failed: List[str] = []
        for f in files:
            try:
                self.manager.add_to_autopack(f)
                ok += 1
            except Exception as exc:
                failed.append(f"{f}: {exc}")
        self.reload()
        if failed:
            QMessageBox.warning(self, _('partial_failure'), "\n".join(failed[:10]))
        else:
            QMessageBox.information(self, _('complete'), _('added_xml_count').format(ok))

    def _set_target_path(self):
        ids = self.model.get_selected_ids(self.table.selectionModel())
        if not ids:
            QMessageBox.information(self, _('set_target_path_title'), _('select_at_least_one'))
            return
        text, ok = QFileDialog.getExistingDirectory(self, _('select_target_dir')), True
        if not ok or not text:
            return

        # 这里按原逻辑 target_path 保存为相对路径更合理；先保存绝对路径（可后续改为rel）
        self.manager.update_target_path(ids, text)
        self.reload()

    def _remove_selected(self):
        ids = self.model.get_selected_ids(self.table.selectionModel())
        if not ids:
            return
        self.manager.remove_from_pending(ids)
        self.reload()

    def _execute(self):
        # 获取勾选的项目
        checked_ids = self.model.get_checked_ids()
        if not checked_ids:
            QMessageBox.information(self, _('pack_execute_title'), _('select_at_least_one'))
            return
        
        base_dir = self.base_pack_dir_edit.text().strip()
        if not base_dir:
            base_dir = QFileDialog.getExistingDirectory(self, _('select_base_pack_dir'))
            if not base_dir:
                return
            self.base_pack_dir_edit.setText(base_dir)

        try:
            # 传入勾选的项目ID列表
            result = self.manager.execute_autopack(base_dir, checked_ids)
            if result.get("success"):
                QMessageBox.information(
                    self,
                    _('pack_execute_title'),
                    _('pack_execute_msg').format(result.get('packed_count', 0), result.get('failed_count', 0)),
                )
            else:
                QMessageBox.warning(
                    self,
                    _('pack_execute_fail_title'),
                    str(result.get("error") or _('unknown_error')),
                )
        except Exception as exc:
            QMessageBox.warning(self, _('pack_execute_fail_title'), str(exc))
        finally:
            self.reload()
