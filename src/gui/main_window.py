#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口 - 3D材质库查询程序主界面
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
from typing import Optional
import logging

# 添加src目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.database import MaterialDatabase
from src.core.xml_parser import MaterialXMLParser
from src.core.i18n import language_manager, _
from src.gui.library_panel import LibraryPanel
from src.gui.material_list_panel import MaterialListPanel

logger = logging.getLogger(__name__)
from src.gui.material_panel import MaterialPanel
from src.gui.sampler_panel import SamplerPanel
from src.gui.library_manager_dialog import LibraryManagerDialog
from src.gui.theme import ModernDarkTheme

class MaterialDatabaseApp:
    """3D材质库查询程序主应用"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.lang_manager = language_manager
        self.root.title(_("app_title") + " " + _("version"))
        self.root.geometry("1400x900")
        self.root.minsize(1000, 600)
        
        # 初始化组件
        self.database = MaterialDatabase()
        self.xml_parser = MaterialXMLParser()
        
        # 当前选中的材质
        self.current_material = None
        self.current_library_id = None
        
        # 材质数据缓存（LRU缓存，最多缓存100个材质）
        self.material_cache = {}
        self.cache_size = 100
        self.cache_order = []  # 用于LRU淘汰策略
        
        # 高级搜索对话框引用
        self.advanced_search_dialog = None
        
        # 自动封包管理器
        from ..core.autopack_manager import AutoPackManager
        self.autopack_manager = AutoPackManager()
        
        # 设置样式
        self._setup_style()
        
        # 创建界面
        self._create_menu()
        self._create_main_layout()
        
        # 初始化面板
        self._init_panels()
        
        # 加载数据
        self._refresh_libraries()
        
        # 确保所有界面文本都是最新的翻译
        self.root.after(100, self._update_interface_text)
    
    def _setup_style(self):
        """设置界面样式"""
        # 应用现代黑暗主题
        ModernDarkTheme.apply_theme(self.root)
    
    def _create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=_("menu_file"), menu=file_menu)
        file_menu.add_command(label=_("menu_add_library"), command=self.add_library)
        file_menu.add_separator()
        file_menu.add_command(label=_("menu_import_xml"), command=self.import_single_xml)
        file_menu.add_command(label=_("menu_import_dcx"), command=self.import_dcx_materials)
        file_menu.add_separator()
        file_menu.add_command(label=_("menu_export_material"), command=self.export_current_material)
        file_menu.add_separator()
        file_menu.add_command(label=_("menu_autopack"), command=self.show_autopack_manager)
        file_menu.add_separator()
        file_menu.add_command(label=_("menu_exit"), command=self.root.quit)
        
        # 编辑菜单
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=_("menu_edit"), menu=edit_menu)
        edit_menu.add_command(label=_("menu_refresh"), command=self._refresh_libraries)
        edit_menu.add_command(label=_("menu_clear_search"), command=self.clear_search)
        
        # 语言菜单
        lang_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=_("menu_language"), menu=lang_menu)
        
        # 添加语言选项
        available_langs = self.lang_manager.get_available_languages()
        for lang_code, lang_name in available_langs.items():
            lang_menu.add_command(
                label=lang_name, 
                command=lambda lc=lang_code: self.change_language(lc)
            )
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=_("menu_help"), menu=help_menu)
        help_menu.add_command(label=_("menu_about"), command=self.show_about)
    
    def _create_main_layout(self):
        """创建主布局"""
        # 主容器
        main_container = ttk.Frame(self.root)
        # 把主容器放入根窗口，否则所有子控件不会显示
        main_container.pack(fill=tk.BOTH, expand=True)
        self.status_text = tk.StringVar(value=_('status_ready'))
        
        # 顶部工具栏
        self._create_toolbar(main_container)
        
        # 顶部库选择区域
        library_frame = ttk.Frame(main_container)
        library_frame.pack(fill=tk.X, pady=(10, 5))
        
        self.library_label = ttk.Label(library_frame, text=_("library_label"))
        self.library_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.library_combo = ttk.Combobox(library_frame, width=30, state="readonly")
        self.library_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.library_combo.bind('<<ComboboxSelected>>', self._on_library_combo_select)
        
        # 导入库按钮（解析DCX）- 淡黄色
        self.import_library_btn = ttk.Button(library_frame, text=_("import_library_button"), style='LightYellow.TButton',
                  command=self.import_dcx_materials)
        self.import_library_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 自动封包按钮 - 橙色
        self.autopack_btn = ttk.Button(library_frame, text=_("autopack_manager"), style='Orange.TButton',
                  command=self.show_autopack_manager)
        self.autopack_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.library_manager_btn = ttk.Button(library_frame, text=_("library_manager_button"), style='Primary.TButton',
                  command=self._show_library_manager)
        self.library_manager_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        # 主内容区域 - 垂直分割（上下布局）
        main_paned = ttk.PanedWindow(main_container, orient=tk.VERTICAL)
        main_paned.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # 上部区域 - 水平分割（材质列表和材质信息）
        top_paned = ttk.PanedWindow(main_paned, orient=tk.HORIZONTAL)
        main_paned.add(top_paned, weight=3)
        
        # 左侧材质列表
        left_frame = ttk.Frame(top_paned, width=300)
        top_paned.add(left_frame, weight=1)
        
        # 右侧材质信息面板
        right_frame = ttk.Frame(top_paned)
        top_paned.add(right_frame, weight=2)
        
        # 底部采样器面板
        bottom_frame = ttk.Frame(main_paned, height=200)
        main_paned.add(bottom_frame, weight=1)
        
        # 保存框架引用
        self.left_frame = left_frame
        self.right_frame = right_frame
        self.bottom_frame = bottom_frame
        
        # 状态栏
        self._create_statusbar(main_container)
    
    def _create_toolbar(self, parent):
        """创建工具栏"""
        toolbar_frame = ttk.Frame(parent)
        toolbar_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 左侧按钮组
        left_buttons = ttk.Frame(toolbar_frame)
        left_buttons.pack(side=tk.LEFT)
        
        self.add_library_btn = ttk.Button(left_buttons, text=_("add_library_button"), style='Success.TButton',
                  command=self.add_library)
        self.add_library_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.refresh_btn = ttk.Button(left_buttons, text=_("menu_refresh"), style='Primary.TButton',
                  command=self._refresh_libraries)
        self.refresh_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 右侧搜索组
        search_frame = ttk.Frame(toolbar_frame)
        search_frame.pack(side=tk.RIGHT)
        
        self.search_label = ttk.Label(search_frame, text=_("search_button") + ":")
        self.search_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._on_search_change)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        self.search_btn = ttk.Button(search_frame, text=_("search_button"), style='Primary.TButton',
                  command=self.perform_search)
        self.search_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.advanced_search_btn = ttk.Button(search_frame, text=_("advanced_search_button"), style='Info.TButton',
                  command=self.show_advanced_search)
        self.advanced_search_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.clear_btn = ttk.Button(search_frame, text=_("clear_button"), style='Danger.TButton',
                  command=self.clear_search)
        self.clear_btn.pack(side=tk.LEFT)
    
    def _create_statusbar(self, parent):
        """创建状态栏"""
        self.statusbar = ttk.Frame(parent)
        self.statusbar.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))
        
        self.status_text = tk.StringVar(value=_('status_ready'))
        ttk.Label(self.statusbar, textvariable=self.status_text).pack(side=tk.LEFT)
        
        # 右侧统计信息
        self.stats_text = tk.StringVar(value="")
        ttk.Label(self.statusbar, textvariable=self.stats_text).pack(side=tk.RIGHT)
    
    def _init_panels(self):
        """初始化各个面板"""
        # 材质列表面板（简化版）
        self.material_list_panel = MaterialListPanel(
            self.left_frame,
            self.database,
            on_material_select=self._on_material_select
        )
        
        # 材质信息面板
        self.material_panel = MaterialPanel(
            self.right_frame,
            on_material_save=self._on_material_save,
            on_material_export=self.export_current_material
        )
        
        # 样例面板（移到底部）
        self.sampler_panel = SamplerPanel(self.bottom_frame)
        
    def _on_library_combo_select(self, event=None):
        """库下拉框选择事件"""
        selection = self.library_combo.current()
        if selection >= 0 and selection < len(self.libraries):
            library = self.libraries[selection]
            self.current_library_id = library['id']
            
            # 加载材质列表
            self.material_list_panel.load_materials(library['id'])
            
            # 清空右侧面板
            self.material_panel.clear()
            self.sampler_panel.clear()
            
            self.status_text.set(_('status_bar_selected_library').format(name=library['name']))
    
    def _show_library_manager(self):
        """显示库管理对话框"""
        LibraryManagerDialog(self.root, self.database, self._refresh_libraries)
    
    def _refresh_libraries(self):
        """刷新材质库列表"""
        try:
            self.libraries = self.database.get_libraries()
            
            # 更新下拉框
            library_names = [f"{lib['name']} (ID:{lib['id']})" for lib in self.libraries]
            self.library_combo['values'] = library_names
            
            if self.libraries:
                self.library_combo.current(0)
                self._on_library_combo_select()
            else:
                self.library_combo.set("")
                self.current_library_id = None
            
            self._update_statistics()
            self.status_text.set(_('library_list_refreshed'))
        except Exception as e:
            messagebox.showerror(_('error'), f"{_('refresh_failed')}：{str(e)}")
    
    def _update_statistics(self):
        """更新统计信息"""
        try:
            stats = self.database.get_statistics()
            stats_text = _('library_material_stats').format(
                libraries=stats.get('total_libraries', 0),
                materials=stats.get('total_materials', 0)
            )
            self.stats_text.set(stats_text)
        except Exception as e:
            self.stats_text.set(_('error'))
    
    def _on_library_select(self, library_id: int):
        """库选择事件处理"""
        self.current_library_id = library_id
        self.current_material = None
        
        # 清空右侧面板
        self.material_panel.clear()
        self.sampler_panel.clear()
        # 使用本地化文本显示当前库（显示 ID 以便保持信息）
        self.status_text.set(_('status_bar_selected_library').format(name=f"ID:{library_id}"))
    
    def _on_material_select(self, material_id: int):
        """材质选择事件处理（带缓存优化）"""
        try:
            import time
            start_time = time.time()
            
            print(f"[主窗口调试] 选中材质ID: {material_id}")
            
            # 检查缓存
            material_data = None
            if material_id in self.material_cache:
                material_data = self.material_cache[material_id]
                print(f"[缓存命中] 从缓存加载材质 ID: {material_id}")
                
                # 更新LRU顺序
                self.cache_order.remove(material_id)
                self.cache_order.append(material_id)
            else:
                # 从数据库加载
                material_data = self.database.get_material_detail(material_id)
                print(f"[数据库查询] 从数据库加载材质 ID: {material_id}")
                
                # 添加到缓存
                if material_data:
                    self._add_to_cache(material_id, material_data)
            
            print(f"[主窗口调试] 从数据库获取的材质数据: {material_data is not None}")
            
            if material_data:
                print(f"[主窗口调试] 材质名: {material_data.get('filename', '未知')}")
                print(f"[主窗口调试] 参数数量: {len(material_data.get('params', []))}")
                print(f"[主窗口调试] 采样器数量: {len(material_data.get('samplers', []))}")
                
                self.current_material = material_data
                
                # 更新面板显示
                self.material_panel.load_material(material_data)
                self.sampler_panel.load_samplers(material_data.get('samplers', []))
                
                elapsed_ms = (time.time() - start_time) * 1000
                print(f"[性能] 材质加载总耗时: {elapsed_ms:.2f}ms")
                
                self.status_text.set(_('loaded_material_status').format(
                    filename=material_data.get('filename', _('unknown_material'))
                ))
            else:
                print(f"[主窗口调试] 无法获取材质详细信息")
                messagebox.showerror(_('error'), _('load_material_failed'))
        except Exception as e:
            print(f"[主窗口调试] 材质选择异常: {e}")
            messagebox.showerror(_('error'), f"{_('load_failed')}：{str(e)}")
    
    def _add_to_cache(self, material_id: int, material_data: dict):
        """添加材质到缓存（LRU策略）"""
        # 如果缓存已满，移除最久未使用的项
        if len(self.material_cache) >= self.cache_size:
            if self.cache_order:
                oldest_id = self.cache_order.pop(0)
                if oldest_id in self.material_cache:
                    del self.material_cache[oldest_id]
                    print(f"[缓存淘汰] 移除材质 ID: {oldest_id}")
        
        # 添加到缓存
        self.material_cache[material_id] = material_data
        self.cache_order.append(material_id)
        print(f"[缓存添加] 缓存材质 ID: {material_id}, 当前缓存大小: {len(self.material_cache)}")
    
    def _clear_cache(self):
        """清除缓存（在导入/删除材质时调用）"""
        self.material_cache.clear()
        self.cache_order.clear()
        print("[缓存清除] 已清空材质缓存")
    
    def _on_library_manage(self, action: str, library_id: int = None):
        """库管理事件处理"""
        if action == "delete" and library_id:
            if messagebox.askyesno(_('confirm_delete_library'), _('confirm_delete_library_message')):
                try:
                    self.database.delete_library(library_id)
                    self._clear_cache()  # 清除缓存
                    self._refresh_libraries()
                    # 使用本地化提示
                    self.status_text.set(_('library_deleted'))
                except Exception as e:
                    messagebox.showerror(_('error'), f"{_('delete_library_failed')}：{str(e)}")
    
    def _on_material_save(self, material_data: dict):
        """材质保存事件处理"""
        if self.current_material and 'id' in self.current_material:
            try:
                material_id = self.current_material['id']
                self.database.update_material(material_id, material_data)
                # 使用就绪状态或本地化的完成提示
                self.status_text.set(_('status_ready'))
                
                # 刷新当前材质数据并更新缓存
                updated_material = self.database.get_material_detail(material_id)
                if updated_material:
                    self.current_material = updated_material
                    # 更新缓存中的数据
                    if material_id in self.material_cache:
                        self.material_cache[material_id] = updated_material
                        print(f"[缓存更新] 已更新材质缓存 ID: {material_id}")
                    
            except Exception as e:
                messagebox.showerror(_('error'), f"{_('save_material_failed')}：{str(e)}")
    
    def _on_search_change(self, *args):
        """搜索框变化事件"""
        # 可以在这里实现实时搜索
        pass
    
    def add_library(self):
        """添加新的材质库 - 支持多种导入模式"""
        # 导入导入模式选择对话框
        from .import_mode_dialog import ImportModeDialog
        
        # 显示导入模式选择对话框
        mode_dialog = ImportModeDialog(self.root)
        if not mode_dialog.result:
            return
        
        import_mode = mode_dialog.result
        
        if import_mode == "folder":
            self._add_library_from_folder()
        elif import_mode == "dcx":
            self.import_dcx_materials()
        elif import_mode == "xml":
            self.import_single_xml()
    
    def _add_library_from_folder(self):
        """从文件夹添加材质库"""
        folder_path = filedialog.askdirectory(title=_('choose_library_folder'))
        if not folder_path:
            return
        
        # 获取库名称和描述
        dialog = LibraryInfoDialog(self.root, os.path.basename(folder_path))
        if not dialog.result:
            return
        
        name, description = dialog.result
        
        try:
            # 显示进度对话框
            progress_dialog = ProgressDialog(self.root, _('parsing_materials'))

            def parse_and_import():
                try:
                    # 解析XML文件
                    materials_data = self.xml_parser.parse_directory(folder_path)

                    if not materials_data:
                        messagebox.showwarning(_('warning'), _('no_valid_materials_in_folder'))
                        return

                    # 创建材质库
                    library_id = self.database.create_library(name, description, folder_path)

                    # 批量添加材质
                    self.database.add_materials(library_id, materials_data)

                    # 刷新界面
                    self.root.after(0, self._refresh_libraries)
                    self.root.after(0, lambda: self.status_text.set(_('import_success_multiple').format(count=len(materials_data))))

                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror(_('error'), f"{_('import_failed')}：{str(e)}"))
                finally:
                    progress_dialog.close()

            # 在后台线程中执行解析
            import threading
            thread = threading.Thread(target=parse_and_import, daemon=True)
            thread.start()

        except Exception as e:
            messagebox.showerror(_('error'), f"{_('add_library_failed')}：{str(e)}")
    
    def import_single_xml(self):
        """导入单个XML文件"""
        file_path = filedialog.askopenfilename(
            title=_('menu_import_xml'),
            filetypes=[(_('xml_files'), "*.xml"), (_('all_files'), "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # 解析XML文件
            material_data = self.xml_parser.parse_file(file_path)
            if not material_data:
                messagebox.showerror(_('error'), _('xml_parse_failed'))
                return
            
            # 如果没有选中库，创建临时库
            if not self.current_library_id:
                # 使用通用的“新建”前缀加编号作为临时库名
                lib_name = f"{_('new')}_{len(self.database.get_libraries()) + 1}"
                library_id = self.database.create_library(
                    lib_name,
                    ''
                )
                self.current_library_id = library_id
            
            # 添加到当前库
            self.database.add_materials(self.current_library_id, [material_data])
            
            # 清除缓存（因为添加了新材质）
            self._clear_cache()
            
            self._refresh_libraries()
            self.status_text.set(_('import_single_success').format(count=1))
            
        except Exception as e:
            messagebox.showerror(_('error'), f"{_('import_xml_failed')}：{str(e)}")
    
    def import_dcx_materials(self):
        """导入DCX材质库"""
        try:
            from .autopack_dialogs import DCXImportDialog
            
            def on_import_complete(result):
                if result['success']:
                    # 清除缓存（因为导入了新材质）
                    self._clear_cache()
                    
                    # 刷新材质库列表
                    if hasattr(self, 'library_panel'):
                        self.library_panel.refresh_libraries()
                    
                    # 选中新导入的库
                    if result['library_id'] and hasattr(self, 'library_panel'):
                        self.library_panel.select_library(result['library_id'])
            
            DCXImportDialog(self.root, self.database, on_import_complete)
            
        except Exception as e:
            messagebox.showerror(_('error'), _('import_dcx_failed', error=str(e)))
    
    def show_autopack_manager(self):
        """显示自动封包管理器"""
        try:
            from .autopack_dialogs import AutoPackDialog
            
            def on_pack_complete(result):
                if result['success']:
                    self.status_text.set(_('autopack_complete_status', success=result['packed_count'], failed=result['failed_count']))
            
            AutoPackDialog(self.root, self.autopack_manager, on_pack_complete)
            
        except Exception as e:
            messagebox.showerror(_('error'), _('open_autopack_failed', error=str(e)))
    
    def export_current_material(self, add_to_autopack=None):
        """导出当前材质
        
        Args:
            add_to_autopack: 是否添加到自动封包列表，None表示询问用户，True/False直接执行
        """
        if not self.current_material:
            messagebox.showwarning(_('warning'), _('select_material_to_export'))
            return
        
        # 获取保存路径
        file_path = filedialog.asksaveasfilename(
            title=_('save'),
            defaultextension=".xml",
            filetypes=[(_('xml_files'), "*.xml"), (_('all_files'), "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # 获取当前编辑的材质数据
            current_data = self.material_panel.get_material_data()
            
            # 导出XML
            if self.xml_parser.export_material_to_xml(current_data, file_path):
                self.status_text.set(_('export_complete').format(filename=os.path.basename(file_path)))
                
                # 根据参数决定是否添加到自动封包列表
                should_add_to_autopack = add_to_autopack
                if should_add_to_autopack is None:
                    # 如果没有指定，询问用户
                    should_add_to_autopack = messagebox.askyesno(_('autopack_title'), _('ask_add_to_autopack'))
                
                if should_add_to_autopack:
                    try:
                        # 查找原始.matbin文件路径（如果有的话）
                        original_matbin = None
                        if self.current_material.get('file_path'):
                            base_name = os.path.splitext(self.current_material['file_path'])[0]
                            original_matbin = f"{base_name}.matbin"
                        
                        # 添加到自动封包列表
                        matbin_file = self.autopack_manager.add_to_autopack(file_path, original_matbin)
                        messagebox.showinfo(_('success'), _('added_to_autopack', filename=os.path.basename(matbin_file)))
                        
                    except Exception as e:
                        messagebox.showerror(_('error'), _('add_to_autopack_failed', error=str(e)))
                else:
                    messagebox.showinfo(_('success'), _('material_exported').format(path=file_path))
            else:
                messagebox.showerror(_('error'), _('export_material_failed'))
                
        except Exception as e:
            messagebox.showerror(_('error'), f"{_('export_failed')}：{str(e)}")
    
    def perform_search(self):
        """执行搜索"""
        keyword = self.search_var.get().strip()
        if keyword and hasattr(self, 'material_list_panel'):
            self.material_list_panel.search_materials(keyword)
            self.status_text.set(_('status_searching').format(keyword=keyword))
        else:
            self.clear_search()
    
    def clear_search(self):
        """清空搜索"""
        self.search_var.set("")
        if hasattr(self, 'material_list_panel') and self.current_library_id:
            self.material_list_panel.load_materials(self.current_library_id)
        self.status_text.set(_('search_cleared'))
    
    def show_advanced_search(self):
        """显示高级搜索对话框"""
        # 使用单例模式，确保只有一个高级搜索窗口
        if hasattr(self, 'advanced_search_dialog') and self.advanced_search_dialog:
            # 如果窗口已存在，将其置于前台
            try:
                self.advanced_search_dialog.dialog.lift()
                self.advanced_search_dialog.dialog.focus_force()
                return
            except tk.TclError:
                # 窗口已被销毁，清除引用
                self.advanced_search_dialog = None
        
        # 创建新的高级搜索窗口
        self.advanced_search_dialog = AdvancedSearchDialog(
            self.root, self.database, self.perform_advanced_search, 
            on_close=self._on_advanced_search_close
        )
    
    def perform_advanced_search(self, search_criteria):
        """执行高级搜索"""
        try:
            # 转换搜索条件格式以匹配数据库方法的期望
            converted_criteria = self._convert_search_criteria(search_criteria)
            
            # 执行搜索
            results = self.database.advanced_search_materials(converted_criteria)
            
            # 显示搜索结果
            if hasattr(self, 'material_list_panel'):
                self.material_list_panel.show_search_results(results)
            
            # 更新状态栏
            count = len(results) if results else 0
            self.status_text.set(_('advanced_search_results').format(count=count))
            
            # 返回搜索结果数量供高级搜索对话框使用
            return count
            
        except Exception as e:
            messagebox.showerror(_('error'), f"{_('search_failed')}：{str(e)}")
            return None
    
    def _convert_search_criteria(self, criteria):
        """转换搜索条件格式"""
        logger.debug(f"[转换前调试] 原始条件数据: {criteria}")
        
        # 获取匹配模式：'and' = 完全匹配（所有条件都满足），'or' = 模糊匹配（任一条件满足）
        match_mode = criteria.get('match_mode', 'or')
        
        converted = {
            'match_mode': 'all' if match_mode == 'and' else 'any',
            'fuzzy_search': True,  # 所有搜索都使用LIKE进行包含匹配
            'conditions': []
        }
        
        # 如果有当前选中的库，添加库筛选
        if hasattr(self, 'current_library_id') and self.current_library_id:
            converted['library_id'] = self.current_library_id
        
        # 直接传递搜索条件，不再按类别分组
        for condition in criteria.get('conditions', []):
            search_condition = {
                'type': condition['type'],
                'content': condition['content']
            }
            
            # 添加采样器搜索的子类型信息
            if condition['type'] == 'sampler':
                if condition.get('sampler_type'):
                    search_condition['sampler_type'] = condition['sampler_type']
                if condition.get('sampler_path'):
                    search_condition['sampler_path'] = condition['sampler_path']
                if condition.get('specific_search'):
                    search_condition['specific_search'] = condition['specific_search']
                if condition.get('sampler_details'):
                    search_condition['sampler_details'] = condition['sampler_details']
            
            # 添加参数搜索的范围信息
            if condition['type'] == 'parameter' and condition.get('range'):
                search_condition['range'] = condition['range']
            
            # 添加参数搜索的值信息
            if condition['type'] == 'parameter' and condition.get('param_value'):
                search_condition['param_value'] = condition['param_value']
            
            converted['conditions'].append(search_condition)
        
        logger.debug(f"[转换后调试] 转换后条件数据: {converted}")
        return converted
    
    def _on_advanced_search_close(self):
        """高级搜索窗口关闭时的清理"""
        self.advanced_search_dialog = None
    
    def show_about(self):
        """显示关于对话框"""
        about_text = """
3D材质库查询程序 v1.0

功能特性：
• 批量解析XML材质配置文件
• 多材质库管理
• 智能搜索和过滤
• 材质参数编辑
• XML导出功能

技术栈：
• Python 3.8+
• Tkinter GUI
• SQLite数据库

开发：GitHub Copilot
        """
        # 使用 i18n 中的 about_text 或直接显示内联 about_text
        try:
            # 如果 i18n 中包含关于文本，则使用其翻译，否则使用内联文本
            translated = _('about_text')
            if translated and translated != 'about_text':
                messagebox.showinfo(_('menu_about'), translated)
            else:
                messagebox.showinfo(_('menu_about'), about_text)
        except Exception:
            messagebox.showinfo(_('menu_about'), about_text)
    
    def change_language(self, language_code: str):
        """切换语言"""
        try:
            # 设置语言并更新所有界面文本
            self.lang_manager.set_language(language_code)
            self._update_interface_text()
            # 显示切换完成提示（使用本地化文本）
            try:
                lang_name = self.lang_manager.get_language_name(language_code)
            except Exception:
                lang_name = language_code
            messagebox.showinfo(_('info'), _('language_changed').format(name=lang_name))
        except Exception as e:
            messagebox.showerror(_("error"), f"{_('change_language_failed')}: {str(e)}")
    
    def _update_interface_text(self):
        """更新界面文本"""
        try:
            # 更新窗口标题
            self.root.title(_("app_title") + " " + _("version"))
            
            # 更新菜单栏（重新创建）
            self._create_menu()
            
            # 更新工具栏按钮文本
            self._update_toolbar_text()
            
            # 更新状态栏
            self._update_statusbar_text()
            
            # 更新各个面板的标题
            self._update_panel_titles()
            
            # 更新库选择标签
            self._update_library_selection_text()
            
        except Exception as e:
            print(f"Error updating interface text: {e}")
    
    def _update_toolbar_text(self):
        """更新工具栏按钮文本"""
        if hasattr(self, 'add_library_btn'):
            self.add_library_btn.configure(text=_("add_library_button"))
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.configure(text=_("menu_refresh"))
        if hasattr(self, 'import_library_btn'):
            self.import_library_btn.configure(text=_("import_library_button"))
        if hasattr(self, 'autopack_btn'):
            self.autopack_btn.configure(text=_("autopack_manager"))
        if hasattr(self, 'library_manager_btn'):
            self.library_manager_btn.configure(text=_("library_manager_button"))
        if hasattr(self, 'search_label'):
            self.search_label.configure(text=_("search_button") + ":")
        if hasattr(self, 'search_btn'):
            self.search_btn.configure(text=_("search_button"))
        if hasattr(self, 'advanced_search_btn'):
            self.advanced_search_btn.configure(text=_("advanced_search_button"))
        if hasattr(self, 'clear_btn'):
            self.clear_btn.configure(text=_("clear_button"))
    
    def _update_statusbar_text(self):
        """更新状态栏文本"""
        if hasattr(self, 'status_text'):
            current_status = self.status_text.get()
            # 如果当前状态是默认的"就绪"状态，则更新为翻译后的文本
            if current_status == "就绪" or current_status == "Ready" or current_status == "準備完了" or current_status == "준비":
                self.status_text.set(_("status_ready"))
        
        # 更新统计信息
        if hasattr(self, 'stats_text'):
            self._update_statistics()
    
    def _update_panel_titles(self):
        """更新面板标题"""
        # 更新库面板
        if hasattr(self, 'library_panel') and hasattr(self.library_panel, 'update_language'):
            self.library_panel.update_language()
            
        # 更新材质列表面板
        if hasattr(self, 'material_list_panel') and hasattr(self.material_list_panel, 'update_language'):
            self.material_list_panel.update_language()
        
        # 更新材质信息面板
        if hasattr(self, 'material_panel') and hasattr(self.material_panel, 'update_language'):
            self.material_panel.update_language()
        
        # 更新样例面板
        if hasattr(self, 'sampler_panel') and hasattr(self.sampler_panel, 'update_language'):
            self.sampler_panel.update_language()
    
    def _update_library_selection_text(self):
        """更新库选择区域文本"""
        if hasattr(self, 'library_label'):
            self.library_label.configure(text=_("library_label"))
        if hasattr(self, 'library_manager_btn'):
            self.library_manager_btn.configure(text=_("library_manager_button"))
    
    def cleanup(self):
        """清理资源"""
        try:
            if hasattr(self, 'database'):
                self.database.close()
        except:
            pass


class LibraryInfoDialog:
    """材质库信息输入对话框"""
    
    def __init__(self, parent, default_name: str = ""):
        self.result = None
        
        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(_("add_library_dialog"))
        self.dialog.geometry("400x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        # 创建界面
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 名称输入
        self.name_label = ttk.Label(main_frame, text=_('library_name_label'))
        self.name_label.pack(anchor=tk.W, pady=(0, 5))
        self.name_var = tk.StringVar(value=default_name)
        name_entry = ttk.Entry(main_frame, textvariable=self.name_var, width=40)
        name_entry.pack(fill=tk.X, pady=(0, 10))
        name_entry.focus()
        
        # 描述输入
        self.desc_label = ttk.Label(main_frame, text=_('description_optional'))
        self.desc_label.pack(anchor=tk.W, pady=(0, 5))
        self.desc_var = tk.StringVar()
        desc_entry = ttk.Entry(main_frame, textvariable=self.desc_var, width=40)
        desc_entry.pack(fill=tk.X, pady=(0, 20))
        
        # 按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        self.ok_btn = ttk.Button(button_frame, text=_('ok_button'), command=self._on_ok)
        self.ok_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        self.cancel_btn = ttk.Button(button_frame, text=_('cancel_button'), command=self._on_cancel)
        self.cancel_btn.pack(side=tk.RIGHT)
        
        # 绑定回车键
        self.dialog.bind('<Return>', lambda e: self._on_ok())
        self.dialog.bind('<Escape>', lambda e: self._on_cancel())
        
        # 等待用户操作
        self.dialog.wait_window()
    
    def _on_ok(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror(_('error'), _('please_enter_library_name'))
            return
        
        self.result = (name, self.desc_var.get().strip())
        self.dialog.destroy()
    
    def _on_cancel(self):
        self.dialog.destroy()


class ProgressDialog:
    """进度对话框"""
    
    def __init__(self, parent, message: str):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(_('processing'))
        self.dialog.geometry("300x100")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)
        
        # 居中显示
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 100, parent.winfo_rooty() + 100))
        
        # 消息和进度条
        ttk.Label(self.dialog, text=message).pack(pady=20)
        
        self.progress = ttk.Progressbar(self.dialog, mode='indeterminate')
        self.progress.pack(padx=20, pady=(0, 20), fill=tk.X)
        self.progress.start()
        
        # 禁用关闭按钮
        self.dialog.protocol("WM_DELETE_WINDOW", lambda: None)
    
    def close(self):
        """关闭对话框"""
        try:
            self.dialog.destroy()
        except:
            pass


class AdvancedSearchDialog:
    """高级搜索对话框"""
    
    def __init__(self, parent, database, on_search_callback, on_close=None):
        self.parent = parent
        self.database = database
        self.on_search_callback = on_search_callback
        self.on_close = on_close
        
        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(_('advanced_search_title'))
        self.dialog.geometry("800x750")
        self.dialog.minsize(750, 600)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(True, True)
        
        # 居中显示
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        # 绑定关闭事件
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_window_close)
        
        # 搜索条件列表
        self.search_conditions = []
        
        # 搜索状态
        self.last_search_results_count = 0
        
        self._create_ui()
    
    def _create_ui(self):
        """创建界面"""
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 标题
        title_label = ttk.Label(main_frame, text=_('advanced_search_title'), 
                               font=('TkDefaultFont', 12, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # 搜索条件区域
        conditions_frame = ttk.LabelFrame(main_frame, text=_('search_conditions'), padding=10)
        conditions_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 创建滚动框架
        self.canvas = tk.Canvas(conditions_frame, highlightthickness=0, bg='#2b2b2b')
        self.scrollbar = ttk.Scrollbar(conditions_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # 配置滚动区域
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self._configure_scroll_region()
        )
        
        # 创建窗口并配置canvas
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # 绑定canvas大小变化事件
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        
        # 布局canvas和滚动条
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # 搜索条件列表
        self.conditions_list_frame = ttk.Frame(self.scrollable_frame)
        self.conditions_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 绑定鼠标滚轮事件
        self._bind_mousewheel()
        
        # 搜索模式区域
        mode_frame = ttk.LabelFrame(main_frame, text=_('search_mode'), padding=10)
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.search_mode_var = tk.StringVar(value="and")
        ttk.Radiobutton(mode_frame, text=_('exact_match'), variable=self.search_mode_var, 
                       value="and").pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text=_('fuzzy_match'), variable=self.search_mode_var, 
                       value="or").pack(anchor=tk.W)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 左侧按钮组
        left_button_frame = ttk.Frame(button_frame)
        left_button_frame.pack(side=tk.LEFT)
        
        ttk.Button(left_button_frame, text=_('add_condition'), 
                  command=self._add_condition).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(left_button_frame, text=_('clear_all'), 
                  command=self._clear_all).pack(side=tk.LEFT, padx=(0, 5))
        
        # 右侧按钮组
        right_button_frame = ttk.Frame(button_frame)
        right_button_frame.pack(side=tk.RIGHT)
        
        ttk.Button(right_button_frame, text=_('search_button'), 
                  command=self._execute_search, style='Primary.TButton').pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(right_button_frame, text=_('cancel'), 
                  command=self._cancel).pack(side=tk.RIGHT)
        
        # 状态显示区域
        status_frame = ttk.LabelFrame(main_frame, text=_('search_status'), padding=10)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = ttk.Label(status_frame, text=_('ready_to_search'), 
                                     font=('TkDefaultFont', 9))
        self.status_label.pack(anchor=tk.W)
        
        # 添加第一个搜索条件
        self._add_condition()
    
    def _add_condition(self):
        """添加搜索条件"""
        # 主条件框架
        condition_main_frame = ttk.LabelFrame(self.conditions_list_frame, 
                                             text=f"{_('search_condition')} {len(self.search_conditions) + 1}", 
                                             padding=12)
        condition_main_frame.pack(fill=tk.X, pady=8, padx=5)
        
        # 第一行：搜索类型和内容
        first_row = ttk.Frame(condition_main_frame)
        first_row.pack(fill=tk.X, pady=(0, 5))
        
        # 搜索类型
        type_label = ttk.Label(first_row, text=_('search_type') + ":")
        type_label.pack(side=tk.LEFT, padx=(0, 5))
        
        type_var = tk.StringVar()
        type_combo = ttk.Combobox(first_row, textvariable=type_var, width=18, state="readonly")
        type_combo['values'] = [
            _('material_name'),
            _('shader_search'),
            _('sampler_search'),
            _('parameter_search')
        ]
        type_combo.current(0)
        type_combo.pack(side=tk.LEFT, padx=(0, 15))
        
        # 搜索内容
        content_label = ttk.Label(first_row, text=_('search_content') + ":")
        content_label.pack(side=tk.LEFT, padx=(0, 5))
        
        content_var = tk.StringVar()
        content_entry = ttk.Entry(first_row, textvariable=content_var, width=30)
        content_entry.pack(side=tk.LEFT, padx=(0, 15), fill=tk.X, expand=True)
        
        # 删除按钮
        delete_btn = ttk.Button(first_row, text=_('delete'), 
                               command=lambda: self._delete_condition(condition_main_frame))
        delete_btn.pack(side=tk.RIGHT)
        
        # 第二行：高级选项（采样器类型、数值范围等）
        second_row = ttk.Frame(condition_main_frame)
        
        # 采样器搜索子选项
        sampler_frame = ttk.Frame(second_row)
        
        # 指定搜索选择框
        sampler_mode_frame = ttk.Frame(sampler_frame)
        sampler_mode_frame.pack(fill=tk.X, pady=(0, 5))
        
        sampler_specific_var = tk.BooleanVar()
        sampler_specific_checkbox = ttk.Checkbutton(sampler_mode_frame, 
                                                   text=_('specific_search'), 
                                                   variable=sampler_specific_var,
                                                   command=lambda: self._toggle_sampler_mode(condition_data))
        sampler_specific_checkbox.pack(side=tk.LEFT)
        
        # 采样器类型输入
        sampler_type_frame = ttk.Frame(sampler_frame)
        sampler_type_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(sampler_type_frame, text=_('sampler_type') + ":").pack(side=tk.LEFT, padx=(0, 5))
        sampler_type_var = tk.StringVar()
        sampler_type_entry = ttk.Entry(sampler_type_frame, textvariable=sampler_type_var, width=25)
        sampler_type_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # 采样器路径输入
        sampler_path_frame = ttk.Frame(sampler_frame)
        sampler_path_frame.pack(fill=tk.X)
        
        ttk.Label(sampler_path_frame, text=_('sampler_path') + ":").pack(side=tk.LEFT, padx=(0, 5))
        sampler_path_var = tk.StringVar()
        sampler_path_entry = ttk.Entry(sampler_path_frame, textvariable=sampler_path_var, width=25)
        sampler_path_entry.pack(side=tk.LEFT)
        
        # 参数搜索子选项
        param_frame = ttk.Frame(second_row)
        
        # 参数值搜索
        param_value_frame = ttk.Frame(param_frame)
        param_value_frame.pack(fill=tk.X, pady=(0, 3))
        
        ttk.Label(param_value_frame, text=_('parameter_value') + ":").pack(side=tk.LEFT, padx=(0, 5))
        param_value_var = tk.StringVar()
        param_value_entry = ttk.Entry(param_value_frame, textvariable=param_value_var, width=25)
        param_value_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # 参数值帮助文本
        param_help_frame = ttk.Frame(param_frame)
        param_help_frame.pack(fill=tk.X, pady=(0, 5))
        
        help_label = ttk.Label(param_help_frame, text=_('parameter_value_help'), 
                              font=('TkDefaultFont', 8), foreground='gray')
        help_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # 数值范围
        range_frame = ttk.Frame(param_frame)
        range_frame.pack(fill=tk.X, pady=(0, 3))
        
        range_var = tk.BooleanVar()
        range_check = ttk.Checkbutton(range_frame, text=_('range_search'), variable=range_var,
                                     command=lambda: self._toggle_range_entries(condition_data))
        range_check.pack(side=tk.LEFT, padx=(0, 10))
        
        range_inputs_frame = ttk.Frame(range_frame)
        range_inputs_frame.pack(side=tk.LEFT)
        
        ttk.Label(range_inputs_frame, text=_('min_value') + ":").pack(side=tk.LEFT, padx=(0, 2))
        min_var = tk.StringVar()
        min_entry = ttk.Entry(range_inputs_frame, textvariable=min_var, width=10)
        min_entry.pack(side=tk.LEFT, padx=(0, 8))
        
        ttk.Label(range_inputs_frame, text=_('max_value') + ":").pack(side=tk.LEFT, padx=(0, 2))
        max_var = tk.StringVar()
        max_entry = ttk.Entry(range_inputs_frame, textvariable=max_var, width=10)
        max_entry.pack(side=tk.LEFT)
        
        # 范围搜索帮助文本
        range_help_frame = ttk.Frame(param_frame)
        range_help_frame.pack(fill=tk.X)
        
        range_help_label = ttk.Label(range_help_frame, text=_('range_search_help'), 
                                    font=('TkDefaultFont', 8), foreground='gray')
        range_help_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # 保存条件信息
        condition_data = {
            'frame': condition_main_frame,
            'type_var': type_var,
            'content_var': content_var,
            'content_entry': content_entry,
            'sampler_specific_var': sampler_specific_var,
            'sampler_type_var': sampler_type_var,
            'sampler_path_var': sampler_path_var,
            'sampler_type_entry': sampler_type_entry,
            'sampler_path_entry': sampler_path_entry,
            'param_value_var': param_value_var,
            'sampler_frame': sampler_frame,
            'param_frame': param_frame,
            'second_row': second_row,
            'range_var': range_var,
            'min_var': min_var,
            'max_var': max_var,
            'min_entry': min_entry,
            'max_entry': max_entry,
            'range_frame': range_frame,
            'range_inputs_frame': range_inputs_frame
        }
        
        self.search_conditions.append(condition_data)
        
        # 绑定类型变化事件
        type_combo.bind('<<ComboboxSelected>>', 
                       lambda e: self._on_type_change(condition_data))
        
        # 初始状态：禁用范围输入和采样器指定搜索
        min_entry.config(state='disabled')
        max_entry.config(state='disabled')
        sampler_type_entry.config(state='disabled')
        sampler_path_entry.config(state='disabled')
        
        # 初始化显示状态
        self._on_type_change(condition_data)
        
        # 更新滚动区域
        self._configure_scroll_region()

    def _configure_scroll_region(self):
        """配置滚动区域"""
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        """Canvas大小变化时的处理"""
        # 更新scrollable_frame的宽度以充满canvas
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)
    
    def _on_type_change(self, condition_data):
        """搜索类型变化事件"""
        search_type = condition_data['type_var'].get()
        
        # 隐藏所有高级选项
        condition_data['second_row'].pack_forget()
        condition_data['sampler_frame'].pack_forget()
        condition_data['param_frame'].pack_forget()
        
        # 根据类型显示相应选项
        if search_type == _('parameter_search'):
            condition_data['second_row'].pack(fill=tk.X, pady=(5, 0))
            condition_data['param_frame'].pack(side=tk.LEFT, fill=tk.X, expand=True)
        elif search_type == _('sampler_search'):
            condition_data['second_row'].pack(fill=tk.X, pady=(5, 0))
            condition_data['sampler_frame'].pack(side=tk.LEFT, fill=tk.X, expand=True)
            # 重置采样器指定搜索状态
            condition_data['sampler_specific_var'].set(False)
            self._toggle_sampler_mode(condition_data)
        
        # 更新滚动区域
        self._configure_scroll_region()
    
    def _toggle_sampler_mode(self, condition_data):
        """切换采样器搜索模式"""
        is_specific = condition_data['sampler_specific_var'].get()
        
        if is_specific:
            # 指定搜索模式：禁用搜索内容，启用类型和路径
            condition_data['content_entry'].config(state='disabled')
            condition_data['sampler_type_entry'].config(state='normal')
            condition_data['sampler_path_entry'].config(state='normal')
            # 清空搜索内容
            condition_data['content_var'].set('')
        else:
            # 常规搜索模式：启用搜索内容，禁用类型和路径
            condition_data['content_entry'].config(state='normal')
            condition_data['sampler_type_entry'].config(state='disabled')
            condition_data['sampler_path_entry'].config(state='disabled')
            # 清空类型和路径
            condition_data['sampler_type_var'].set('')
            condition_data['sampler_path_var'].set('')
    
    def _delete_condition(self, condition_frame):
        """删除搜索条件"""
        # 从列表中移除
        self.search_conditions = [c for c in self.search_conditions 
                                if c['frame'] != condition_frame]
        
        # 销毁界面
        condition_frame.destroy()
        
        # 更新滚动区域
        self._configure_scroll_region()
        
        # 如果没有条件了，添加一个新的
        if not self.search_conditions:
            self._add_condition()
    
    def _clear_all(self):
        """清空所有条件"""
        for condition in self.search_conditions:
            condition['frame'].destroy()
        self.search_conditions.clear()
        self._add_condition()
    
    def _execute_search(self):
        """执行搜索"""
        # 收集搜索条件
        criteria = {
            'conditions': [],
            'match_mode': self.search_mode_var.get()
        }
        
        for condition in self.search_conditions:
            search_type = condition['type_var'].get()
            content = condition['content_var'].get().strip()
            
            print(f"[界面调试] 检查条件 - 搜索类型: '{search_type}', 内容: '{content}'")
            print(f"[界面调试] 参数搜索类型文本: '{_('parameter_search')}'")
            print(f"[界面调试] 类型匹配: {search_type == _('parameter_search')}")
            
            # 基本条件检查：至少要有主要内容或特殊选项
            has_basic_content = bool(content)
            has_sampler_details = (search_type == _('sampler_search') and 
                                 (condition['sampler_type_var'].get().strip() or 
                                  condition['sampler_path_var'].get().strip()))
            has_param_details = (search_type == _('parameter_search') and
                               (condition['param_value_var'].get().strip() or
                                condition['range_var'].get()))
            
            print(f"[界面调试] 有效性检查 - 基础内容: {has_basic_content}, 采样器详情: {has_sampler_details}, 参数详情: {has_param_details}")
            
            if not (has_basic_content or has_sampler_details or has_param_details):
                continue
            
            condition_data = {
                'type': self._get_search_type_key(search_type),
                'content': content,
                'fuzzy': True  # 默认模糊搜索
            }
            
            # 如果是采样器搜索，添加类型和路径信息
            if search_type == _('sampler_search'):
                is_specific_search = condition['sampler_specific_var'].get()
                sampler_type = condition['sampler_type_var'].get().strip()
                sampler_path = condition['sampler_path_var'].get().strip()
                
                if is_specific_search:
                    # 指定搜索模式：直接使用类型和路径字段
                    condition_data['sampler_type'] = sampler_type
                    condition_data['sampler_path'] = sampler_path
                    condition_data['specific_search'] = True
                elif sampler_type or sampler_path:
                    # 兼容旧版本的详细搜索（如果有的话）
                    condition_data['sampler_details'] = {
                        'type': sampler_type if sampler_type else None,
                        'path': sampler_path if sampler_path else None
                    }
            
            # 如果是参数搜索，添加参数值和范围信息
            if search_type == _('parameter_search'):
                param_value = condition['param_value_var'].get().strip()
                print(f"[界面调试] 参数搜索 - 搜索类型: '{search_type}', 参数值: '{param_value}'")
                print(f"[界面调试] 参数值变量对象: {condition['param_value_var']}")
                print(f"[界面调试] 参数值是否为空: {not param_value}")
                if param_value:
                    condition_data['param_value'] = param_value
                    print(f"[界面调试] 参数值已添加到条件: {param_value}")
                else:
                    print(f"[界面调试] 参数值为空，未添加到条件")
                
                # 如果启用了范围搜索
                if condition['range_var'].get():
                    try:
                        min_val = float(condition['min_var'].get()) if condition['min_var'].get() else None
                        max_val = float(condition['max_var'].get()) if condition['max_var'].get() else None
                        if min_val is not None or max_val is not None:
                            condition_data['range'] = {'min': min_val, 'max': max_val}
                    except ValueError:
                        pass
            
            print(f"[界面调试] 最终条件数据: {condition_data}")
            criteria['conditions'].append(condition_data)
        
        if not criteria['conditions']:
            messagebox.showwarning(_('warning'), _('no_search_conditions'))
            return
        
        # 执行搜索但保持窗口打开
        try:
            # 更新按钮状态显示正在搜索
            self._update_search_status(_('searching'))
            
            # 执行搜索
            result_count = self.on_search_callback(criteria)
            
            # 更新搜索结果状态
            if result_count is not None:
                self.last_search_results_count = result_count
                self._update_search_status(_('search_completed').format(count=result_count))
            else:
                self._update_search_status(_('search_completed_unknown'))
                
        except Exception as e:
            self._update_search_status(_('search_failed'))
            messagebox.showerror(_('error'), f"{_('search_failed')}：{str(e)}")

    def _bind_mousewheel(self):
        """绑定鼠标滚轮事件"""
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # 绑定到canvas和所有子组件
        self.canvas.bind("<MouseWheel>", _on_mousewheel)
        self.dialog.bind("<MouseWheel>", _on_mousewheel)

    def _toggle_range_entries(self, condition_data):
        """切换范围输入框的状态"""
        if condition_data['range_var'].get():
            condition_data['min_entry'].config(state='normal')
            condition_data['max_entry'].config(state='normal')
        else:
            condition_data['min_entry'].config(state='disabled')
            condition_data['max_entry'].config(state='disabled')
            condition_data['min_var'].set('')
            condition_data['max_var'].set('')

    def _get_search_type_key(self, search_type_text):
        """将搜索类型文本转换为键值"""
        if search_type_text == _('material_name'):
            return 'material_name'
        elif search_type_text == _('shader_search'):
            return 'shader'
        elif search_type_text == _('sampler_search'):
            return 'sampler'
        elif search_type_text == _('parameter_search'):
            return 'parameter'
        return 'material_name'
    
    def _update_search_status(self, status_text):
        """更新搜索状态显示"""
        if hasattr(self, 'status_label'):
            self.status_label.config(text=status_text)
    
    def _on_window_close(self):
        """窗口关闭事件处理"""
        if self.on_close:
            self.on_close()
        self.dialog.destroy()
    
    def _cancel(self):
        """取消搜索"""
        self._on_window_close()