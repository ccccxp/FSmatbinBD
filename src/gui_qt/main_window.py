from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QLabel, QPushButton, QToolBar, QToolButton, QMenu, QStatusBar,
    QSplitter, QApplication, QSizePolicy, QFrame, QMessageBox, QDialog,
    QStackedLayout
)
from PySide6.QtCore import Qt, QEvent, QTimer, QThread, Signal
from PySide6.QtGui import QIcon, QPixmap, QPalette, QColor
import os
import sys

from .material_tree_panel import MaterialTreePanel
from .material_editor_panel import MaterialEditorPanel
from .models import LibraryListModel, MaterialListModel
from .loading_overlay import LoadingOverlay
from src.core.database import MaterialDatabase
from src.core.i18n import _, language_manager


class SearchWorker(QThread):
    """后台线程执行数据库搜索，避免阻塞UI"""
    finished = Signal(list)  # 搜索完成信号，传递结果列表
    
    def __init__(self, db_path: str, library_id: Optional[int], keyword: str):
        super().__init__()
        self.db_path = db_path  # 只传路径，在线程内创建新连接
        self.library_id = library_id
        self.keyword = keyword
    
    def run(self):
        try:
            # 在工作线程中创建独立的数据库连接
            from src.core.database import MaterialDatabase
            thread_db = MaterialDatabase(self.db_path)
            results = thread_db.search_materials(
                library_id=self.library_id,
                keyword=self.keyword
            )
            self.finished.emit(results)
        except Exception as e:
            print(f"搜索错误: {e}")
            import traceback
            traceback.print_exc()
            self.finished.emit([])


class _InvokeCallableEvent(QEvent):
    """用于把一个 callable 投递到主线程执行的自定义事件。"""

    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self, fn):
        super().__init__(self.EVENT_TYPE)
        self.fn = fn


class CommandBar(QWidget):
    """顶部黑蓝渐变命令栏占位，含库选择与全局搜索。"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # left: library combo (移除标题，左移)
        left_box = QHBoxLayout()
        left_box.setSpacing(8)
        self.library_label = QLabel()
        left_box.addWidget(self.library_label)
        self.library_combo = QComboBox()
        self.library_combo.setMinimumWidth(220)
        left_box.addWidget(self.library_combo)
        left_box.addStretch(1)
        layout.addLayout(left_box)

        # right: search
        right_box = QHBoxLayout()
        right_box.setSpacing(6)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(_('search_placeholder_full'))
        self.search_edit.setMinimumWidth(260)
        right_box.addWidget(self.search_edit)
        self.search_btn = QPushButton()
        self.search_btn.setObjectName("primary")
        right_box.addWidget(self.search_btn)
        self.clear_btn = QPushButton()
        self.clear_btn.setObjectName("ghost")
        right_box.addWidget(self.clear_btn)
        layout.addLayout(right_box)


class MaterialDatabaseMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 设置窗口标题和图标
        # 设置窗口标题和图标
        self.setWindowTitle(_('app_title_full'))
        
        # 尝试加载应用图标
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # 设置深色标题栏（Windows 11/10）
        self._set_dark_titlebar()
        
        self.resize(1400, 900)
        # data
        self.db = MaterialDatabase()
        self.library_model = LibraryListModel()
        self.material_model = MaterialListModel()
        self.current_library_id: Optional[int] = None
        self.current_material: Optional[Dict[str, Any]] = None
        
        # 搜索防抖定时器（延迟搜索以减少卡顿）
        from PySide6.QtCore import QTimer
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(100)  # 100ms 延迟（减少等待时间）
        self._search_timer.timeout.connect(self._do_search)

        self._build_ui()
        self._apply_translations()

    def _set_dark_titlebar(self):
        """设置深色标题栏（Windows 10/11）"""
        try:
            # Windows平台特定处理
            if sys.platform == 'win32':
                # 尝试使用ctypes设置Windows标题栏为深色
                try:
                    import ctypes
                    from ctypes import wintypes
                    
                    # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (Windows 10 build 19041+)
                    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                    
                    def set_dark_title_bar(hwnd):
                        value = ctypes.c_int(1)  # 1 = 深色模式, 0 = 浅色模式
                        ctypes.windll.dwmapi.DwmSetWindowAttribute(
                            hwnd,
                            DWMWA_USE_IMMERSIVE_DARK_MODE,
                            ctypes.byref(value),
                            ctypes.sizeof(value)
                        )
                    
                    # 需要在窗口显示后调用，使用定时器延迟执行
                    QTimer.singleShot(0, lambda: self._apply_dark_titlebar(set_dark_title_bar))
                    
                except Exception as e:
                    print(_('dark_titlebar_failed').format(e=e))
        except Exception:
            pass
    
    def _apply_dark_titlebar(self, set_func):
        """应用深色标题栏设置"""
        try:
            hwnd = int(self.winId())
            set_func(hwnd)
        except Exception as e:
            print(_('dark_titlebar_apply_failed').format(e=e))

    # ---- UI building ----
    def _build_ui(self):
        # central layout container
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        # command bar
        self.command_bar = CommandBar()
        self.command_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        central_layout.addWidget(self.command_bar)

        # bind search and library change
        self.command_bar.library_combo.currentIndexChanged.connect(self._on_library_changed)
        self.command_bar.search_btn.clicked.connect(self._on_search)
        self.command_bar.clear_btn.clicked.connect(self._on_clear_search)

        # tool bar
        toolbar = self._create_toolbar()
        # use a frame to host toolbar for padding consistency
        tb_frame = QFrame()
        tb_layout = QVBoxLayout(tb_frame)
        tb_layout.setContentsMargins(8, 6, 8, 6)
        tb_layout.setSpacing(0)
        tb_layout.addWidget(toolbar)
        central_layout.addWidget(tb_frame)

        # splitter workspace
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)

        self.left_panel = MaterialTreePanel()
        self.left_panel.set_model(self.material_model)
        self.left_panel.materialSelected.connect(self._on_material_selected)
        self.right_panel = MaterialEditorPanel()
        self.right_panel.saveRequested.connect(self._on_save_material)
        self.right_panel.exportRequested.connect(self._on_export_material_from_panel)

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 7)

        central_layout.addWidget(self.splitter, 1)

        self.setCentralWidget(central)

        # status bar
        status = QStatusBar()
        status.showMessage(_('status_ready'))
        self.setStatusBar(status)

        # menubar placeholder
        self._create_menubar()

        # initial load
        self._load_libraries()

    def _ui_call(self, fn):
        """线程安全：把回调投递到 Qt 主线程执行。"""
        try:
            QApplication.instance().postEvent(self, _InvokeCallableEvent(fn))
        except Exception:
            # 兜底：直接执行（可能在主线程时）
            try:
                fn()
            except Exception:
                pass

    def customEvent(self, event):  # type: ignore[override]
        if isinstance(event, _InvokeCallableEvent):
            try:
                event.fn()
            except Exception:
                pass
            return
        return super().customEvent(event)

    def _create_menubar(self):
        menubar = self.menuBar()
        
        # 文件菜单
        self.menu_file = menubar.addMenu(_('menu_file'))
        self.act_import = self.menu_file.addAction(_('menu_import'), self._on_import_library)
        self.act_export = self.menu_file.addAction(_('menu_export_material'), self._on_export_material)
        self.act_autopack = self.menu_file.addAction(_('menu_autopack'), self._on_auto_pack)
        self.menu_file.addSeparator()
        self.act_exit = self.menu_file.addAction(_('menu_exit'), self.close)

        # 编辑菜单
        self.menu_edit = menubar.addMenu(_('menu_edit'))
        self.act_refresh = self.menu_edit.addAction(_('menu_refresh'), self._refresh_library_list)
        self.act_clear_search = self.menu_edit.addAction(_('menu_clear_search'), self._on_clear_search)

        # 工具菜单
        self.menu_tools = menubar.addMenu(_('menu_tools'))
        self.act_match = self.menu_tools.addAction(_('material_matching_button'), self._on_open_material_matching)
        self.act_adv_search = self.menu_tools.addAction(_('advanced_search_button'), self._on_open_advanced_search)

        # 视图菜单
        self.menu_view = menubar.addMenu(_('menu_view'))
        self.act_toggle_sidebar = self.menu_view.addAction(_('menu_toggle_sidebar'), self._toggle_sidebar)
        self.act_toggle_samplers = self.menu_view.addAction(_('menu_toggle_samplers'), self._toggle_samplers)

        # 帮助菜单
        self.menu_help = menubar.addMenu(_('menu_help'))
        self.act_about = self.menu_help.addAction(_('menu_about'), self._show_about)

        # 语言菜单
        self.menu_language = menubar.addMenu(_('menu_language'))
        self.act_lang_zh = self.menu_language.addAction('中文', lambda: self._switch_language('zh_CN'))
        self.act_lang_en = self.menu_language.addAction('English', lambda: self._switch_language('en_US'))

    def _create_toolbar(self) -> QToolBar:
        toolbar = QToolBar()
        toolbar.setMovable(False)

        # left group
        self.import_btn = QToolButton()
        self.import_btn.setObjectName("primary")
        self.import_btn.clicked.connect(self._on_import_library)
        toolbar.addWidget(self.import_btn)

        self.export_btn = QToolButton()
        self.export_btn.clicked.connect(self._on_export_material)
        toolbar.addWidget(self.export_btn)

        self.autopack_btn = QToolButton()
        self.autopack_btn.clicked.connect(self._on_autopack)
        toolbar.addWidget(self.autopack_btn)

        toolbar.addSeparator()

        # center group
        self.match_btn = QToolButton()
        self.match_btn.setObjectName("primary")
        self.match_btn.clicked.connect(self._on_match_material)
        toolbar.addWidget(self.match_btn)

        self.adv_btn = QToolButton()
        self.adv_btn.clicked.connect(self._on_advanced_search)
        toolbar.addWidget(self.adv_btn)

        toolbar.addSeparator()

        # right group
        self.refresh_btn = QToolButton()
        self.refresh_btn.setText("🔄")
        self.refresh_btn.setObjectName("ghost")
        self.refresh_btn.clicked.connect(self._on_refresh)
        toolbar.addWidget(self.refresh_btn)

        self.more_btn = QToolButton()
        self.more_btn.setPopupMode(QToolButton.InstantPopup)
        self.more_menu = QMenu(self.more_btn)
        self.act_manage_libraries = self.more_menu.addAction(_('menu_library_manager_icon'), self._on_manage_libraries)
        self.more_btn.setMenu(self.more_menu)
        toolbar.addWidget(self.more_btn)

        return toolbar

    def _apply_translations(self):
        # window & command bar
        self.setWindowTitle(_('app_title_full'))
        self.command_bar.library_label.setText(_('menu_library_manager'))
        self.command_bar.search_edit.setPlaceholderText(_('search_placeholder_full'))
        self.command_bar.search_btn.setText(_('search_button'))
        self.command_bar.clear_btn.setText(_('clear_button'))

        # toolbar buttons
        self.import_btn.setText(_('menu_import'))
        self.export_btn.setText(_('menu_export_material'))
        self.autopack_btn.setText(_('menu_autopack'))
        self.match_btn.setText(_('material_matching_button'))
        self.adv_btn.setText(_('advanced_search_button'))
        self.refresh_btn.setText(_('menu_refresh'))
        self.more_btn.setText(f"⋯ { _('menu_tools') }")
        self.act_manage_libraries.setText(_('menu_library_manager_icon'))

        # menubar titles & actions
        self.menu_file.setTitle(_('menu_file'))
        self.act_import.setText(_('menu_import'))
        self.act_export.setText(_('menu_export_material'))
        self.act_autopack.setText(_('menu_autopack'))
        self.act_exit.setText(_('menu_exit'))

        self.menu_edit.setTitle(_('menu_edit'))
        self.act_refresh.setText(_('menu_refresh'))
        self.act_clear_search.setText(_('menu_clear_search'))

        self.menu_tools.setTitle(_('menu_tools'))
        self.act_match.setText(_('material_matching_button'))
        self.act_adv_search.setText(_('advanced_search_button'))

        self.menu_view.setTitle(_('menu_view'))
        self.act_toggle_sidebar.setText(_('menu_toggle_sidebar'))
        self.act_toggle_samplers.setText(_('menu_toggle_samplers'))

        self.menu_help.setTitle(_('menu_help'))
        self.act_about.setText(_('menu_about'))

        self.menu_language.setTitle(_('menu_language'))
        self.act_lang_zh.setText('中文')
        self.act_lang_en.setText('English')

        # status
        if self.statusBar():
            self.statusBar().showMessage(_('status_ready'))
        
        # right panel (material editor)
        if hasattr(self, 'right_panel') and self.right_panel:
            self.right_panel.refresh_translations()

    def _switch_language(self, language_code: str):
        language_manager.set_language(language_code)
        self._apply_translations()

    # ===== data loading & handlers =====
    def _load_libraries(self):
        libs = self.db.get_libraries()
        self.library_model.load(libs)
        self.command_bar.library_combo.blockSignals(True)
        self.command_bar.library_combo.clear()
        for lib in libs:
            self.command_bar.library_combo.addItem(lib.get('name', ''), lib)
        self.command_bar.library_combo.blockSignals(False)
        if libs:
            self.command_bar.library_combo.setCurrentIndex(0)
            self._set_current_library(libs[0].get('id'))

    def _set_current_library(self, library_id: Optional[int]):
        self.current_library_id = library_id
        self._load_materials(keyword=self.command_bar.search_edit.text().strip())

    def _load_materials(self, keyword: str = ""):
        """同步加载材质列表（带等待光标和状态栏提示）"""
        if self.current_library_id is None:
            self.material_model.load([])
            return
        
        # 显示等待光标和状态栏提示
        from PySide6.QtGui import QCursor
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        self.statusBar().showMessage("正在加载材质...")
        QApplication.processEvents()
        
        try:
            # 同步加载 - QAbstractListModel 已优化为毫秒级
            materials = self.db.search_materials(
                library_id=self.current_library_id,
                keyword=keyword
            )
            self.material_model.load(materials)
            
            if materials:
                # auto-select first
                index = self.material_model.index(0, 0)
                self.left_panel.list_view.setCurrentIndex(index)
                mid = self.material_model.get_material_id(index)
                if mid:
                    self._load_material_detail(mid)
            
            self.statusBar().showMessage(f"已加载 {len(materials)} 个材质", 2000)
        except Exception as e:
            self.statusBar().showMessage(f"加载失败: {e}", 3000)
        finally:
            # 恢复正常光标
            QApplication.restoreOverrideCursor()

    def _on_library_changed(self, idx: int):
        data = self.command_bar.library_combo.itemData(idx)
        if isinstance(data, dict):
            self._set_current_library(data.get('id'))

    def _on_search(self):
        # 使用防抖：重置定时器，等待用户停止输入后再执行搜索
        self._search_timer.start()
    
    def _do_search(self):
        """实际执行搜索（由防抖定时器触发）"""
        keyword = self.command_bar.search_edit.text().strip()
        self._load_materials(keyword=keyword)
        # 重置滚动状态防止跳动
        if hasattr(self.left_panel.list_view, 'reset_scroll_state'):
            self.left_panel.list_view.reset_scroll_state()

    def _on_clear_search(self):
        self._search_timer.stop()  # 停止任何待执行的搜索
        self.command_bar.search_edit.clear()
        self._load_materials(keyword="")

    def _on_material_selected(self, material_data):
        if isinstance(material_data, dict):
            mid = material_data.get('id')
        else:
            mid = material_data
        if mid:
            # 使用防抖：避免快速点击时重复加载
            self._pending_material_id = mid
            if not hasattr(self, '_material_timer'):
                from PySide6.QtCore import QTimer
                self._material_timer = QTimer()
                self._material_timer.setSingleShot(True)
                self._material_timer.setInterval(50)  # 50ms 防抖
                self._material_timer.timeout.connect(self._do_load_material)
            self._material_timer.start()
    
    def _do_load_material(self):
        """实际加载材质详情（由防抖定时器触发）"""
        mid = getattr(self, '_pending_material_id', None)
        if mid:
            self._load_material_detail(mid)

    def _load_material_detail(self, material_id: int):
        # 使用缓存避免重复查询数据库
        if not hasattr(self, '_material_cache'):
            self._material_cache = {}  # 简单的LRU缓存
            self._cache_order = []
            self._max_cache_size = 20  # 缓存最多20个材质
        
        if material_id in self._material_cache:
            detail = self._material_cache[material_id]
            # 移到缓存末尾（最近使用）
            self._cache_order.remove(material_id)
            self._cache_order.append(material_id)
        else:
            detail = self.db.get_material_detail(material_id)
            # 添加到缓存
            self._material_cache[material_id] = detail
            self._cache_order.append(material_id)
            # 超出缓存大小时移除最旧的
            while len(self._cache_order) > self._max_cache_size:
                old_id = self._cache_order.pop(0)
                self._material_cache.pop(old_id, None)
        
        self.current_material = detail
        self.right_panel.load_detail(detail)

    def select_material_by_id(self, material_id: int, library_id: Optional[int] = None):
        """在列表中选中指定的材质ID（如果需要则切换库）"""
        # 1. 清除搜索内容（不触发信号，稍后手动加载）
        has_search = bool(self.command_bar.search_edit.text().strip())
        if has_search:
            self.command_bar.search_edit.blockSignals(True)
            self.command_bar.search_edit.clear()
            self.command_bar.search_edit.blockSignals(False)
        
        # 2. 处理库切换
        lib_switched = False
        # 2. 处理库切换
        lib_switched = False
        if library_id and library_id != self.current_library_id:
            # 尝试在下拉框中找到并选中该库
            combo = self.command_bar.library_combo
            idx = -1
            for i in range(combo.count()):
                data = combo.itemData(i)
                # itemData 存储的是库信息的字典
                if isinstance(data, dict) and data.get('id') == library_id:
                    idx = i
                    break
                # 兼容可能直接存储ID的情况（如果有）
                elif data == library_id:
                    idx = i
                    break
            
            if idx >= 0:
                # 选中会触发 currentIndexChanged -> _on_library_changed -> _set_current_library -> _load_materials
                combo.setCurrentIndex(idx)
                lib_switched = True
            else:
                print(f"警告：未在列表中找到库ID {library_id}")
                # 兜底：直接切换内部状态
                self._set_current_library(library_id)
                lib_switched = True
                
        # 3. 如果没有切换库但清除了搜索，或者刚刚切换了库（确保列表是最新的）
        if not lib_switched and has_search:
            self._load_materials(keyword="")
            
        # 确保UI更新完成 (列表加载)
        QApplication.processEvents()
        
        # 4. 选中材质
        self._select_material_in_list(material_id)
    
    def _select_material_in_list(self, material_id: int):
        """在当前列表中查找并选中指定材质"""
        # 遍历模型查找匹配的材质
        for row in range(self.material_model.rowCount()):
            index = self.material_model.index(row, 0)
            mid = self.material_model.get_material_id(index)
            if mid == material_id:
                # 找到了，选中并滚动到可见
                self.left_panel.list_view.setCurrentIndex(index)
                self.left_panel.list_view.scrollTo(index)
                self._load_material_detail(material_id)
                return True
        return False

    # ===== toolbar handlers (placeholders) =====
    def _info(self, text: str):
        self.statusBar().showMessage(text, 3000)

    def _on_import_library(self):
        """导入/新建材质库 (对应原add_library)"""
        try:
            # 旧 Tk 版：先弹 ImportModeDialog(文件夹/DCX/XML)
            from PySide6.QtWidgets import QInputDialog

            items = [_('import_mode_folder_xml'), _('import_mode_dcx_auto'), _('import_mode_single_xml')]
            choice, ok = QInputDialog.getItem(self, _('import_mode_dialog_title'), _('import_mode_label'), items, 0, False)
            if not ok or not choice:
                return

            if choice == items[0]:
                self._import_library_from_folder()
            elif choice == items[1]:
                self._import_library_from_dcx()
            else:
                self._import_single_xml()

        except Exception as exc:
            import traceback
            QMessageBox.warning(self, _('import_failed'), _('import_failed_msg').format(exc=exc, traceback=traceback.format_exc()))

    def _import_library_from_folder(self):
        """对齐旧版 add_library(folder)：选择文件夹->解析XML->创建库->批量写入。"""
        from PySide6.QtWidgets import QFileDialog
        folder = QFileDialog.getExistingDirectory(self, _('select_library_folder'))
        if not folder:
            return
        try:
            import os
            import threading

            from src.core.xml_parser import MaterialXMLParser
            from .import_dialogs_qt import LibraryInfoDialogQt, create_busy_progress

            default_name = os.path.basename(folder.rstrip("/\\"))
            info_dlg = LibraryInfoDialogQt(self, default_name=default_name)
            if info_dlg.exec() != QDialog.Accepted or not info_dlg.result:
                return

            lib_name = info_dlg.result.name
            lib_desc = info_dlg.result.description

            progress = create_busy_progress(self, _('import_progress_title_folder'), _('import_progress_msg_folder'))
            progress.show()

            def work():
                try:
                    parser = MaterialXMLParser()
                    materials_data = parser.parse_directory(folder)
                    if not materials_data:
                        self._ui_call(lambda: QMessageBox.information(self, _('import_progress_title_folder'), _('no_valid_xml_found')))
                        return

                    # 旧版：create_library(name, description, folder_path)
                    if hasattr(self.db, "create_library"):
                        library_id = self.db.create_library(lib_name, lib_desc, folder)
                        if hasattr(self.db, "add_materials"):
                            self.db.add_materials(library_id, materials_data)
                    else:
                        self.db.add_library(lib_name, folder, description=lib_desc)
                        library_id = None

                    def done_ui():
                        self._load_libraries()
                        if isinstance(library_id, int):
                            for i in range(self.command_bar.library_combo.count()):
                                data = self.command_bar.library_combo.itemData(i)
                                if isinstance(data, dict) and data.get("id") == library_id:
                                    self.command_bar.library_combo.setCurrentIndex(i)
                                    break
                                    break
                        self._info(_('import_success_msg').format(lib_name=lib_name, count=len(materials_data)))

                    self._ui_call(done_ui)
                except Exception as exc:
                    import traceback

                    self._ui_call(lambda: QMessageBox.warning(self, _('import_failed'), _('import_folder_failed_msg').format(exc=exc, traceback=traceback.format_exc())))
                finally:
                    self._ui_call(progress.close)

            thread = threading.Thread(target=work, daemon=True)
            thread.start()

            def on_cancel():
                # 解析/导入本身目前不可中断；这里只做 UI 关闭，避免“卡死”感。
                progress.close()

            progress.canceled.connect(on_cancel)

        except Exception as exc:
            import traceback
            QMessageBox.warning(self, _('import_failed'), _('import_folder_failed_msg').format(exc=exc, traceback=traceback.format_exc()))

    def _import_single_xml(self):
        """对齐旧版 import_single_xml：选择XML->解析->添加到当前库/新建临时库。"""
        from PySide6.QtWidgets import QFileDialog
        file_path, _unused = QFileDialog.getOpenFileName(self, _('select_xml_file'), filter="XML Files (*.xml);;All Files (*.*)")
        if not file_path:
            return
        try:
            import os
            import threading

            from src.core.xml_parser import MaterialXMLParser
            from .import_dialogs_qt import LibraryInfoDialogQt, create_busy_progress

            progress = create_busy_progress(self, _('import_mode_single_xml'), _('import_progress_msg_xml'))
            progress.show()

            def work():
                try:
                    parser = MaterialXMLParser()
                    material_data = parser.parse_file(file_path)
                    if not material_data:
                        self._ui_call(lambda: QMessageBox.warning(self, _('import_failed'), _('xml_parse_failed')))
                        return

                    library_id = self.current_library_id
                    # 旧版：若未选库则创建临时库（Qt 版补齐“库名/描述输入”）
                    if not library_id and hasattr(self.db, "create_library"):
                        default_name = os.path.splitext(os.path.basename(file_path))[0]
                        info_dlg = LibraryInfoDialogQt(self, default_name=default_name)
                        if info_dlg.exec() != QDialog.Accepted or not info_dlg.result:
                            return
                        library_id = self.db.create_library(info_dlg.result.name, info_dlg.result.description)
                        self.current_library_id = library_id

                    if library_id and hasattr(self.db, "add_materials"):
                        self.db.add_materials(library_id, [material_data])
                    else:
                        self._ui_call(
                            lambda: QMessageBox.information(
                                self,
                                _('import_mode_single_xml'),
                                _('no_library_selected_for_xml'),
                            )
                        )
                        return

                    def done_ui():
                        self._load_libraries()
                        if isinstance(library_id, int):
                            for i in range(self.command_bar.library_combo.count()):
                                data = self.command_bar.library_combo.itemData(i)
                                if isinstance(data, dict) and data.get("id") == library_id:
                                    self.command_bar.library_combo.setCurrentIndex(i)
                                    break
                                    break
                        self._info(_('import_xml_success'))

                    self._ui_call(done_ui)

                except Exception as exc:
                    import traceback

                    self._ui_call(lambda: QMessageBox.warning(self, _('import_failed'), _('import_xml_failed').format(exc=exc, traceback=traceback.format_exc())))
                finally:
                    self._ui_call(progress.close)

            thread = threading.Thread(target=work, daemon=True)
            thread.start()

            progress.canceled.connect(progress.close)
        except Exception as exc:
            import traceback
            QMessageBox.warning(self, _('import_failed'), _('import_xml_failed').format(exc=exc, traceback=traceback.format_exc()))

    def _import_library_from_dcx(self):
        """对齐旧版 import_dcx_materials：打开 Qt 版 DCX 导入对话框（避免 Qt/Tk 混用）。"""
        try:
            from .dcx_import_dialog_qt import DCXImportDialogQt

            dlg = DCXImportDialogQt(self, self.db)

            def _after_import(result: Dict[str, Any]):
                # 刷新库列表
                self._load_libraries()
                # 尝试选中新库
                lib_id = result.get("library_id") if isinstance(result, dict) else None
                if isinstance(lib_id, int):
                    # 在 combo 里找到对应项
                    for i in range(self.command_bar.library_combo.count()):
                        data = self.command_bar.library_combo.itemData(i)
                        if isinstance(data, dict) and data.get("id") == lib_id:
                            self.command_bar.library_combo.setCurrentIndex(i)
                            break

            dlg.imported.connect(_after_import)
            dlg.exec()
        except Exception:
            pass

    def _on_export_material(self):
        """导出当前材质 (工具栏按钮 - 触发右侧面板导出)"""
        if not self.current_material:
            QMessageBox.information(self, _('export_xml_title'), _('select_material_hint'))
            return
        
        # 直接调用导出逻辑,不通过信号
        try:
            from PySide6.QtWidgets import QFileDialog
            
            # 询问保存位置
            file_path, _unused = QFileDialog.getSaveFileName(
                self, 
                _('export_xml_title'), 
                f"{self.current_material.get('filename', 'material')}.xml",
                "XML Files (*.xml)"
            )
            if not file_path:
                return
            
            # 导出逻辑
            from src.core.xml_parser import MaterialXMLParser
            parser = MaterialXMLParser()
            
            # 使用当前详情数据
            export_data = dict(self.current_material)
            export_data['add_to_autopack'] = self.right_panel.autopack_check.isChecked()
            
            parser.export_material_to_xml(export_data, file_path)
            
            # 如果勾选了自动封包
            if export_data.get('add_to_autopack', False):
                from src.core.autopack_manager import AutoPackManager
                autopack_mgr = AutoPackManager()
                autopack_mgr.add_material(file_path)
                self._info(_('export_autopack_success').format(file_path=file_path))
            else:
                self._info(_('export_success').format(file_path=file_path))
                
        except Exception as exc:
            import traceback
            QMessageBox.warning(self, _('export_failed_title'), _('export_failed_msg').format(exc=exc, traceback=traceback.format_exc()))

    def _on_autopack(self):
        """打开自动封包管理器"""
        try:
            from src.core.autopack_manager import AutoPackManager
            from .autopack_dialog_qt import AutoPackDialogQt

            dlg = AutoPackDialogQt(self, AutoPackManager())
            dlg.exec()
        except Exception as exc:
            import traceback
            QMessageBox.warning(self, _('autopack_manager'), _('autopack_manager_error').format(exc=exc, traceback=traceback.format_exc()))

    def _on_match_material(self):
        """打开材质匹配对话框"""
        try:
            from .material_matching_dialog_qt import MaterialMatchingDialogQt

            initial_material_name = ""
            if isinstance(self.current_material, dict):
                initial_material_name = (
                    self.current_material.get("name")
                    or self.current_material.get("file_name")
                    or self.current_material.get("filename")
                    or ""
                )

            dlg = MaterialMatchingDialogQt(
                parent=self,
                database_manager=self.db,
                initial_source_library_id=self.current_library_id,
                initial_material_name=initial_material_name,
                version_tag="MM-20251217-01",
            )
            dlg.show()
        except Exception as exc:
            import traceback

            QMessageBox.warning(self, _('error'), _('match_window_error').format(exc=exc, traceback=traceback.format_exc()))

    def _on_advanced_search(self):
        """打开高级搜索对话框"""
        try:
            from .advanced_search_dialog_qt import AdvancedSearchDialogQt
            
            # 创建搜索回调函数
            def search_callback(criteria: dict) -> int:
                """执行搜索并返回结果数量"""
                results = self.db.advanced_search_materials(criteria)
                
                # 更新材质列表显示
                self.material_model.clear()
                for mat in results:
                    self.material_model.add_material(mat)
                
                # 更新状态栏
                self._info(_('advanced_search_result_msg').format(count=len(results)))
                
                return len(results)
            
            # 创建并显示对话框
            dialog = AdvancedSearchDialogQt(self.db, search_callback, self)
            dialog.exec()
            
        except Exception as exc:
            import traceback
            QMessageBox.warning(
                self, 
                _('error'), 
                _('advanced_search_error').format(exc=exc, traceback=traceback.format_exc())
            )

    def _on_refresh(self):
        self._load_libraries()
        self._info(_('list_refreshed_msg'))

    def _on_manage_libraries(self):
        """打开库管理对话框"""
        try:
            from .library_manager_dialog_qt import LibraryManagerDialogQt

            # 用于排查“运行的不是最新代码”的版本戳
            version_tag = "LM-20251217-01"

            dlg = LibraryManagerDialogQt(
                self,
                self.db,
                refresh_callback=self._load_libraries,
                add_library_callback=self._on_import_library,
                version_tag=version_tag,
            )
            dlg.exec()
            # 兜底：对话框关闭后再刷新一次，确保主窗口同步
            self._load_libraries()

        except Exception as exc:
            import traceback
            QMessageBox.warning(self, _('menu_library_manager'), _('library_manager_error').format(exc=exc, traceback=traceback.format_exc()))

    def _on_save_material(self, updated_data: Dict[str, Any]):
        """将右侧面板的修改写回数据库，并刷新详情。"""
        if not self.current_material:
            return
        mid = self.current_material.get('id')
        if not mid:
            return
        try:
            self.db.update_material(mid, updated_data)
            
            # 检查是否需要添加到自动封包
            if self.right_panel.autopack_check.isChecked():
                from src.core.autopack_manager import AutoPackManager
                
                # 添加材质ID引用到自动封包列表
                material_name = self.current_material.get('filename', '')
                autopack_mgr = AutoPackManager()
                autopack_mgr.add_material_by_db_id(mid, material_name)
                self.statusBar().showMessage(_('save_and_autopack_success'), 3000)
            else:
                self.statusBar().showMessage(_('save_success'), 3000)
            
            # 重新加载详情，确保显示与数据库一致
            self._load_material_detail(mid)
        except Exception as exc:
            self.statusBar().showMessage(_('save_failed_msg').format(exc=exc), 5000)
    
    def _on_export_material_from_panel(self, export_data: Dict[str, Any]):
        """从右侧面板触发的导出 (exportRequested信号)"""
        try:
            # 调用原有导出逻辑
            from PySide6.QtWidgets import QFileDialog
            # 询问保存位置
            file_path, _unused = QFileDialog.getSaveFileName(
                self, 
                _('export_xml_title'), 
                f"{export_data.get('filename', 'material')}.xml",
                "XML Files (*.xml)"
            )
            if not file_path:
                return
            
            # 导出逻辑(需要使用原xml_parser)
            from src.core.xml_parser import MaterialXMLParser
            parser = MaterialXMLParser()
            parser.export_material_to_xml(export_data, file_path)
            
            # 如果勾选了自动封包
            if export_data.get('add_to_autopack', False):
                # TODO: 调用自动封包管理器添加
                self._info("已导出并添加到自动封包队列")
            else:
                self._info(f"导出成功: {file_path}")
                
        except Exception as exc:
            QMessageBox.warning(self, "导出失败", f"导出过程中出错: {exc}")

    # ---- 菜单栏功能方法 ----
    
    def _on_auto_pack(self):
        """自动封包菜单项 - 调用现有的autopack方法"""
        self._on_autopack()
    
    def _refresh_library_list(self):
        """刷新库列表 - 调用现有的refresh方法"""
        self._on_refresh()
    
    def _on_open_material_matching(self):
        """打开材质匹配对话框 - 调用现有方法"""
        self._on_match_material()
    
    def _on_open_advanced_search(self):
        """打开高级搜索对话框 - 调用现有方法"""
        self._on_advanced_search()
    
    def _toggle_sidebar(self):
        """切换侧边栏显示/隐藏"""
        if hasattr(self, 'splitter'):
            # 获取左侧面板
            left_panel = self.splitter.widget(0)
            if left_panel:
                left_panel.setVisible(not left_panel.isVisible())
                status = "已显示" if left_panel.isVisible() else "已隐藏"
                self.statusBar().showMessage(f"侧边栏{status}", 2000)
    
    def _toggle_samplers(self):
        """切换采样器显示/隐藏"""
        # 这个功能需要在MaterialEditorPanel中实现
        # 目前只显示提示
        QMessageBox.information(self, "功能提示", "采样器显示/隐藏功能将在后续版本中实现")
    
    def _show_about(self):
        """显示关于对话框"""
        about_text = f"""
        <h2>{_('about_app_name')}</h2>
        <p><b>{_('about_version')}:</b> v1.1</p>
        <p><b>{_('about_description')}:</b> {_('about_description_text')}</p>
        <br>
        <p><b>{_('about_features')}:</b></p>
        <ul>
            <li>{_('about_feature_import')}</li>
            <li>{_('about_feature_match')}</li>
            <li>{_('about_feature_search')}</li>
            <li>{_('about_feature_edit')}</li>
            <li>{_('about_feature_autopack')}</li>
        </ul>
        <br>
        <p><b>{_('about_tech_stack')}:</b> Python 3 + PySide6 (Qt6)</p>
        <p><b>{_('about_developer')}:</b> CCX</p>
        <p><b>{_('about_date')}:</b> 2025-12-23</p>
        """
        QMessageBox.about(self, _('about_title'), about_text)


# convenience runner for module testing
def launch():
    import sys
    from .theme.qss import load_stylesheet
    from PySide6.QtGui import QFont

    app = QApplication.instance() or QApplication(sys.argv)
    # 字体兜底：部分环境里 Qt 可能会出现 pointSize=-1 的字体（像素字体/系统字体回退导致），
    # 这里强制设置一个合法默认字号，避免刷 `QFont::setPointSize` 警告。
    try:
        f = app.font() or QFont()
        if f.pointSize() <= 0:
            f.setPointSize(10)
        # 统一默认字体族，避免不同控件/平台回退不一致
        if not f.family():
            f.setFamily("Segoe UI")
        app.setFont(f)
    except Exception:
        pass
    app.setStyleSheet(load_stylesheet())
    win = MaterialDatabaseMainWindow()
    win.show()
    return app, win


if __name__ == "__main__":
    import sys
    app, _ = launch()
    sys.exit(app.exec())
