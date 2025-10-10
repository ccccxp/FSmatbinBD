#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
材质样例面板 - 显示材质的Sampler信息（只读，支持复制）
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
from typing import List, Dict, Any
from src.gui.theme import ModernDarkTheme
from src.core.i18n import language_manager, _

class SamplerPanel:
    """材质样例面板（只读版本）"""
    
    def __init__(self, parent):
        """
        初始化样例面板
        
        Args:
            parent: 父容器
        """
        self.parent = parent
        self.samplers_data = []
        
        self._create_widgets()
    
    def _create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 固定标题栏（不滚动）
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        self.title_label = ttk.Label(title_frame, text=_("material_samples"), 
                 style='Title.TLabel')
        self.title_label.pack(side=tk.LEFT)
        
        # 统计信息
        self.count_label = ttk.Label(title_frame, text="", style='Info.TLabel')
        self.count_label.pack(side=tk.RIGHT)
        
        # 提示信息
        hint_frame = ttk.Frame(main_frame)
        hint_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        self.hint_label = ttk.Label(hint_frame, text=_('double_click_copy_hint'), 
                 style='Info.TLabel')
        self.hint_label.pack(side=tk.LEFT)
        
        # 样例列表容器
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # 配置TreeView - 增加更多列显示完整信息
        columns = ('type', 'path', 'key', 'unk14_x', 'unk14_y')
        self.sampler_tree = ttk.Treeview(list_frame, columns=columns, 
                                       show='tree headings', height=8)
        
        # 配置列标题和宽度
        self.sampler_tree.heading('#0', text=_('sequence_number'))
        self.sampler_tree.heading('type', text=_('sampler_type'))
        self.sampler_tree.heading('path', text=_('sampler_path'))
        self.sampler_tree.heading('key', text=_('key_value'))
        self.sampler_tree.heading('unk14_x', text=_('unk14_x'))
        self.sampler_tree.heading('unk14_y', text=_('unk14_y'))
        
        # 调整列宽度 - 缩短序号/键值/UN14X/UN14Y，增加样例名称和路径宽度
        self.sampler_tree.column('#0', width=30, minwidth=30, anchor='center')
        self.sampler_tree.column('type', width=200, minwidth=150)
        self.sampler_tree.column('path', width=400, minwidth=300)
        self.sampler_tree.column('key', width=50, minwidth=40)
        self.sampler_tree.column('unk14_x', width=45, minwidth=40, anchor='center')
        self.sampler_tree.column('unk14_y', width=45, minwidth=40, anchor='center')
        
        # 滚动条
        scrollbar_v = ttk.Scrollbar(list_frame, orient=tk.VERTICAL,
                                  command=self.sampler_tree.yview)
        scrollbar_h = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL,
                                  command=self.sampler_tree.xview)
        
        self.sampler_tree.configure(yscrollcommand=scrollbar_v.set,
                                  xscrollcommand=scrollbar_h.set)
        
        # 布局
        self.sampler_tree.grid(row=0, column=0, sticky='nsew')
        scrollbar_v.grid(row=0, column=1, sticky='ns')
        scrollbar_h.grid(row=1, column=0, sticky='ew')
        
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # 绑定双击事件
        self.sampler_tree.bind('<Double-1>', self._on_double_click)

        # 空状态提示
        self.empty_label = ttk.Label(main_frame, 
                                   text=_('select_material_hint'),
                                   style='Info.TLabel')
        self.empty_label.pack(expand=True, pady=20)
    
    def _on_double_click(self, event):
        """双击事件 - 复制单元格内容到剪贴板"""
        region = self.sampler_tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        
        # 获取点击的项目和列
        item = self.sampler_tree.identify_row(event.y)
        column = self.sampler_tree.identify_column(event.x)
        
        if not item:
            return
        
        # 获取单元格内容
        if column == "#0":
            # 序号列
            cell_value = self.sampler_tree.item(item, "text")
            column_name = _('sequence_number')
        else:
            # 数据列
            column_index = int(column[1:]) - 1  # #1, #2, #3, #4, #5 -> 0, 1, 2, 3, 4
            values = self.sampler_tree.item(item, "values")
            if 0 <= column_index < len(values):
                cell_value = values[column_index]
                # 列名映射
                column_names = [_('sampler_type'), _('sampler_path'), _('key_value'), _('unk14_x'), _('unk14_y')]
                column_name = column_names[column_index] if column_index < len(column_names) else _('unknown_column')
            else:
                return
        
        # 复制到剪贴板
        if cell_value:
            try:
                self.parent.clipboard_clear()
                self.parent.clipboard_append(str(cell_value))
                self._show_copy_feedback(cell_value, column_name)
            except Exception as e:
                # 使用本地化的错误标题和消息
                messagebox.showerror(_('error'), f"{_('copy_failed')}: {str(e)}")
    
    def _show_copy_feedback(self, content, column_name=_('content')):
        """显示复制反馈"""
        # 限制显示长度
        display_content = content[:50] + "..." if len(content) > 50 else content
        # 本地化成功提示
        messagebox.showinfo(_('copy_success'), _('copied_to_clipboard').format(column_name=column_name, content=display_content))
    
    def load_samplers(self, samplers: List[Dict[str, Any]]):
        """加载样例数据"""
        self.samplers_data = samplers
        
        if not samplers:
            # 显示空状态
            self._show_empty_state()
            return
        
        # 隐藏空状态
        self.empty_label.pack_forget()
        
        # 清空现有数据
        for item in self.sampler_tree.get_children():
            self.sampler_tree.delete(item)
        
        # 添加样例数据
        for i, sampler in enumerate(samplers):
            # 处理路径显示
            path = sampler.get('path', '')
            sampler_type = sampler.get('type', '')
            key_value = sampler.get('key_value', '')
            
            # 处理 Unk14 数据
            unk14 = sampler.get('unk14', {})
            unk14_x = str(unk14.get('X', 0)) if unk14 else '0'
            unk14_y = str(unk14.get('Y', 0)) if unk14 else '0'
            
            # 插入数据
            self.sampler_tree.insert('', tk.END,
                                   text=str(i + 1),
                                   values=(sampler_type, path, key_value, unk14_x, unk14_y))
        
        # 更新统计信息
        self.count_label.config(text=_('sampler_count').format(count=len(samplers)))
    
    def _show_empty_state(self):
        """显示空状态"""
        self.empty_label.pack(expand=True, pady=20)
        
        # 清空列表
        for item in self.sampler_tree.get_children():
            self.sampler_tree.delete(item)
        
        # 清空统计
        self.count_label.config(text="")
    
    def clear(self):
        """清空面板"""
        self.samplers_data = []
        self._show_empty_state()
    
    def update_language(self):
        """更新界面语言"""
        try:
            # 更新标题
            if hasattr(self, 'title_label'):
                self.title_label.config(text=_("material_samples"))
            
            # 更新提示文本
            if hasattr(self, 'hint_label'):
                self.hint_label.config(text=_('double_click_copy_hint'))
            
            # 更新空状态提示
            if hasattr(self, 'empty_label'):
                self.empty_label.config(text=_('select_material_hint'))
            
            # 更新表格列标题
            if hasattr(self, 'sampler_tree'):
                self.sampler_tree.heading('#0', text=_('sequence_number'))
                self.sampler_tree.heading('type', text=_('sampler_type'))
                self.sampler_tree.heading('path', text=_('sampler_path'))
                self.sampler_tree.heading('key', text=_('key_value'))
                self.sampler_tree.heading('unk14_x', text=_('unk14_x'))
                self.sampler_tree.heading('unk14_y', text=_('unk14_y'))
                
            # 更新统计信息
            if hasattr(self, 'count_label') and hasattr(self, 'samplers_data'):
                count = len(self.samplers_data) if self.samplers_data else 0
                if count > 0:
                    self.count_label.config(text=_('sampler_count').format(count=count))
                else:
                    self.count_label.config(text="")
                
        except Exception as e:
            print(f"Error updating sampler panel language: {e}")