#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
材质信息面板
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
from typing import Dict, Any, Callable, Optional, List
from src.gui.theme import ModernDarkTheme

class MaterialPanel:
    """材质信息编辑面板"""
    
    def __init__(self, parent, 
                 on_material_save: Optional[Callable[[str, Dict[str, Any]], None]] = None,
                 on_material_export: Optional[Callable[[str, Dict[str, Any]], None]] = None):
        """
        初始化材质信息面板
        
        Args:
            parent: 父容器
            on_material_save: 材质保存回调函数
            on_material_export: 材质导出回调函数
        """
        self.parent = parent
        self.on_material_save = on_material_save
        self.on_material_export = on_material_export
        
        self.current_material = None
        self.param_widgets = {}
        
        self._create_widgets()
        self._setup_bindings()
    
    def _create_widgets(self):
        """创建界面组件"""
        # 主容器
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 固定头部区域（不滚动）
        self.fixed_header = ttk.Frame(main_frame)
        self.fixed_header.pack(fill=tk.X, padx=10, pady=(10, 0))
        
        # 标题和按钮（固定在顶部）
        self.title_frame = ttk.Frame(self.fixed_header)
        self.title_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(self.title_frame, text="📋 材质信息", 
                 style='Title.TLabel').pack(side=tk.LEFT)
        
        # 操作按钮
        button_frame = ttk.Frame(self.title_frame)
        button_frame.pack(side=tk.RIGHT)
        
        ttk.Button(button_frame, text="💾 另存为", 
                  command=self._export_material).pack(side=tk.LEFT)
        
        # 分隔线
        self.separator = ttk.Separator(self.fixed_header, orient='horizontal')
        self.separator.pack(fill=tk.X, pady=(0, 5))
        
        # 可滚动内容区域
        content_container = ttk.Frame(main_frame)
        content_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # 创建Canvas和Scrollbar用于滚动
        self.canvas = tk.Canvas(content_container, bg='#1e1e1e', highlightthickness=0)
        scrollbar = ttk.Scrollbar(content_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # 优化滚动区域更新
        def update_scrollregion(event=None):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        self.scrollable_frame.bind("<Configure>", update_scrollregion)
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 改进的鼠标滚轮事件处理
        def _on_mousewheel(event):
            # 检查鼠标是否在canvas区域内
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            return "break"
        
        # 绑定滚轮事件
        def bind_mousewheel_recursive(widget):
            try:
                widget.bind("<MouseWheel>", _on_mousewheel)
                for child in widget.winfo_children():
                    bind_mousewheel_recursive(child)
            except:
                pass
        
        # 绑定到canvas和滚动内容
        self.canvas.bind("<MouseWheel>", _on_mousewheel)
        bind_mousewheel_recursive(self.scrollable_frame)
        
        # 响应窗口大小变化，优化canvas宽度
        def configure_canvas_width(event):
            canvas_width = event.width
            self.canvas.itemconfig(self.canvas_window, width=canvas_width)
        
        self.canvas.bind('<Configure>', configure_canvas_width)
        
        # 基本信息区域（在滚动区域内）
        self._create_basic_info_section()
        
        # 参数区域（在滚动区域内）
        self._create_params_section()
        
        # 初始状态显示提示
        self.empty_label = ttk.Label(self.scrollable_frame, 
                                   text="请在左侧选择一个材质来查看详细信息",
                                   style='Info.TLabel')
        self.empty_label.pack(expand=True, pady=50)
        
        # 设置 content_frame 引用（为了兼容性）
        self.content_frame = self.scrollable_frame
    
    def _create_basic_info_section(self):
        """创建基本信息区域 - 一行两个信息"""
        self.basic_frame = ttk.LabelFrame(self.scrollable_frame, text="📋 基本信息")
        self.basic_frame.pack(fill=tk.X, pady=(10, 10))
        
        # 创建基本信息字段
        self.basic_vars = {}
        basic_fields = [
            ('filename', '材质名称'),
            ('shader_path', '着色器路径'),
            ('source_path', '材质文件路径'),
            ('compression', '压缩类型'),
            ('key', '键值')
        ]
        
        # 使用网格布局，每行两个字段
        info_container = ttk.Frame(self.basic_frame)
        info_container.pack(fill=tk.X, padx=10, pady=10)
        
        row = 0
        col = 0
        
        for field, label in basic_fields:
            # 创建字段容器
            field_frame = ttk.Frame(info_container)
            field_frame.grid(row=row, column=col, sticky='ew', 
                           padx=(0, 15 if col == 0 else 0), pady=3)
            
            # 标签
            label_widget = ttk.Label(field_frame, text=f"{label}:", 
                                   font=('Microsoft YaHei UI', 9),
                                   width=12, anchor='w')
            label_widget.pack(side=tk.LEFT)
            
            # 输入框
            var = tk.StringVar()
            self.basic_vars[field] = var
            
            entry = ttk.Entry(field_frame, textvariable=var, 
                            font=('Microsoft YaHei UI', 9), width=25)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
            
            # 布局控制
            col += 1
            if col >= 2:  # 每行两个
                col = 0
                row += 1
        
        # 配置列权重
        info_container.grid_columnconfigure(0, weight=1)
        info_container.grid_columnconfigure(1, weight=1)
    
    def _create_params_section(self):
        """创建参数区域"""
        self.params_frame = ttk.LabelFrame(self.scrollable_frame, text="⚙️ 可编辑参数")
        
        # 参数工具栏
        param_toolbar = ttk.Frame(self.params_frame)
        param_toolbar.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(param_toolbar, text="➕ 添加参数", 
                  command=self._add_param).pack(side=tk.LEFT)
        ttk.Button(param_toolbar, text="🔄 刷新", 
                  command=self._refresh_params).pack(side=tk.LEFT, padx=(10, 0))
        
        # 参数网格容器 - 支持自适应布局
        self.params_grid_frame = ttk.Frame(self.params_frame)
        self.params_grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # 绑定大小变化事件
        self.params_grid_frame.bind('<Configure>', self._on_params_frame_configure)
    
    def _on_params_frame_configure(self, event):
        """参数框架大小变化事件"""
        # 防抖处理，避免频繁重新布局
        if hasattr(self, '_layout_timer'):
            self.params_grid_frame.after_cancel(self._layout_timer)
        self._layout_timer = self.params_grid_frame.after(100, self._layout_params_grid)
    
    def _layout_params_grid(self):
        """使用网格布局参数控件（优化版）"""
        if not hasattr(self, 'param_widgets') or not self.param_widgets:
            return
        
        # 获取框架宽度
        frame_width = self.params_grid_frame.winfo_width()
        if frame_width <= 1:  # 框架还没有正确大小
            return
        
        # 计算每个参数控件的最小宽度（估计值）
        min_param_width = 350
        
        # 计算列数
        new_columns = max(1, frame_width // min_param_width)
        
        # 如果列数没有变化，并且之前已经布局过了，则跳过
        if hasattr(self, '_last_columns') and self._last_columns == new_columns:
            return
        
        self._last_columns = new_columns
        
        # 批量处理网格布局，减少重绘次数
        widgets_to_layout = []
        for index, widget_data in self.param_widgets.items():
            frame = widget_data.get('frame')
            if frame and frame.winfo_exists():
                widgets_to_layout.append((index, frame))
        
        # 暂时禁用自动更新
        self.params_grid_frame.update_idletasks()
        
        # 重新排列参数控件
        row = 0
        col = 0
        
        for index, frame in widgets_to_layout:
            frame.grid(row=row, column=col, sticky='ew', padx=5, pady=5)
            
            col += 1
            if col >= new_columns:
                col = 0
                row += 1
        
        # 配置列权重
        for c in range(new_columns):
            self.params_grid_frame.grid_columnconfigure(c, weight=1)
        
        # 清理多余的列配置
        for c in range(new_columns, getattr(self, '_max_columns', 0)):
            self.params_grid_frame.grid_columnconfigure(c, weight=0)
        
        self._max_columns = max(getattr(self, '_max_columns', 0), new_columns)
    
    def _setup_bindings(self):
        """设置事件绑定"""
        pass
    
    def _rebind_mousewheel_events(self):
        """重新绑定鼠标滚轮事件到所有组件"""
        def _on_mousewheel(event):
            if hasattr(self, 'canvas'):
                self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                return "break"
        
        # 绑定滚轮事件到所有子组件
        def bind_mousewheel_recursive(widget):
            try:
                widget.bind("<MouseWheel>", _on_mousewheel)
                for child in widget.winfo_children():
                    bind_mousewheel_recursive(child)
            except:
                pass
        
        # 绑定到滚动区域的所有组件
        if hasattr(self, 'scrollable_frame'):
            bind_mousewheel_recursive(self.scrollable_frame)
    
    def display_material(self, material_data: Dict[str, Any]):
        """
        显示材质信息
        
        Args:
            material_data: 材质数据字典
        """
        self.current_material = material_data
        
        # 隐藏空状态提示
        self.empty_label.pack_forget()
        
        # 显示固定头部（标题和按钮）
        self.fixed_header.pack(fill=tk.X, padx=10, pady=(10, 0))
        
        # 显示信息区域
        self.basic_frame.pack(fill=tk.X, pady=(10, 10))
        self.params_frame.pack(fill=tk.BOTH, expand=True)
        
        # 加载基本信息
        self._load_basic_info()
        
        # 加载参数
        self._load_params()
        
        # 重新绑定滚轮事件到新显示的内容
        self._rebind_mousewheel_events()
    
    def load_material(self, material_data: Dict[str, Any]):
        """
        加载材质信息（与display_material相同的功能，为了兼容性）
        
        Args:
            material_data: 材质数据字典
        """
        self.display_material(material_data)
    
    def _load_basic_info(self):
        """加载基本信息"""
        if not self.current_material:
            return
        
        # 设置基本信息值
        for field, var in self.basic_vars.items():
            value = self.current_material.get(field, '')
            var.set(str(value) if value is not None else '')
    
    def _load_params(self):
        """加载参数信息"""
        # 清除现有参数控件
        for widget_data in self.param_widgets.values():
            frame = widget_data.get('frame')
            if frame:
                frame.destroy()
        self.param_widgets.clear()
        
        if not self.current_material:
            return
        
        # 获取参数数据
        params_data = self.current_material.get('params', [])
        if not isinstance(params_data, list):
            return
        
        # 创建参数控件
        for i, param in enumerate(params_data):
            self._create_param_widget(i, param)
        
        # 重新布局
        self._layout_params_grid()
    
    def _create_param_widget(self, index: int, param_data: Dict[str, Any]):
        """创建单个参数控件"""
        # 参数容器
        param_frame = ttk.LabelFrame(self.params_grid_frame, 
                                   text=f"参数 {index + 1}: {param_data.get('name', '')[:20]}...")
        
        # 参数类型
        type_frame = ttk.Frame(param_frame)
        type_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(type_frame, text="类型:", font=('Microsoft YaHei UI', 9)).pack(side=tk.LEFT)
        type_var = tk.StringVar(value=param_data.get('type', ''))
        type_combo = ttk.Combobox(type_frame, textvariable=type_var, 
                                font=('Microsoft YaHei UI', 9),
                                values=['Float', 'Float2', 'Float3', 'Float4', 'Float5', 'Int', 'Int2', 'Bool'],
                                state='readonly')
        type_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # 参数名称
        name_frame = ttk.Frame(param_frame)
        name_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(name_frame, text="名称:", font=('Microsoft YaHei UI', 9)).pack(side=tk.LEFT)
        name_var = tk.StringVar(value=param_data.get('name', ''))
        name_entry = ttk.Entry(name_frame, textvariable=name_var, 
                             font=('Microsoft YaHei UI', 9))
        name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # 参数值（智能处理数组）
        value_frame = ttk.Frame(param_frame)
        value_frame.pack(fill=tk.X, padx=5, pady=2)
        
        param_value = param_data.get('value', '')
        param_type = param_data.get('type', '')
        
        # 检查是否为数组类型
        if self._is_array_type(param_type):
            # 数组类型处理
            array_values = self._parse_array_from_xml_format(param_value)
            
            ttk.Label(value_frame, text=f"数组值 ({len(array_values)} 个元素):", 
                     font=('Microsoft YaHei UI', 9)).pack(side=tk.TOP, anchor='w')
            
            # 数组编辑区域（水平排列）
            array_container = ttk.Frame(value_frame)
            array_container.pack(fill=tk.X, pady=(2, 0))
            
            value_vars = []
            for i, val in enumerate(array_values):
                row_frame = ttk.Frame(array_container)
                row_frame.pack(fill=tk.X, pady=1)
                
                ttk.Label(row_frame, text=f"[{i}]:", width=4, font=('Microsoft YaHei UI', 9)).pack(side=tk.LEFT)
                var = tk.StringVar(value=str(val).strip())
                entry = ttk.Entry(row_frame, textvariable=var, font=('Microsoft YaHei UI', 9), width=15)
                entry.pack(side=tk.LEFT, padx=(2, 5))
                value_vars.append(var)
            
            # 数组操作按钮
            array_btn_frame = ttk.Frame(array_container)
            array_btn_frame.pack(fill=tk.X, pady=(5, 0))
            
            ttk.Button(array_btn_frame, text="+", width=3,
                      command=lambda: self._add_array_element(index)).pack(side=tk.LEFT)
            ttk.Button(array_btn_frame, text="-", width=3,
                      command=lambda: self._remove_array_element(index)).pack(side=tk.LEFT, padx=(2, 0))
            
            value_var = None  # 数组模式不使用单一变量
        else:
            # 单值显示（传统编辑）
            ttk.Label(value_frame, text="值:", font=('Microsoft YaHei UI', 9)).pack(side=tk.LEFT)
            value_var = tk.StringVar(value=str(param_value))
            value_entry = ttk.Entry(value_frame, textvariable=value_var, 
                                  font=('Microsoft YaHei UI', 9))
            value_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
            value_vars = None
        
        # 操作按钮
        button_frame = ttk.Frame(param_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="删除", 
                  command=lambda idx=index: self._remove_param(idx)).pack(side=tk.RIGHT)
        
        # 保存控件引用
        self.param_widgets[index] = {
            'frame': param_frame,
            'type_var': type_var,
            'name_var': name_var,
            'value_var': value_var,
            'value_vars': value_vars,  # 数组值列表
            'is_array': array_values is not None,
            'data': param_data
        }
    
    def _add_param(self):
        """添加新参数"""
        if not hasattr(self, 'param_widgets'):
            self.param_widgets = {}
        
        # 计算新索引
        new_index = len(self.param_widgets)
        
        # 创建新参数数据
        new_param = {
            'type': 'float',
            'name': f'新参数_{new_index + 1}',
            'value': '0.0'
        }
        
        # 创建控件
        self._create_param_widget(new_index, new_param)
        
        # 重新布局
        self._layout_params_grid()
    
    def _remove_param(self, index: int):
        """删除参数"""
        if index in self.param_widgets:
            widget_data = self.param_widgets[index]
            frame = widget_data.get('frame')
            if frame:
                frame.destroy()
            del self.param_widgets[index]
        
        # 重新布局
        self._layout_params_grid()
    
    def _refresh_params(self):
        """刷新参数显示"""
        self._load_params()
    
    def _export_material(self):
        """导出材质"""
        if self.current_material and self.on_material_export:
            # 直接调用导出方法，不传递参数
            self.on_material_export()
    
    def _is_array_type(self, param_type):
        """判断是否为数组类型"""
        return param_type in ['Float2', 'Float3', 'Float4', 'Float5', 'Int2']
    
    def _parse_array_from_xml_format(self, value):
        """从 XML 格式解析数组值"""
        if not value:
            return ['0.0']
        
        # 如果是字符串格式如 "[1.0, 2.0, 3.0]"
        if isinstance(value, str):
            value_str = value.strip()
            if value_str.startswith('[') and value_str.endswith(']'):
                try:
                    inner = value_str[1:-1].strip()
                    if inner:
                        return [elem.strip() for elem in inner.split(',')]
                except:
                    pass
            return [value_str]
        
        # 如果是列表格式（XML中的奇怪格式）
        if isinstance(value, list):
            # 重建正确的数组格式
            result = []
            current_number = ''
            for item in value:
                item_str = str(item)
                if item_str == '[':
                    continue
                elif item_str == ']':
                    if current_number:
                        result.append(current_number)
                    break
                elif item_str == ',':
                    if current_number:
                        result.append(current_number)
                        current_number = ''
                elif item_str == ' ':
                    continue
                else:
                    current_number += item_str
            
            if current_number:
                result.append(current_number)
            
            return result if result else ['0.0']
        
        return [str(value)]
    
    def _add_array_element(self, param_index):
        """添加数组元素"""
        # 重新创建该参数控件，添加一个新元素
        if param_index in self.param_widgets:
            widget_data = self.param_widgets[param_index]
            if widget_data.get('is_array') and widget_data.get('value_vars'):
                # 添加一个新的默认值
                current_values = [var.get() for var in widget_data['value_vars']]
                current_values.append('0.0')
                
                # 更新参数数据
                array_str = '[' + ', '.join(current_values) + ']'
                widget_data['data']['value'] = array_str
                
                # 重新创建控件
                self._recreate_param_widget(param_index)
    
    def _remove_array_element(self, param_index):
        """移除数组元素"""
        if param_index in self.param_widgets:
            widget_data = self.param_widgets[param_index]
            if widget_data.get('is_array') and widget_data.get('value_vars'):
                current_values = [var.get() for var in widget_data['value_vars']]
                if len(current_values) > 1:  # 至少保留一个元素
                    current_values.pop()  # 移除最后一个
                    
                    # 更新参数数据
                    array_str = '[' + ', '.join(current_values) + ']'
                    widget_data['data']['value'] = array_str
                    
                    # 重新创建控件
                    self._recreate_param_widget(param_index)
    
    def _recreate_param_widget(self, param_index):
        """重新创建参数控件"""
        if param_index in self.param_widgets:
            widget_data = self.param_widgets[param_index]
            param_data = widget_data['data']
            
            # 保存当前编辑的值
            param_data['type'] = widget_data['type_var'].get()
            param_data['name'] = widget_data['name_var'].get()
            
            if widget_data.get('is_array') and widget_data.get('value_vars'):
                # 数组模式：收集所有数组元素
                current_values = [var.get() for var in widget_data['value_vars']]
                array_str = '[' + ', '.join(current_values) + ']'
                param_data['value'] = array_str
            elif widget_data.get('value_var'):
                # 单值模式
                param_data['value'] = widget_data['value_var'].get()
            
            # 删除旧控件
            widget_data['frame'].destroy()
            
            # 重新创建
            self._create_param_widget(param_index, param_data)
            
            # 重新布局
            self._layout_params_grid()
    
    def _collect_material_data(self) -> Dict[str, Any]:
        """收集当前编辑的材质数据"""
        if not self.current_material:
            return {}
        
        # 复制原始数据
        material_data = dict(self.current_material)
        
        # 更新基本信息
        for field, var in self.basic_vars.items():
            material_data[field] = var.get()
        
        # 更新参数
        params = []
        for widget_data in self.param_widgets.values():
            param = {
                'type': widget_data['type_var'].get(),
                'name': widget_data['name_var'].get()
            }
            
            # 处理参数值（数组或单值）
            if widget_data.get('is_array') and widget_data.get('value_vars'):
                # 数组模式：收集所有数组元素
                array_values = [var.get() for var in widget_data['value_vars']]
                param['value'] = '[' + ', '.join(array_values) + ']'
            elif widget_data.get('value_var'):
                # 单值模式
                param['value'] = widget_data['value_var'].get()
            else:
                param['value'] = ''
            
            params.append(param)
        
        material_data['params'] = params
        
        return material_data
    
    def get_material_data(self) -> Dict[str, Any]:
        """获取当前材质数据（供外部调用）"""
        return self._collect_material_data()
    
    def clear(self):
        """清空显示"""
        self.current_material = None
        
        # 隐藏固定头部
        if hasattr(self, 'fixed_header'):
            self.fixed_header.pack_forget()
        
        # 隐藏信息区域
        self.basic_frame.pack_forget()
        self.params_frame.pack_forget()
        
        # 显示空状态提示
        self.empty_label.pack(expand=True, pady=50)
        
        # 清空参数控件
        for widget_data in self.param_widgets.values():
            frame = widget_data.get('frame')
            if frame:
                frame.destroy()
        self.param_widgets.clear()