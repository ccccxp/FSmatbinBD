from __future__ import annotations

import os
from typing import Optional, Dict, Any

from PySide6.QtCore import Qt, QThread, Signal, QTimer
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
    """带进度回调的DCX导入工作线程"""
    finishedResult = Signal(dict)
    progressUpdate = Signal(str, int, int)  # (阶段名称, 当前进度, 总数)

    def __init__(self, database, dcx_file: str, library_name: str, description: str):
        super().__init__()
        self._database = database
        self._dcx_file = dcx_file
        self._library_name = library_name
        self._description = description

    def _progress_callback(self, stage: str, current: int, total: int):
        """进度回调，从后台线程发送信号到主线程"""
        self.progressUpdate.emit(stage, current, total)

    def run(self):
        try:
            from src.core.witchybnd_processor import MaterialLibraryImporter

            importer = MaterialLibraryImporter(self._database)
            result = importer.import_from_dcx(
                self._dcx_file, 
                self._library_name, 
                self._description,
                progress_callback=self._progress_callback
            )
            if not isinstance(result, dict):
                result = {
                    "success": False,
                    "error": _('importer_invalid_result'),
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

    特性：
    - 选择 DCX 文件
    - 输入库名称/描述
    - 显示详细的分阶段进度
    - 动态进度条动画
    - 后台线程调用 `MaterialLibraryImporter.import_from_dcx`
    """

    imported = Signal(dict)

    def __init__(self, parent: Optional[QWidget], database):
        super().__init__(parent)
        
        # 应用深色标题栏
        from .dark_titlebar import apply_dark_titlebar_to_dialog
        apply_dark_titlebar_to_dialog(self)
        
        self.setWindowTitle(_('import_dcx_title'))
        self.setModal(True)
        self.resize(720, 560)

        self._database = database
        self._worker: Optional[_DCXImportWorker] = None
        
        # 动画相关
        self._animation_timer: Optional[QTimer] = None
        self._animation_value = 0
        self._animation_direction = 1
        self._current_stage = ""
        self._has_real_progress = False

        self._build_ui()

    def initialize(self, path: str = "", name: str = "", desc: str = ""):
        """初始化预设值（用于从外部调用，如'从文件夹导入'）"""
        if path:
            self.dcx_path_edit.setText(path)
            # 如果是文件夹，更新标题和提示
            if os.path.isdir(path):
                self.setWindowTitle(_('import_folder_dialog_header'))
                self.ui_title.setText(_('import_folder_dialog_header'))
                self.ui_hint.setText(_('import_folder_hint'))
                self.ui_file_box.setTitle(_('folder_path_group'))
                
        if name:
            self.name_edit.setText(name)
        if desc:
            self.desc_edit.setText(desc)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.ui_title = QLabel(_('import_dcx_title'))
        self.ui_title.setStyleSheet("font-size: 12pt; font-weight: 700;")
        layout.addWidget(self.ui_title)

        self.ui_hint = QLabel(_('import_dcx_hint'))
        self.ui_hint.setStyleSheet("color:#9ca9c5;")
        self.ui_hint.setWordWrap(True)
        layout.addWidget(self.ui_hint)

        self.ui_file_box = QGroupBox(_('dcx_files'))
        self.ui_file_box.setStyleSheet(
            "QGroupBox { background-color:#0d1222; border:1px solid #313b5c; border-radius:10px; margin-top:12px; padding:12px; }"
            "QGroupBox::title { subcontrol-origin: margin; left:12px; padding:0 6px; background-color:#0d1222; }"
        )
        file_layout = QHBoxLayout(self.ui_file_box)
        self.dcx_path_edit = QLineEdit()
        self.dcx_path_edit.setPlaceholderText(_('select_dcx_placeholder'))
        browse_btn = QPushButton(_('browse_button'))
        browse_btn.setObjectName("glass")
        browse_btn.clicked.connect(self._choose_dcx)
        file_layout.addWidget(self.dcx_path_edit, 1)
        file_layout.addWidget(browse_btn)
        layout.addWidget(self.ui_file_box)

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

        # 进度区域 - 包含阶段标签和详细进度
        progress_box = QGroupBox(_('import_progress'))
        progress_box.setStyleSheet(
            "QGroupBox { background-color:#0d1222; border:1px solid #313b5c; border-radius:10px; margin-top:12px; padding:12px; }"
            "QGroupBox::title { subcontrol-origin: margin; left:12px; padding:0 6px; background-color:#0d1222; }"
        )
        progress_layout = QVBoxLayout(progress_box)
        
        # 当前阶段标签
        self.stage_label = QLabel(_('waiting_start'))
        self.stage_label.setStyleSheet("color:#58a6ff; font-weight: bold; font-size: 11pt;")
        progress_layout.addWidget(self.stage_label)
        
        # 详细进度标签
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color:#9ca9c5;")
        progress_layout.addWidget(self.progress_label)

        # 进度条
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setFormat("%p%")
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #313b5c;
                border-radius: 5px;
                background-color: #1a1f35;
                text-align: center;
                color: #ffffff;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #238636, stop:1 #2ea043);
                border-radius: 4px;
            }
        """)
        progress_layout.addWidget(self.progress)
        
        layout.addWidget(progress_box)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.cancel_btn = QPushButton(_('cancel'))
        self.cancel_btn.setObjectName("glass")
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

    def _start_animation(self):
        """启动进度条动画（用于没有实际进度的阶段）"""
        if self._animation_timer is None:
            self._animation_timer = QTimer(self)
            self._animation_timer.timeout.connect(self._animate_progress)
        
        # 进入定制忙碌模式（隐藏文字，使用自定义动画）
        self.progress.setTextVisible(False)
        self._animation_value = 0
        self._animation_timer.start(20)  # 更流畅的动画 (20ms)
        
    def _stop_animation(self):
        """停止进度条动画"""
        if self._animation_timer:
            self._animation_timer.stop()
        # 恢复正常模式
        self.progress.setTextVisible(True)
            
    def _animate_progress(self):
        """进度条动画效果 - 自定义循环移动（从左到右循环）"""
        if self._has_real_progress:
            return
            
        # 锯齿波循环 (0 -> 100 -> 0)
        self._animation_value += 1
        if self._animation_value > 100:
            self._animation_value = 0
            
        self.progress.setValue(self._animation_value)

    def _set_busy(self, busy: bool):
        self.start_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(not busy)
        if busy:
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            self.stage_label.setText(_('importing_wait'))
            self.progress_label.setText("")
            self._has_real_progress = False
            self._start_animation()
        else:
            self._stop_animation()
            self.progress.setValue(0)
            self.stage_label.setText(_('waiting_start'))
            self.progress_label.setText("")

    def _on_progress(self, stage: str, current: int, total: int):
        """处理进度更新"""
        # 翻译阶段名称 - 使用 i18n 翻译键
        stage_translations = {
            "解包DCX文件": _('stage_extract_dcx'),
            "转换材质文件": _('stage_convert_matbin'), 
            "解析XML文件": _('stage_parse_xml'),
            "写入数据库": _('stage_write_db'),
            "清理临时文件": _('stage_cleanup'),
        }
        display_stage = stage_translations.get(stage, f"⏳ {stage}")
        
        # 更新阶段标签
        self.stage_label.setText(display_stage)
        self._current_stage = stage
        
        if total > 0 and total > 1:
            # 有实际进度数据
            self._has_real_progress = True
            self._stop_animation()
            percent = int((current / total) * 100)
            self.progress.setValue(percent)
            self.progress_label.setText(_('progress_format').format(current=current, total=total))
        else:
            # 没有详细进度，使用动画
            self._has_real_progress = False
            if not self._animation_timer or not self._animation_timer.isActive():
                self._start_animation()
            self.progress_label.setText(_('processing'))

    def _start(self):
        dcx_file = self.dcx_path_edit.text().strip()
        lib_name = self.name_edit.text().strip()
        desc = self.desc_edit.toPlainText().strip()

        if not dcx_file:
            QMessageBox.warning(self, _('import_dcx_title'), _('please_select_dcx_file'))
            return
        if not os.path.exists(dcx_file):
            QMessageBox.warning(self, _('import_dcx_title'), _('file_not_found') + f": {dcx_file}")
            return
        if not lib_name:
            QMessageBox.warning(self, _('import_dcx_title'), _('please_input_library_name'))
            return

        self._set_busy(True)
        self._worker = _DCXImportWorker(self._database, dcx_file, lib_name, desc)
        self._worker.progressUpdate.connect(self._on_progress)
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
            QMessageBox.warning(self, _('import_failed'), _('import_dcx_failed_msg').format(error=result.get('error', _('unknown_error'))))
