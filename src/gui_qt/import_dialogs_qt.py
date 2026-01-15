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
    QComboBox,
    QFrame,
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


class ImportSingleXmlDialog(QDialog):
    """单XML文件导入对话框：预览并编辑信息，选择目标库。"""

    def __init__(self, parent, db, material_data, current_lib_id=None):
        super().__init__(parent)
        self.db = db
        self.material_data = material_data.copy() # Work on a copy
        self.result_library_id = None
        self.result_new_lib_info = None  # (name, desc)
        
        # 应用深色标题栏
        from .dark_titlebar import apply_dark_titlebar_to_dialog
        apply_dark_titlebar_to_dialog(self)

        self.setWindowTitle(_('import_single_dialog_title'))
        self.setModal(True)
        self.resize(550, 400)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 获取初始值
        current_filename = self.material_data.get('filename') or self.material_data.get('file_name') or ""
        # 优先使用 XML 解析出的 source_path (游戏内引用路径)，
        # 如果没有则回退到 file_path (本地文件路径)
        current_filepath = self.material_data.get('source_path') or self.material_data.get('file_path') or ""
        current_shader = self.material_data.get('shader_path') or ""
        
        # 1. 文件名
        layout.addWidget(QLabel(_('header_name')))
        self.file_name_edit = QLineEdit(current_filename)
        self.file_name_edit.setPlaceholderText(_('header_name'))
        layout.addWidget(self.file_name_edit)
        
        # 监测文件名变化以自动更新路径（用户要求取消自动推断，改为完全手动或使用解析原值）
        # self.file_name_edit.textEdited.connect(self._on_filename_edited)

        # 2. 文件路径
        layout.addWidget(QLabel(_('header_file_path')))
        self.path_edit = QLineEdit(current_filepath)
        self.path_edit.setPlaceholderText(_('header_file_path'))
        layout.addWidget(self.path_edit)

        # 3. Shader路径
        layout.addWidget(QLabel(_('header_shader_path')))
        self.shader_edit = QLineEdit(current_shader)
        self.shader_edit.setPlaceholderText(_('header_shader_path'))
        layout.addWidget(self.shader_edit)

        # 4. 库选择
        layout.addWidget(QLabel(_('target_library')))
        self.combo = QComboBox()
        libs = self.db.get_libraries()
        current_idx = 0
        for i, lib in enumerate(libs):
            self.combo.addItem(lib['name'], lib['id'])
            if current_lib_id and lib['id'] == current_lib_id:
                current_idx = i
        self.combo.addItem(_('create_new_library'), -1)
        
        if libs and current_lib_id:
            self.combo.setCurrentIndex(current_idx)
        elif not libs:
            self.combo.setCurrentIndex(0)

        layout.addWidget(self.combo)

        # 5. 新建库面板
        self.new_lib_frame = QFrame()
        nf_layout = QVBoxLayout(self.new_lib_frame)
        nf_layout.setContentsMargins(0, 5, 0, 5)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(_('library_name_placeholder'))
        self.name_edit.setText(current_filename) # 默认库名为文件名
        
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText(_('description_placeholder'))
        
        nf_layout.addWidget(self.name_edit)
        nf_layout.addWidget(self.desc_edit)
        layout.addWidget(self.new_lib_frame)

        # 按钮
        btn_box = QHBoxLayout()
        btn_box.addStretch(1)
        self.btn_cancel = QPushButton(_('cancel'))
        self.btn_ok = QPushButton(_('ok'))
        self.btn_ok.setObjectName("primary")
        
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self._on_ok)
        
        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_ok)
        layout.addLayout(btn_box)

        self.combo.currentIndexChanged.connect(self._on_combo_changed)
        self._on_combo_changed(self.combo.currentIndex()) # Init state

    def _on_combo_changed(self, index):
        lib_id = self.combo.itemData(index)
        is_new = (lib_id == -1)
        self.new_lib_frame.setVisible(is_new)
    
    def _on_ok(self):
        # Validate Filename
        name_input = self.file_name_edit.text().strip()
        if not name_input:
            self.file_name_edit.setFocus()
            return

        # Update material_data
        self.material_data['filename'] = name_input
        self.material_data['file_name'] = name_input # Sync logic name
        self.material_data['file_path'] = self.path_edit.text().strip()
        # 同步更新 source_path (用户编辑的文件路径实际上是 SourcePath)
        self.material_data['source_path'] = self.path_edit.text().strip()
        self.material_data['shader_path'] = self.shader_edit.text().strip()

        # Library selection
        lib_id = self.combo.currentData()
        if lib_id == -1:
            name = self.name_edit.text().strip()
            if not name:
                self.name_edit.setFocus()
                return
            self.result_new_lib_info = (name, self.desc_edit.text().strip())
            self.result_library_id = None
        else:
            self.result_library_id = lib_id
            self.result_new_lib_info = None
            
        self.accept()
