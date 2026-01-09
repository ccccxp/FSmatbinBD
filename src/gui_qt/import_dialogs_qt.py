from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QProgressDialog,
)
from src.core.i18n import _


@dataclass
class LibraryInfo:
    name: str
    description: str


class LibraryInfoDialogQt(QDialog):
    """Qt 版库信息输入对话框（对齐旧版 LibraryInfoDialog：库名 + 描述）。"""

    def __init__(self, parent, default_name: str = ""):
        super().__init__(parent)
        
        # 应用深色标题栏
        from .dark_titlebar import apply_dark_titlebar_to_dialog
        apply_dark_titlebar_to_dialog(self)
        
        apply_dark_titlebar_to_dialog(self)
        
        self.setWindowTitle(_('library_info_title'))
        self.setModal(True)
        self.resize(520, 320)

        self.result: Optional[LibraryInfo] = None

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        root.setSpacing(10)

        title = QLabel(_('enter_library_info'))
        title.setStyleSheet("font-weight:600; font-size:13px;")
        root.addWidget(title)

        self.name_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(_('library_name_placeholder'))
        self.name_edit.setText(default_name or "")
        root.addWidget(self.name_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText(_('description_placeholder'))
        self.desc_edit.setFixedHeight(120)
        root.addWidget(self.desc_edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.cancel_btn = QPushButton(_('cancel'))
        self.cancel_btn.setObjectName("glass")
        self.ok_btn = QPushButton(_('ok_button'))
        self.ok_btn.setObjectName("primary")
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.ok_btn)
        root.addLayout(btn_row)

        self.cancel_btn.clicked.connect(self.reject)
        self.ok_btn.clicked.connect(self._on_ok)

        self.name_edit.selectAll()
        self.name_edit.setFocus(Qt.OtherFocusReason)

    def _on_ok(self):
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setFocus(Qt.OtherFocusReason)
            return
        self.result = LibraryInfo(name=name, description=self.desc_edit.toPlainText().strip())
        self.accept()


def create_busy_progress(parent, title: str, label: str) -> QProgressDialog:
    """创建一个“忙碌”进度对话框（不显示具体百分比，支持取消）。"""

def create_busy_progress(parent, title: str, label: str) -> QProgressDialog:
    """创建一个“忙碌”进度对话框（不显示具体百分比，支持取消）。"""

    dlg = QProgressDialog(label, _('cancel'), 0, 0, parent)
    dlg.setWindowTitle(title)
    dlg.setWindowModality(Qt.WindowModal)
    dlg.setMinimumDuration(0)
    dlg.setAutoClose(False)
    dlg.setAutoReset(False)
    dlg.setValue(0)
    return dlg
