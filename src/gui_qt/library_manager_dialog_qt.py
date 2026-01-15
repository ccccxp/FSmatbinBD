from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableView,
    QHeaderView,
    QMessageBox,
    QLineEdit,
    QTextEdit,
    QFileDialog,
)

from src.core.i18n import _



@dataclass(frozen=True)
class _LibraryRow:
    id: int
    name: str
    source_path: str
    material_count: int


class _LibraryTableModel(QAbstractTableModel):
    COL_NAME = 0
    COL_PATH = 1
    COL_COUNT = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: List[_LibraryRow] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
        return 0 if parent.isValid() else 3

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):  # type: ignore[override]
        if role != Qt.DisplayRole or orientation != Qt.Horizontal:
            return None
        if section == self.COL_NAME:
            return _('library_name_column')
        if section == self.COL_PATH:
            return _('library_path_column')
        if section == self.COL_COUNT:
            return _('material_count_column')
        return None

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):  # type: ignore[override]
        if not index.isValid():
            return None
        row = self._rows[index.row()]

        if role in (Qt.DisplayRole, Qt.ToolTipRole):
            if index.column() == self.COL_NAME:
                return row.name
            if index.column() == self.COL_PATH:
                return row.source_path
            if index.column() == self.COL_COUNT:
                return str(row.material_count)

        if role == Qt.TextAlignmentRole:
            if index.column() == self.COL_COUNT:
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        return None

    def load_rows(self, rows: List[_LibraryRow]):
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def library_id_at(self, row: int) -> Optional[int]:
        if row < 0 or row >= len(self._rows):
            return None
        return self._rows[row].id

    def library_at(self, row: int) -> Optional[_LibraryRow]:
        if row < 0 or row >= len(self._rows):
            return None
        return self._rows[row]


class LibraryManagerDialogQt(QDialog):
    """Qt 版“库管理”对话框：三列表 + 刷新/重扫/删除/关闭。

    合同：
    - 输入：MaterialDatabase 实例，外部 refresh_callback()
    - 输出：操作后 emit librariesChanged 并调用 refresh_callback
    """

    librariesChanged = Signal()

    def __init__(self, parent, database, refresh_callback=None, add_library_callback=None, version_tag: str = ""):
        super().__init__(parent)
        
        # 应用深色标题栏
        from .dark_titlebar import apply_dark_titlebar_to_dialog
        apply_dark_titlebar_to_dialog(self)
        
        self._version_tag = version_tag
        self._add_library_callback = add_library_callback
        title = _('library_manager_button')
        self.setWindowTitle(title)
        self.resize(760, 520)

        self._db = database
        self._refresh_callback = refresh_callback

        self._model = _LibraryTableModel(self)

        self._build_ui()
        self.reload()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        title = QLabel(self.windowTitle())
        title.setStyleSheet("font-weight:600; font-size:14px;")
        root.addWidget(title)

        self.table = QTableView()
        self.table.setModel(self._model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)
        # 确保可点击选中（避免被全局 QSS/焦点策略影响）
        self.table.setFocusPolicy(Qt.StrongFocus)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.setStyleSheet(
            "QTableView::item:selected { background-color: rgba(87, 140, 255, 0.22); }"
            "QTableView::item:selected:active { background-color: rgba(87, 140, 255, 0.28); }"
        )

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(_LibraryTableModel.COL_NAME, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(_LibraryTableModel.COL_PATH, QHeaderView.Stretch)
        header.setSectionResizeMode(_LibraryTableModel.COL_COUNT, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(lambda _idx: self._on_edit())

        root.addWidget(self.table, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        root.addLayout(btn_row)

        self.add_btn = QPushButton(_('add_library_button_ellipsis'))
        self.add_btn.setObjectName("glass")
        self.refresh_btn = QPushButton(_('menu_refresh'))
        self.refresh_btn.setObjectName("glass")
        self.edit_btn = QPushButton(_('menu_edit'))
        self.edit_btn.setObjectName("glass")
        self.move_up_btn = QPushButton(_('move_up'))
        self.move_up_btn.setObjectName("green-glass")
        self.move_down_btn = QPushButton(_('move_down'))
        self.move_down_btn.setObjectName("pink-glass")
        self.delete_btn = QPushButton(_('delete'))
        self.delete_btn.setObjectName("danger")
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.refresh_btn)
        btn_row.addWidget(self.edit_btn)
        btn_row.addWidget(self.move_up_btn)
        btn_row.addWidget(self.move_down_btn)
        btn_row.addWidget(self.delete_btn)
        btn_row.addStretch(1)
        self.close_btn = QPushButton(_('close'))
        self.close_btn.setObjectName("glass")
        btn_row.addWidget(self.close_btn)

        self.add_btn.clicked.connect(self._on_add_library)
        self.refresh_btn.clicked.connect(self.reload)
        self.edit_btn.clicked.connect(self._on_edit)
        self.move_up_btn.clicked.connect(self._on_move_up)
        self.move_down_btn.clicked.connect(self._on_move_down)
        self.delete_btn.clicked.connect(self._on_delete)
        self.close_btn.clicked.connect(self.accept)
        self.table.selectionModel().selectionChanged.connect(self._update_move_button_states)

        if not callable(self._add_library_callback):
            self.add_btn.setEnabled(False)

    def reload(self):
        rows: List[_LibraryRow] = []
        for lib in self._safe_get_libraries():
            lid = lib.get("id")
            if lid is None:
                continue
            name = lib.get("name") or ""
            src = lib.get("source_path") or lib.get("path") or ""
            try:
                count = int(self._db.get_material_count(lid))
            except Exception:
                count = 0
            rows.append(_LibraryRow(id=int(lid), name=str(name), source_path=str(src), material_count=count))

        self._model.load_rows(rows)
        if rows:
            self.table.selectRow(0)

    def _safe_get_libraries(self) -> List[Dict[str, Any]]:
        try:
            libs = self._db.get_libraries() or []
            return libs if isinstance(libs, list) else []
        except Exception:
            return []

    def _selected_library_id(self) -> Optional[int]:
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        return self._model.library_id_at(idx.row())

    def _selected_library_row(self) -> Optional[_LibraryRow]:
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        return self._model.library_at(idx.row())

    def _update_move_button_states(self):
        """根据当前选中行更新上移/下移按钮状态"""
        idx = self.table.currentIndex()
        row_count = self._model.rowCount()
        
        if not idx.isValid() or row_count == 0:
            self.move_up_btn.setEnabled(False)
            self.move_down_btn.setEnabled(False)
            return
        
        current_row = idx.row()
        self.move_up_btn.setEnabled(current_row > 0)
        self.move_down_btn.setEnabled(current_row < row_count - 1)

    def _on_move_up(self):
        """将当前选中的库上移一位"""
        idx = self.table.currentIndex()
        if not idx.isValid() or idx.row() == 0:
            return
        
        current_row = idx.row()
        current_lib = self._model.library_at(current_row)
        prev_lib = self._model.library_at(current_row - 1)
        
        if current_lib is None or prev_lib is None:
            return
        
        try:
            if hasattr(self._db, "swap_library_order"):
                self._db.swap_library_order(current_lib.id, prev_lib.id)
            else:
                QMessageBox.warning(self, _('error'), _('db_sort_not_supported'))
                return
        except Exception as exc:
            QMessageBox.warning(self, _('error'), str(exc))
            return
        
        self.reload()
        self.table.selectRow(current_row - 1)
        self._emit_changed()

    def _on_move_down(self):
        """将当前选中的库下移一位"""
        idx = self.table.currentIndex()
        row_count = self._model.rowCount()
        if not idx.isValid() or idx.row() >= row_count - 1:
            return
        
        current_row = idx.row()
        current_lib = self._model.library_at(current_row)
        next_lib = self._model.library_at(current_row + 1)
        
        if current_lib is None or next_lib is None:
            return
        
        try:
            if hasattr(self._db, "swap_library_order"):
                self._db.swap_library_order(current_lib.id, next_lib.id)
            else:
                QMessageBox.warning(self, _('error'), _('db_sort_not_supported'))
                return
        except Exception as exc:
            QMessageBox.warning(self, _('error'), str(exc))
            return
        
        self.reload()
        self.table.selectRow(current_row + 1)
        self._emit_changed()

    def _on_delete(self):
        row = self._selected_library_row()
        if row is None:
            return

        from src.gui_qt.standard_dialogs import show_confirm_dialog
        ok = show_confirm_dialog(
            self,
            _('delete_library'),
            _('delete_library_confirm_msg').format(row.name),
            confirm_style='danger'
        )
        if not ok:
            return

        try:
            if hasattr(self._db, "delete_library"):
                self._db.delete_library(row.id)
            elif hasattr(self._db, "remove_library"):
                self._db.remove_library(row.id)
            else:
                raise RuntimeError(_('db_delete_not_supported'))
        except Exception as exc:
            QMessageBox.warning(self, _('delete_failed'), str(exc))
            return

        self.reload()
        self._emit_changed()

    def _on_add_library(self):
        if not callable(self._add_library_callback):
            return
        try:
            self._add_library_callback()
        except Exception as exc:
            QMessageBox.warning(self, _('add_library'), str(exc))
            return
        # 导入可能是后台线程；这里先刷新一次，导入完成后主窗口也会刷新。
        self.reload()
        self._emit_changed()

    def _on_edit(self):
        row = self._selected_library_row()
        if row is None:
            return

        raw = None
        for lib in self._safe_get_libraries():
            if lib.get("id") == row.id:
                raw = lib
                break
        if raw is None:
            QMessageBox.warning(self, _('edit_library'), _('cannot_get_library_info'))
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(_('edit_library'))
        dlg.resize(620, 320)

        root = QVBoxLayout(dlg)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        title = QLabel(_('edit_library_title').format(name=raw.get('name', '')))
        title.setStyleSheet("font-weight:600; font-size:14px;")
        root.addWidget(title)

        root.addWidget(QLabel(_('library_name_column')))
        name_edit = QLineEdit(str(raw.get("name") or ""))
        name_edit.setPlaceholderText(_('library_name_placeholder'))
        root.addWidget(name_edit)

        root.addWidget(QLabel(_('library_path_label')))
        path_row = QHBoxLayout()
        path_edit = QLineEdit(str(raw.get("source_path") or raw.get("path") or ""))
        path_edit.setPlaceholderText(_('library_path_label'))
        browse_btn = QPushButton(_('browse_button'))
        browse_btn.setObjectName("glass")
        path_row.addWidget(path_edit, 1)
        path_row.addWidget(browse_btn)
        root.addLayout(path_row)

        root.addWidget(QLabel(_('library_description')))
        desc_edit = QTextEdit(str(raw.get("description") or ""))
        desc_edit.setPlaceholderText(_('description_placeholder'))
        desc_edit.setFixedHeight(90)
        root.addWidget(desc_edit)

        def choose_path():
            p = QFileDialog.getExistingDirectory(dlg, _('select_library_path'))
            if p:
                path_edit.setText(p)

        browse_btn.clicked.connect(choose_path)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = QPushButton(_('cancel'))
        cancel_btn.setObjectName("glass")
        ok_btn = QPushButton(_('save'))
        ok_btn.setObjectName("primary")
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)
        cancel_btn.clicked.connect(dlg.reject)

        def save():
            name = name_edit.text().strip()
            if not name:
                QMessageBox.warning(dlg, _('edit_library'), _('library_name_empty'))
                return
            new_path = path_edit.text().strip()
            new_desc = desc_edit.toPlainText().strip()
            try:
                self._db.update_library(row.id, name=name, description=new_desc, source_path=new_path)
            except TypeError:
                # 兼容旧签名（若未更新 database.py）
                self._db.update_library(row.id, name=name, description=new_desc)
                QMessageBox.information(dlg, _('info'), _('update_path_not_supported'))
            except Exception as exc:
                QMessageBox.warning(dlg, _('save_failed'), str(exc))
                return
            dlg.accept()

        ok_btn.clicked.connect(save)

        if dlg.exec() == QDialog.Accepted:
            self.reload()
            self._emit_changed()

    def _emit_changed(self):
        try:
            self.librariesChanged.emit()
        except Exception:
            pass

        if callable(self._refresh_callback):
            try:
                self._refresh_callback()
            except Exception:
                pass
