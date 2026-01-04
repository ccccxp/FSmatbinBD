from __future__ import annotations

import os
from typing import Optional, Dict, Any

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTextEdit,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QWidget,
    QGroupBox,
)
from src.core.i18n import _



class _DCXImportWorker(QThread):
    finishedResult = Signal(dict)

    def __init__(self, database, dcx_file: str, library_name: str, description: str):
        super().__init__()
        self._database = database
        self._dcx_file = dcx_file
        self._library_name = library_name
        self._description = description

    def run(self):
        try:
            from src.core.witchybnd_processor import MaterialLibraryImporter

            importer = MaterialLibraryImporter(self._database)
            result = importer.import_from_dcx(self._dcx_file, self._library_name, self._description)
            if not isinstance(result, dict):
                result = {
                    "success": False,
                    "error": "导入器未返回有效结果",
                    "library_id": None,
                    "material_count": 0,
                }
            self.finishedResult.emit(result)
        except Exception as exc:
            self.finishedResult.emit(
                {
                    "success": False,
                    "error": str(exc),
                    "library_id": None,
                    "material_count": 0,
                }
            )


class DCXImportDialogQt(QDialog):
    """Qt版 DCX 材质库导入对话框。

    对齐旧版 Tk 的 `DCXImportDialog`：
    - 选择 DCX 文件
    - 输入库名称/描述
    - 显示导入进度（简化：不细分阶段，仅显示忙碌状态）
    - 后台线程调用 `MaterialLibraryImporter.import_from_dcx`
    """

    imported = Signal(dict)

    def __init__(self, parent: Optional[QWidget], database):
        super().__init__(parent)
        
        # 应用深色标题栏
        from .dark_titlebar import apply_dark_titlebar_to_dialog
        apply_dark_titlebar_to_dialog(self)
        
        apply_dark_titlebar_to_dialog(self)
        
        self.setWindowTitle(_('import_dcx_title'))
        self.setModal(True)
        self.resize(720, 560)

        self._database = database
        self._worker: Optional[_DCXImportWorker] = None

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel(_('import_dcx_title'))
        title.setStyleSheet("font-size: 12pt; font-weight: 700;")
        layout.addWidget(title)

        hint = QLabel(_('import_dcx_hint'))
        hint.setStyleSheet("color:#9ca9c5;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        file_box = QGroupBox(_('dcx_files'))
        file_box.setStyleSheet(
            "QGroupBox { background-color:#0d1222; border:1px solid #313b5c; border-radius:10px; margin-top:12px; padding:12px; }"
            "QGroupBox::title { subcontrol-origin: margin; left:12px; padding:0 6px; background-color:#0d1222; }"
        )
        file_layout = QHBoxLayout(file_box)
        self.dcx_path_edit = QLineEdit()
        self.dcx_path_edit.setPlaceholderText(_('select_dcx_placeholder'))
        browse_btn = QPushButton(_('browse_button'))
        browse_btn.setObjectName("standard")
        browse_btn.clicked.connect(self._choose_dcx)
        file_layout.addWidget(self.dcx_path_edit, 1)
        file_layout.addWidget(browse_btn)
        layout.addWidget(file_box)

        info_box = QGroupBox(_('library_info'))
        info_box.setStyleSheet(
            "QGroupBox { background-color:#0d1222; border:1px solid #313b5c; border-radius:10px; margin-top:12px; padding:12px; }"
            "QGroupBox::title { subcontrol-origin: margin; left:12px; padding:0 6px; background-color:#0d1222; }"
        )
        info_layout = QVBoxLayout(info_box)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(_('library_name_placeholder'))
        info_layout.addWidget(self.name_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText(_('description_placeholder'))
        self.desc_edit.setFixedHeight(90)
        info_layout.addWidget(self.desc_edit)

        layout.addWidget(info_box)

        self.progress_label = QLabel(_('waiting_start'))
        self.progress_label.setStyleSheet("color:#9ca9c5;")
        layout.addWidget(self.progress_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.cancel_btn = QPushButton(_('cancel'))
        self.cancel_btn.setObjectName("ghost")
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        self.start_btn = QPushButton(_('start_import'))
        self.start_btn.setObjectName("primary")
        self.start_btn.clicked.connect(self._start)
        btn_row.addWidget(self.start_btn)

        layout.addLayout(btn_row)

    def _choose_dcx(self):
        file_path, _unused = QFileDialog.getOpenFileName(self, _('select_dcx_file'), filter="DCX Files (*.dcx);;All Files (*.*)")
        if not file_path:
            return
        self.dcx_path_edit.setText(file_path)
        if not self.name_edit.text().strip():
            base = os.path.splitext(os.path.basename(file_path))[0]
            self.name_edit.setText(base)

    def _set_busy(self, busy: bool):
        self.start_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(not busy)
        self.progress.setValue(1 if busy else 0)
        self.progress_label.setText(_('importing_wait') if busy else _('waiting_start'))

    def _start(self):
        dcx_file = self.dcx_path_edit.text().strip()
        lib_name = self.name_edit.text().strip()
        desc = self.desc_edit.toPlainText().strip()

        if not dcx_file:
            QMessageBox.warning(self, "导入DCX", please_select_dcx)
            return
        if not os.path.exists(dcx_file):
            QMessageBox.warning(self, _('import_dcx_title'), _('file_not_found') + f": {dcx_file}")
            return
        if not lib_name:
            QMessageBox.warning(self, _('import_dcx_title'), _('please_input_library_name'))
            return

        self._set_busy(True)
        self._worker = _DCXImportWorker(self._database, dcx_file, lib_name, desc)
        self._worker.finishedResult.connect(self._on_finished)
        self._worker.start()

    def _on_finished(self, result: Dict[str, Any]):
        self._set_busy(False)

        if result.get("success"):
            QMessageBox.information(
                self,
                _('import_complete_title'),
                _('import_dcx_success_msg').format(lib_id=result.get('library_id'), count=result.get('material_count', 0)),
            )
            self.imported.emit(result)
            self.accept()
        else:
            QMessageBox.warning(self, _('import_failed'), _('import_dcx_failed_msg').format(error=result.get('error', '未知错误')))
