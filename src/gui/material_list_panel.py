#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
材质列表面板 - 显示材质列表（简化版）
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional, List, Dict, Any
from src.gui.theme import ModernDarkTheme
from src.core.i18n import language_manager, _

class MaterialListPanel:
    """材质列表面板（简化版）"""
    
    def __init__(self, parent, database, 
                 on_material_select: Callable[[int], None] = None):
        """
        初始化材质列表面板
        
        Args:
            parent: 父容器
            database: 数据库实例
            on_material_select: 材质选择回调
        """
        self.parent = parent
        self.database = database
        self.on_material_select = on_material_select
        
        self.current_library_id = None
        self.materials = []  # 原始材质数据
        self.displayed_materials = []  # 当前显示的材质数据（搜索结果或全部）
        
        self._create_widgets()
        self._setup_bindings()
        
    def _create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.title_label = ttk.Label(title_frame, text=_("material_list"), 
                 style='Heading.TLabel')
        self.title_label.pack(side=tk.LEFT)
        
        # 统计信息
        self.count_label = ttk.Label(title_frame, text="", style='Info.TLabel')
        self.count_label.pack(side=tk.RIGHT)

        # 搜索框
        self.search_frame = ttk.Frame(main_frame)
        self.search_frame.pack(fill=tk.X, pady=(0, 5))

        # 暴露给 update_language 使用的搜索标签和变量
        self.search_label = ttk.Label(self.search_frame, text=_('search_label'))
        self.search_label.pack(side=tk.LEFT)

        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._on_search_change)
        search_entry = ttk.Entry(self.search_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)

        # 材质列表
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        # 使用Listbox替代TreeView
        self.material_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.material_listbox.yview)
        self.material_listbox.configure(yscrollcommand=scrollbar.set)

        self.material_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 应用主题样式
        ModernDarkTheme.configure_listbox(self.material_listbox)

        # 空状态提示
        self.empty_label = ttk.Label(main_frame,
                                   text=_('select_library_hint'),
                                   style='Info.TLabel')
        
    def _setup_bindings(self):
        """设置事件绑定"""
        # 材质选择事件
        self.material_listbox.bind('<<ListboxSelect>>', self._on_material_select)
        
        # 双击事件
        self.material_listbox.bind('<Double-1>', self._on_material_double_click)
        
        # 右键菜单
        self.material_listbox.bind('<Button-3>', self._show_context_menu)
    
    def load_materials(self, library_id: int):
        """加载指定库的材质列表"""
        self.current_library_id = library_id
        
        try:
            # 获取材质列表
            self.materials = self.database.search_materials(library_id=library_id)
            
            # 更新列表
            self._update_material_list()
            
            # 隐藏空状态
            self.empty_label.pack_forget()
            
            # 更新统计
            self.count_label.config(text=_('material_count').format(count=len(self.materials)))
            
        except Exception as e:
            messagebox.showerror(_('error'), f"{_('load_failed')}：{str(e)}")
    
    def _update_material_list(self, filtered_materials=None):
        """更新材质列表显示"""
        # 清空列表
        self.material_listbox.delete(0, tk.END)
        
        # 使用过滤后的材质或全部材质
        materials_to_show = filtered_materials if filtered_materials is not None else self.materials
        
        # 更新当前显示的材质数据
        self.displayed_materials = materials_to_show
        
        # 添加材质到列表
        for material in materials_to_show:
            display_name = material.get('filename', _('unknown_material'))
            self.material_listbox.insert(tk.END, display_name)
    
    def _on_material_select(self, event):
        """材质选择事件处理"""
        selection = self.material_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        # 使用当前显示的材质数据而不是原始数据
        if index < len(self.displayed_materials):
            material = self.displayed_materials[index]
            
            # 触发回调
            if self.on_material_select:
                self.on_material_select(material['id'])
    
    def _on_material_double_click(self, event):
        """材质双击事件处理"""
        # 可以添加双击处理逻辑
        pass
    
    def _on_search_change(self, *args):
        """搜索框变化事件"""
        search_text = self.search_var.get().strip().lower()
        
        if not search_text:
            # 显示所有材质
            self._update_material_list()
            self.count_label.config(text=_('material_count').format(count=len(self.materials)))
            return
        
        # 执行搜索
        self._perform_search(search_text)
    
    def _perform_search(self, keyword: str):
        """执行搜索"""
        if not self.current_library_id:
            return
        
        try:
            # 按材质名称、着色器名称和样例名称搜索
            results = self.database.search_materials_extended(
                library_id=self.current_library_id,
                keyword=keyword
            )
            
            # 更新显示
            self._update_material_list(results)
            self.count_label.config(text=_('search_results').format(count=len(results)))
            
        except Exception as e:
            messagebox.showerror(_('error'), f"{_('search_failed')}：{str(e)}")
    
    def search_materials(self, keyword: str):
        """外部搜索接口"""
        self.search_var.set(keyword)
    
    def show_search_results(self, results: List[Dict[str, Any]]):
        """显示搜索结果"""
        try:
            # 更新材质列表显示
            self._update_material_list(results)
            
            # 更新统计信息
            count = len(results) if results else 0
            self.count_label.config(text=_('search_results').format(count=count))
            
        except Exception as e:
            messagebox.showerror(_('error'), f"{_('show_results_failed')}：{str(e)}")
    
    
    def _show_context_menu(self, event):
        """显示右键菜单"""
        selection = self.material_listbox.curselection()
        if not selection:
            return
        
        menu = tk.Menu(self.parent, tearoff=0)
        menu.add_command(label=_('view_details'), command=self._view_material_detail)
        menu.add_command(label=_('copy_name'), command=self._copy_material_name)
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
    
    def _view_material_detail(self):
        """查看材质详情"""
        selection = self.material_listbox.curselection()
        if selection:
            self._on_material_select(None)
    
    def _copy_material_name(self):
        """复制材质名称"""
        selection = self.material_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        # 使用当前显示的材质数据而不是原始数据
        if index < len(self.displayed_materials):
            material = self.displayed_materials[index]
            name = material.get('filename', '')
            if name:
                self.parent.clipboard_clear()
                self.parent.clipboard_append(name)
                messagebox.showinfo(_('success'), _('material_name_copied').format(name=name))
    
    def clear(self):
        """清空列表"""
        self.materials = []
        self.displayed_materials = []
        self.material_listbox.delete(0, tk.END)
        self.current_library_id = None
        self.count_label.config(text="")
        self.search_var.set("")
        
        # 显示空状态
        self.empty_label.pack(expand=True, pady=20)
    
    def update_language(self):
        """更新界面语言"""
        try:
            # 更新标题
            if hasattr(self, 'title_label'):
                self.title_label.config(text=_("material_list"))
            
            # 更新空状态提示
            if hasattr(self, 'empty_label'):
                self.empty_label.config(text=_("select_library_hint"))
            
            # 更新搜索控件
            if hasattr(self, 'search_label'):
                self.search_label.config(text=_('search_label'))
            
            # 更新分组选择
            if hasattr(self, 'group_var') and hasattr(self, 'grouped_materials'):
                # 重新设置分组选项
                group_options = [_('all_materials')] + list(self.grouped_materials.keys())
                if hasattr(self, 'group_combobox'):
                    current = self.group_var.get()
                    self.group_combobox['values'] = group_options
                    # 如果当前选择等于翻译前的文本 '全部材质'，更新为翻译后的文本
                    if current == _('all_materials') or current == '全部材质':
                        self.group_var.set(_('all_materials'))
            
            # 更新统计信息
            if hasattr(self, 'materials') and self.materials:
                self.count_label.config(text=_('material_count').format(count=len(self.materials)))
            
            # 更新列表中的材质项
            if hasattr(self, 'material_listbox') and hasattr(self, 'materials'):
                # 刷新当前显示的列表（优先 displayed_materials）
                if self.displayed_materials:
                    self._update_material_list(self.displayed_materials)
                else:
                    self._update_material_list(self.materials)
                
        except Exception as e:
            print(f"Error updating material list panel language: {e}")