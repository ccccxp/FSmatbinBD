#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
库管理对话框 - 管理材质库的添加、删除和重新扫描
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from typing import Optional, Callable
from ..core.database import MaterialDatabase
from ..core.xml_parser import MaterialXMLParser
from ..core.i18n import _


class LibraryManagerDialog:
    """库管理对话框类"""
    
    def __init__(self, parent, database: MaterialDatabase, refresh_callback: Callable):
        """初始化库管理对话框"""
        self.database = database
        self.refresh_callback = refresh_callback
        
        # 创建模态对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(_('library_manager'))
        self.dialog.geometry("600x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 创建界面
        self._create_interface()
        
        # 加载库列表
        self._refresh_library_list()
        
        # 居中显示
        self._center_dialog()
    
    def _create_interface(self):
        """创建界面元素"""
        # 主框架
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 标题
        title_label = ttk.Label(main_frame, text=_('library_manager'), font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 10))

        # 库列表框架
        list_frame = ttk.LabelFrame(main_frame, text=_('imported_libraries'))
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 创建Treeview
        columns = ('name', 'path', 'count')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)

        # 设置列
        self.tree.heading('name', text=_('library_name'))
        self.tree.heading('path', text=_('library_path'))
        self.tree.heading('count', text=_('material_count_column'))

        self.tree.column('name', width=150)
        self.tree.column('path', width=300)
        self.tree.column('count', width=80)

        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # 打包
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5, padx=(0, 5))

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        self.button_frame = button_frame

        # 按钮（使用 i18n 文本）
        self.add_folder_btn = ttk.Button(button_frame, text=_('add_library'), command=self._add_library_with_mode_selection)
        self.add_folder_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.add_single_btn = ttk.Button(button_frame, text=_('add_library_dialog'), command=self._add_single_file)
        self.add_single_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.rescan_btn = ttk.Button(button_frame, text=_('refresh_library_list'), command=self._rescan_library)
        self.rescan_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.delete_btn = ttk.Button(button_frame, text=_('delete_library'), command=self._delete_library)
        self.delete_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.close_btn = ttk.Button(button_frame, text=_('close'), command=self._close)
        self.close_btn.pack(side=tk.RIGHT)
    
    def _refresh_library_list(self):
        """刷新库列表"""
        try:
            # 清空现有项目
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # 获取库列表
            libraries = self.database.get_libraries()
            
            for lib in libraries:
                try:
                    # 获取材质数量
                    count = self.database.get_material_count(lib['id'])

                    # 获取路径，优先使用source_path，回退到未设置文本
                    path = lib.get('source_path', '') or lib.get('path', '') or _('not_set')

                    self.tree.insert('', 'end', values=(
                        lib['name'],
                        path,
                        count
                    ), tags=(lib['id'],))
                except Exception as e:
                    print(f"处理库 {lib.get('name', 'Unknown')} 失败: {e}")
                    # 仍然插入记录，但显示错误信息
                    self.tree.insert('', 'end', values=(
                        lib.get('name', 'Unknown'),
                        _('error'),
                        '?'
                    ), tags=(lib['id'],))
        except Exception as e:
            print(f"刷新库列表失败: {e}")
            messagebox.showerror(_('error'), f"{_('refresh_library_list_failed')}: {str(e)}")
    
    def _add_library_with_mode_selection(self):
        """使用模式选择添加库"""
        try:
            from .import_mode_dialog import ImportModeDialog
            
            # 显示导入模式选择对话框
            dialog = ImportModeDialog(self.dialog)
            import_mode = dialog.get_selection()
            
            if import_mode == "folder":
                self._add_library_folder()
            elif import_mode == "dcx":
                self._add_library_dcx()
            elif import_mode == "xml":
                self._add_single_file()
                
        except Exception as e:
            messagebox.showerror(_('error'), _('import_mode_failed', error=str(e)))
    
    def _add_library_dcx(self):
        """添加DCX材质库"""
        try:
            from .autopack_dialogs import DCXImportDialog
            
            def on_import_complete():
                """导入完成回调"""
                self._refresh_library_list()
                self.refresh_callback()
            
            # 显示DCX导入对话框
            DCXImportDialog(self.dialog, self.database, on_import_complete)
        except Exception as e:
            messagebox.showerror(_('error'), _('import_dcx_failed', error=str(e)))
    
    def _add_library_folder(self):
        """添加材质库文件夹"""
        folder_path = filedialog.askdirectory(
            title=_('choose_library_folder'),
            initialdir=os.path.expanduser("~")
        )
        
        if folder_path:
            self._import_library(folder_path, is_folder=True)
    
    def _add_single_file(self):
        """添加单个材质文件"""
        file_path = filedialog.askopenfilename(
            title=_('choose_material_file') if 'choose_material_file' in globals() else _('open'),
            filetypes=[(_('xml_file_filter') if 'xml_file_filter' in globals() else 'XML files', "*.xml"), (_('all_files') if 'all_files' in globals() else 'All files', "*.*")],
            initialdir=os.path.expanduser("~")
        )
        
        if file_path:
            self._import_library(file_path, is_folder=False)
    
    def _import_library(self, path: str, is_folder: bool):
        """导入材质库"""
        try:
            parser = MaterialXMLParser()
            
            if is_folder:
                # 扫描文件夹
                xml_files = []
                for root, dirs, files in os.walk(path):
                    for file in files:
                        if file.lower().endswith('.xml'):
                            xml_files.append(os.path.join(root, file))
                
                if not xml_files:
                    messagebox.showwarning(_('warning'), _('no_xml_files_in_folder'))
                    return
                
                # 创建库记录
                library_name = os.path.basename(path)
                library_id = self.database.add_library(library_name, path)
                
                # 导入材质
                success_count = 0
                for xml_file in xml_files:
                    try:
                        materials = parser.parse_file(xml_file)
                        for material in materials:
                            self.database.add_material(material, library_id)
                        success_count += 1
                    except Exception as e:
                        print(f"导入文件 {xml_file} 失败: {e}")

                # 在导入完成后显示统计信息
                messagebox.showinfo(_('info'), _('imported_files_count').format(success=success_count, total=len(xml_files)))
            
            else:
                # 单个文件
                materials = parser.parse_file(path)
                
                if not materials:
                    messagebox.showwarning(_('warning'), _('no_material_data_in_file'))
                    return
                
                # 创建库记录
                library_name = os.path.splitext(os.path.basename(path))[0]
                library_id = self.database.add_library(library_name, os.path.dirname(path))
                
                # 导入材质
                for material in materials:
                    self.database.add_material(material, library_id)

                # 单文件导入成功提示
                messagebox.showinfo(_('info'), _('import_single_success').format(count=len(materials)))
            
            # 刷新列表
            self._refresh_library_list()
            
            # 回调父窗口刷新
            if self.refresh_callback:
                self.refresh_callback()
        
        except Exception as e:
            messagebox.showerror(_('error'), f"{_('import_failed')}: {e}")
    
    def _rescan_library(self):
        """重新扫描选中的库"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning(_('warning'), _('select_library_hint'))
            return
        
        item = selection[0]
        library_id = self.tree.item(item)['tags'][0]
        
        try:
            # 获取库信息
            library = self.database.get_library_by_id(library_id)
            if not library:
                messagebox.showerror(_('error'), _('library_not_found'))
                return
            
            # 删除库中的所有材质
            self.database.clear_library_materials(library_id)
            
            # 重新导入
            self._import_library(library['path'], is_folder=True)
        
        except Exception as e:
            messagebox.showerror(_('error'), f"{_('rescan_failed')}: {e}")
    
    def _delete_library(self):
        """删除选中的库"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning(_('warning'), _('select_library_hint'))
            return
        
        item = selection[0]
        library_name = self.tree.item(item)['values'][0]
        library_id = self.tree.item(item)['tags'][0]
        
        # 确认删除
        result = messagebox.askyesno(_('confirm'), _('confirm_delete_library_dialog').format(name=library_name))

        if result:
            try:
                self.database.delete_library(library_id)
                messagebox.showinfo(_('info'), _('library_deleted'))

                # 刷新列表
                self._refresh_library_list()

                # 回调父窗口刷新
                if self.refresh_callback:
                    self.refresh_callback()

            except Exception as e:
                messagebox.showerror(_('error'), f"{_('delete_failed')}: {e}")
    
    def _center_dialog(self):
        """居中显示对话框"""
        self.dialog.update_idletasks()
        
        # 获取对话框大小
        dialog_width = self.dialog.winfo_width()
        dialog_height = self.dialog.winfo_height()
        
        # 获取屏幕大小
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        
        # 计算居中位置
        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2
        
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    def _close(self):
        """关闭对话框"""
        self.dialog.destroy()
    
    def update_language(self):
        """更新界面语言"""
        try:
            # 更新对话框标题
            self.dialog.title(_('library_manager'))
            
            # 更新表格列标题
            self.tree.heading('name', text=_('library_name'))
            self.tree.heading('path', text=_('library_path'))
            self.tree.heading('count', text=_('material_count_column'))
            # 直接更新按钮文本（更可靠）
            try:
                self.add_folder_btn.config(text=_('add_library'))
                self.add_single_btn.config(text=_('add_library_dialog'))
                self.rescan_btn.config(text=_('refresh_library_list'))
                self.delete_btn.config(text=_('delete_library'))
                self.close_btn.config(text=_('close'))
            except Exception:
                # 如果某些按钮不存在（回退机制），遍历子组件更新常见键
                for widget in getattr(self, 'button_frame', tk.Frame()).winfo_children():
                    if isinstance(widget, ttk.Button):
                        widget_text = widget.cget('text').lower()
                        if 'add' in widget_text or '添加' in widget_text:
                            widget.config(text=_('add_library'))
                        elif 'delete' in widget_text or '删除' in widget_text:
                            widget.config(text=_('delete_library'))
                        elif 'rescan' in widget_text or '重新' in widget_text:
                            widget.config(text=_('refresh_library_list'))
                        elif 'close' in widget_text or '关闭' in widget_text:
                            widget.config(text=_('close'))
                        
        except Exception as e:
            print(f"更新库管理对话框语言失败: {e}")