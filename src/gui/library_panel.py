#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
库列表面板 - 显示材质库和材质列表
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional, List, Dict, Any
from ..core.i18n import _

class LibraryPanel:
    """材质库列表面板"""
    
    def __init__(self, parent, database, 
                 on_library_select: Callable[[int], None] = None,
                 on_material_select: Callable[[int], None] = None,
                 on_library_manage: Callable[[str, int], None] = None,
                 on_autopack_manage: Callable[[], None] = None):
        """
        初始化库列表面板
        
        Args:
            parent: 父容器
            database: 数据库实例
            on_library_select: 库选择回调
            on_material_select: 材质选择回调
            on_library_manage: 库管理回调
            on_autopack_manage: 自动封包管理回调
        """
        self.parent = parent
        self.database = database
        self.on_library_select = on_library_select
        self.on_material_select = on_material_select
        self.on_library_manage = on_library_manage
        self.on_autopack_manage = on_autopack_manage
        
        self.current_library_id = None
        self.libraries = []
        self.materials = []
        
        self._create_widgets()
        self._setup_bindings()
        
    def _create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(title_frame, text=f"📚 {_('library_manager')}",
                  style='Title.TLabel').pack(side=tk.LEFT)

        # 按钮容器
        button_frame = ttk.Frame(title_frame)
        button_frame.pack(side=tk.RIGHT)

        # 自动封包按钮
        self.autopack_btn = ttk.Button(button_frame, text=_("autopack_manager"), 
                                       command=self._show_autopack_dialog)
        self.autopack_btn.pack(side=tk.LEFT, padx=(0, 5))

        # 库管理按钮
        self.manage_btn = ttk.Button(button_frame, text="⚙️", width=3,
                                     command=self._show_manage_menu)
        self.manage_btn.pack(side=tk.LEFT)

        # 库列表
        library_frame = ttk.LabelFrame(main_frame, text=f"📚 {_('imported_libraries')}")
        library_frame.pack(fill=tk.X, pady=(0, 10))

        # 库列表框
        library_list_frame = ttk.Frame(library_frame)
        library_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 库列表
        self.library_listbox = tk.Listbox(library_list_frame, height=4,
                                          selectmode=tk.SINGLE)
        library_scrollbar = ttk.Scrollbar(library_list_frame, orient=tk.VERTICAL,
                                          command=self.library_listbox.yview)
        self.library_listbox.configure(yscrollcommand=library_scrollbar.set)

        self.library_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        library_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 材质列表
        material_frame = ttk.LabelFrame(main_frame, text=f"📋 {_('material_list')}")
        material_frame.pack(fill=tk.BOTH, expand=True)

        # 搜索框
        search_frame = ttk.Frame(material_frame)
        search_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        self.search_label = ttk.Label(search_frame, text=_('filter') + ':')
        self.search_label.pack(side=tk.LEFT)
        self.filter_var = tk.StringVar()
        self.filter_var.trace('w', self._on_filter_change)
        filter_entry = ttk.Entry(search_frame, textvariable=self.filter_var, width=20)
        filter_entry.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)

        # 材质列表树视图
        material_list_frame = ttk.Frame(material_frame)
        material_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # 配置列
        columns = ('name', 'file', 'shader')
        self.material_tree = ttk.Treeview(material_list_frame, columns=columns,
                                         show='tree headings', height=15)

        # 配置列标题
        self.material_tree.heading('#0', text=_('id_column'))
        self.material_tree.heading('name', text=_('material_name'))
        self.material_tree.heading('file', text=_('filename'))
        self.material_tree.heading('shader', text=_('shader_name'))

        # 配置列宽
        self.material_tree.column('#0', width=50, minwidth=50)
        self.material_tree.column('name', width=150, minwidth=100)
        self.material_tree.column('file', width=120, minwidth=100)
        self.material_tree.column('shader', width=100, minwidth=80)

        # 滚动条
        material_scrollbar = ttk.Scrollbar(material_list_frame, orient=tk.VERTICAL,
                                           command=self.material_tree.yview)
        self.material_tree.configure(yscrollcommand=material_scrollbar.set)

        self.material_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        material_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 统计信息
        self.info_label = ttk.Label(main_frame, text="", style='Info.TLabel')
        self.info_label.pack(fill=tk.X, pady=(5, 0))
        
    def _setup_bindings(self):
        """设置事件绑定"""
        # 库选择事件
        self.library_listbox.bind('<<ListboxSelect>>', self._on_library_select)
        
        # 材质选择事件
        self.material_tree.bind('<<TreeviewSelect>>', self._on_material_select)
        
        # 双击事件
        self.material_tree.bind('<Double-1>', self._on_material_double_click)
        
        # 右键菜单
        self.library_listbox.bind('<Button-3>', self._show_library_context_menu)
        self.material_tree.bind('<Button-3>', self._show_material_context_menu)
    
    def refresh_libraries(self):
        """刷新材质库列表"""
        try:
            # 获取所有库
            self.libraries = self.database.get_libraries()
            
            # 清空列表
            self.library_listbox.delete(0, tk.END)
            
            # 添加库到列表
            for lib in self.libraries:
                display_name = f"{lib['name']} ({lib['id']})"
                if lib['description']:
                    display_name += f" - {lib['description']}"
                self.library_listbox.insert(tk.END, display_name)
            
            # 更新信息
            self._update_info(_('library_count').format(count=len(self.libraries)))
            
            # 清空材质列表
            self._clear_materials()
            
        except Exception as e:
            messagebox.showerror(_('error'), f"{_('refresh_library_list_failed')}: {str(e)}")
    
    def _on_library_select(self, event):
        """库选择事件处理"""
        selection = self.library_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        if index < len(self.libraries):
            library = self.libraries[index]
            self.current_library_id = library['id']
            
            # 触发回调
            if self.on_library_select:
                self.on_library_select(library['id'])
            
            # 加载材质列表
            self._load_materials(library['id'])
    
    def _load_materials(self, library_id: int):
        """加载指定库的材质列表"""
        try:
            # 获取材质列表
            self.materials = self.database.search_materials(library_id=library_id)
            
            # 更新材质树视图
            self._update_material_tree()
            
            # 更新信息
            self._update_info(_('material_count').format(count=len(self.materials)))
            
        except Exception as e:
            messagebox.showerror(_('error'), f"{_('load_failed')}: {str(e)}")
    
    def _update_material_tree(self):
        """更新材质树视图"""
        # 清空树视图
        for item in self.material_tree.get_children():
            self.material_tree.delete(item)
        
        # 添加材质
        for material in self.materials:
            # 简化着色器路径显示
            shader_path = material.get('shader_path', '')
            shader_name = shader_path.split('\\')[-1] if shader_path else ''
            
            item_id = self.material_tree.insert('', tk.END, 
                                              text=str(material['id']),
                                              values=(
                                                  material.get('filename', ''),
                                                  material.get('file_name', ''),
                                                  shader_name
                                              ))
            
            # 不需要设置#0列，因为已经在text中设置了
    
    def _on_material_select(self, event):
        """材质选择事件处理"""
        selection = self.material_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        material_id = int(self.material_tree.item(item)['text'])
        
        # 触发回调
        if self.on_material_select:
            self.on_material_select(material_id)
    
    def _on_material_double_click(self, event):
        """材质双击事件处理"""
        # 可以在这里添加双击处理逻辑，比如快速编辑
        pass
    
    def _on_filter_change(self, *args):
        """过滤器变化事件"""
        filter_text = self.filter_var.get().strip().lower()
        
        if not filter_text:
            # 显示所有材质
            self._update_material_tree()
            return
        
        # 过滤材质
        filtered_materials = []
        for material in self.materials:
            # 检查各个字段
            if (filter_text in material.get('filename', '').lower() or
                filter_text in material.get('file_name', '').lower() or
                filter_text in material.get('shader_path', '').lower()):
                filtered_materials.append(material)
        
        # 更新树视图
        for item in self.material_tree.get_children():
            self.material_tree.delete(item)
        
        for material in filtered_materials:
            shader_path = material.get('shader_path', '')
            shader_name = shader_path.split('\\')[-1] if shader_path else ''
            
            self.material_tree.insert('', tk.END,
                                    text=str(material['id']),
                                    values=(
                                        material.get('filename', ''),
                                        material.get('file_name', ''),
                                        shader_name
                                    ))
        
        self._update_info(_('search_results').format(count=len(filtered_materials)))
    
    def _clear_materials(self):
        """清空材质列表"""
        for item in self.material_tree.get_children():
            self.material_tree.delete(item)
        self.materials = []
        self.current_library_id = None
    
    def _update_info(self, text: str):
        """更新信息标签"""
        self.info_label.config(text=text)
    
    def _show_manage_menu(self):
        """显示管理菜单"""
        if not self.current_library_id:
            messagebox.showinfo(_('info'), _('please_select_library'))
            return
        
        menu = tk.Menu(self.parent, tearoff=0)
        menu.add_command(label=_('rename_library'), command=self._rename_library)
        menu.add_command(label=_('edit_description'), command=self._edit_description)
        menu.add_separator()
        menu.add_command(label=_('delete_library'), command=self._delete_library)
        
        try:
            menu.tk_popup(self.manage_btn.winfo_rootx(), 
                         self.manage_btn.winfo_rooty() + self.manage_btn.winfo_height())
        finally:
            menu.grab_release()
    
    def _show_autopack_dialog(self):
        """显示自动封包对话框"""
        if self.on_autopack_manage:
            self.on_autopack_manage()
    
    def _show_library_context_menu(self, event):
        """显示库右键菜单"""
        selection = self.library_listbox.curselection()
        if not selection:
            return
        
        menu = tk.Menu(self.parent, tearoff=0)
        menu.add_command(label=_('rename_library'), command=self._rename_library)
        menu.add_command(label=_('edit_description'), command=self._edit_description)
        menu.add_separator()
        menu.add_command(label=_('delete_library'), command=self._delete_library)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
    
    def _show_material_context_menu(self, event):
        """显示材质右键菜单"""
        selection = self.material_tree.selection()
        if not selection:
            return
        
        menu = tk.Menu(self.parent, tearoff=0)
        menu.add_command(label=_('edit'), command=lambda: self._on_material_select(None))
        menu.add_command(label=_('copy'), command=self._copy_material_path)
        menu.add_separator()
        menu.add_command(label=_('menu_export_material'), command=self._export_material)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
    
    def _rename_library(self):
        """重命名材质库"""
        if not self.current_library_id:
            return
        
        # 找到当前库信息
        current_lib = None
        for lib in self.libraries:
            if lib['id'] == self.current_library_id:
                current_lib = lib
                break
        
        if not current_lib:
            return
        
        # 输入新名称
        new_name = tk.simpledialog.askstring(
            _('rename_library'),
            _('please_enter_new_name'),
            initialvalue=current_lib['name']
        )
        
        if new_name and new_name != current_lib['name']:
            try:
                self.database.update_library(self.current_library_id, name=new_name)
                self.refresh_libraries()
                messagebox.showinfo(_('success'), _('library_rename_success'))
            except Exception as e:
                messagebox.showerror(_('error'), f"{_('rename_failed')}: {str(e)}")
    
    def _edit_description(self):
        """编辑库描述"""
        if not self.current_library_id:
            return
        
        # 找到当前库信息
        current_lib = None
        for lib in self.libraries:
            if lib['id'] == self.current_library_id:
                current_lib = lib
                break
        
        if not current_lib:
            return
        
        # 输入新描述
        new_desc = tk.simpledialog.askstring(
            _('edit_description'),
            _('please_enter_new_name'),
            initialvalue=current_lib.get('description', '')
        )
        
        if new_desc is not None:
            try:
                self.database.update_library(self.current_library_id, description=new_desc)
                self.refresh_libraries()
                messagebox.showinfo(_('success'), _('library_description_updated'))
            except Exception as e:
                messagebox.showerror(_('error'), f"{_('update_description_failed')}: {str(e)}")
    
    def _delete_library(self):
        """删除材质库"""
        if not self.current_library_id:
            return
        
        if self.on_library_manage:
            self.on_library_manage("delete", self.current_library_id)
    
    def _copy_material_path(self):
        """复制材质路径"""
        selection = self.material_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        material_id = int(self.material_tree.item(item)['text'])
        
        # 查找材质信息
        for material in self.materials:
            if material['id'] == material_id:
                path = material.get('file_path', '')
                if path:
                    self.parent.clipboard_clear()
                    self.parent.clipboard_append(path)
                    messagebox.showinfo(_('success'), _('path_copied').format(path=path))
                break
    
    def _export_material(self):
        """导出当前材质"""
        selection = self.material_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        material_id = int(self.material_tree.item(item)['text'])
        
        if self.on_material_select:
            self.on_material_select(material_id)
    
    def search_materials(self, keyword: str):
        """搜索材质"""
        if not self.current_library_id:
            messagebox.showinfo(_('info'), _('select_library_hint'))
            return
        
        try:
            # 执行搜索
            results = self.database.search_materials(
                library_id=self.current_library_id,
                keyword=keyword
            )
            
            # 更新材质列表
            self.materials = results
            self._update_material_tree()
            self._update_info(_('search_results').format(count=len(results)))
            
        except Exception as e:
            messagebox.showerror(_('error'), f"{_('search_failed')}: {str(e)}")
    
    def clear_search(self):
        """清空搜索"""
        self.filter_var.set("")
        if self.current_library_id:
            self._load_materials(self.current_library_id)
    
    def update_language(self):
        """更新界面语言"""
        try:
            # 更新材质列表列标题
            self.material_tree.heading('#0', text=_('id_column'))
            self.material_tree.heading('name', text=_('material_name'))
            self.material_tree.heading('file', text=_('filename'))
            self.material_tree.heading('shader', text=_('shader_name'))
            
            # 更新搜索标签（使用 'filter' 键保持与创建时一致）
            self.search_label.config(text=_('filter') + ':')
            
        except Exception as e:
            print(f"更新库面板语言失败: {e}")
import tkinter.simpledialog