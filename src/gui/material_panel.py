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
from src.core.i18n import language_manager, _

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
        
        # 性能优化相关属性
        self._cached_font = None
        self._cached_type_values = None
        
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
        
        self.title_label = ttk.Label(self.title_frame, text=_("material_info_panel"), 
                 style='Title.TLabel')
        self.title_label.pack(side=tk.LEFT)
        
        # 操作按钮
        button_frame = ttk.Frame(self.title_frame)
        button_frame.pack(side=tk.RIGHT)
        
        # 自动封包选项
        self.autopack_var = tk.BooleanVar()
        self.autopack_check = ttk.Checkbutton(button_frame, text=_('add_to_autopack'), 
                                             variable=self.autopack_var)
        self.autopack_check.pack(side=tk.LEFT, padx=(0, 10))
        
        self.save_as_btn = ttk.Button(button_frame, text=_('save_as_button'), 
                                     command=self._export_material)
        self.save_as_btn.pack(side=tk.LEFT)
        
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
                                   text=_('select_material_detail_hint'),
                                   style='Info.TLabel')
        self.empty_label.pack(expand=True, pady=50)
        
        # 设置 content_frame 引用（为了兼容性）
        self.content_frame = self.scrollable_frame
    
    def _create_basic_info_section(self):
        """创建基本信息区域 - 一行两个信息"""
        self.basic_frame = ttk.LabelFrame(self.scrollable_frame, text=_("basic_info"))
        self.basic_frame.pack(fill=tk.X, pady=(10, 10))
        
        # 创建基本信息字段
        self.basic_vars = {}
        self.basic_labels = {}  # 存储标签widget引用
        basic_fields = [
            ('filename', _('material_name')),
            ('shader_path', _('shader_path')),
            ('source_path', _('material_file_path')),
            ('compression', _('compression_type')),
            ('key_value', _('key_value'))
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
            self.basic_labels[field] = label_widget  # 存储标签引用
            
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
        self.params_frame = ttk.LabelFrame(self.scrollable_frame, text=_("editable_params"))
        
        # 参数工具栏
        param_toolbar = ttk.Frame(self.params_frame)
        param_toolbar.pack(fill=tk.X, padx=10, pady=5)
        
        self.add_param_btn = ttk.Button(param_toolbar, text=_('add_parameter'), 
                  command=self._add_param)
        self.add_param_btn.pack(side=tk.LEFT)
        
        self.refresh_btn = ttk.Button(param_toolbar, text=_('menu_refresh'), 
                  command=self._refresh_params)
        self.refresh_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        # 加载提示组件
        self.loading_frame = ttk.Frame(self.params_frame)
        self.loading_label = ttk.Label(self.loading_frame, text=_('loading_params'), 
                                     style='Info.TLabel')
        self.loading_label.pack(pady=10)
        
        self.loading_progress = ttk.Progressbar(self.loading_frame, mode='determinate',
                                              length=200)
        self.loading_progress.pack(pady=(0, 10))
        
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
    
    def _batch_create_params(self, params_data, show_progress=False):
        """批量创建参数控件（分批处理）"""
        batch_size = 10  # 每批处理10个参数
        total_params = len(params_data)
        
        def create_batch(start_index):
            end_index = min(start_index + batch_size, total_params)
            
            # 创建当前批次的参数控件
            for i in range(start_index, end_index):
                param = params_data[i]
                self._create_param_widget_optimized(i, param)
            
            # 更新进度
            if show_progress:
                progress = (end_index / total_params) * 100
                self._update_loading_progress(progress)
            
            # 如果还有更多参数，继续下一批
            if end_index < total_params:
                # 使用after方法避免界面冻结
                self.params_grid_frame.after(10, lambda: create_batch(end_index))
            else:
                # 所有参数创建完成，进行布局
                self._finalize_params_layout(show_progress)
        
        # 开始批量创建
        create_batch(0)
    
    def _finalize_params_layout(self, hide_progress=False):
        """完成参数布局"""
        if hide_progress:
            self._show_loading_hint(False)
        
        # 延迟布局，避免频繁重排
        self.params_grid_frame.after_idle(self._layout_params_grid)
    
    def _layout_params_grid(self):
        """使用网格布局参数控件（优化版）"""
        if not hasattr(self, 'param_widgets') or not self.param_widgets:
            return
        
        # 获取框架宽度（避免强制更新）
        frame_width = self.params_grid_frame.winfo_width()
        if frame_width <= 1:
            frame_width = 800  # 默认宽度
        
        # 计算列数（每列最小350像素）
        columns = max(1, frame_width // 350)
        
        # 批量配置网格
        widgets_to_grid = []
        row = 0
        col = 0
        
        for index, widget_data in self.param_widgets.items():
            frame = widget_data.get('frame')
            if frame and frame.winfo_exists():
                widgets_to_grid.append((frame, row, col))
                
                col += 1
                if col >= columns:
                    col = 0
                    row += 1
        
        # 批量应用网格布局
        for frame, r, c in widgets_to_grid:
            frame.grid(row=r, column=c, sticky='ew', padx=5, pady=5)
        
        # 配置列权重
        for c in range(columns):
            self.params_grid_frame.grid_columnconfigure(c, weight=1)
        
        # 布局完成后强制更新滚动区域
        self._update_scroll_region()
    
    def _update_scroll_region(self):
        """强制更新Canvas滚动区域（修复滚动限制问题）"""
        if hasattr(self, 'canvas') and hasattr(self, 'scrollable_frame'):
            # 强制更新所有待处理的几何变化
            self.scrollable_frame.update_idletasks()
            # 重新配置滚动区域
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            print(f"[滚动区域] 已更新: {self.canvas.bbox('all')}")
    
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
        """加载参数信息（优化版）"""
        print(f"[材质面板调试] 开始加载参数...")
        
        # 暂停界面更新，提高性能
        self.params_grid_frame.update_idletasks = lambda: None
        
        # 清除现有参数控件
        for widget_data in self.param_widgets.values():
            frame = widget_data.get('frame')
            if frame:
                frame.destroy()
        self.param_widgets.clear()

        if not self.current_material:
            print(f"[材质面板调试] 当前材质数据为空")
            # 恢复界面更新
            self.params_grid_frame.update_idletasks = ttk.Frame.update_idletasks
            return

        # 获取参数数据
        params_data = self.current_material.get('params', [])
        print(f"[材质面板调试] 获取到的参数数据类型: {type(params_data)}")
        print(f"[材质面板调试] 参数数量: {len(params_data) if isinstance(params_data, list) else '非列表类型'}")
        
        if isinstance(params_data, list) and len(params_data) > 0:
            print(f"[材质面板调试] 前3个参数:")
            for i, param in enumerate(params_data[:3]):
                print(f"  参数{i+1}: {param.get('name', '无名')} = {param.get('value', '无值')}")
        
        if not isinstance(params_data, list):
            print(f"[材质面板调试] 参数数据不是列表类型，无法显示")
            # 恢复界面更新
            self.params_grid_frame.update_idletasks = ttk.Frame.update_idletasks
            return

        # 如果参数过多，显示进度提示
        show_progress = len(params_data) > 20
        if show_progress:
            self._show_loading_hint(True)
        
        # 批量创建参数控件（分批处理避免界面冻结）
        self._batch_create_params(params_data, show_progress)
        
        # 恢复界面更新
        self.params_grid_frame.update_idletasks = ttk.Frame.update_idletasks
    
    def _show_loading_hint(self, show=True):
        """显示或隐藏加载提示"""
        if show:
            self.loading_frame.pack(expand=True, pady=50)
            self.loading_progress['value'] = 0
        else:
            self.loading_frame.pack_forget()
    
    def _update_loading_progress(self, progress):
        """更新加载进度"""
        if hasattr(self, 'loading_progress'):
            self.loading_progress['value'] = progress
            self.loading_label.config(text=f"{_('loading_params')}... {progress:.0f}%")
    
    def _finalize_params_layout(self, hide_progress=False):
        """完成参数布局"""
        if hide_progress:
            self._show_loading_hint(False)
        
        # 延迟布局，避免频繁重排
        self.params_grid_frame.after_idle(self._layout_params_grid)
        
        # 延迟更新滚动区域，确保布局完成后再更新
        self.params_grid_frame.after(150, self._update_scroll_region)
    
    def _batch_create_params(self, params_data, show_progress=False):
        """批量创建参数控件（分批处理 - 优化版）"""
        # 优化：增加批次大小，减少批次数量
        batch_size = 20  # 从10提升到20，减少批次间延迟的累积影响
        total_params = len(params_data)
        
        def create_batch(start_index):
            end_index = min(start_index + batch_size, total_params)
            
            # 创建当前批次的参数控件
            for i in range(start_index, end_index):
                param = params_data[i]
                self._create_param_widget_optimized(i, param)
            
            # 更新进度
            if show_progress:
                progress = (end_index / total_params) * 100
                self._update_loading_progress(progress)
            
            # 如果还有更多参数，继续下一批
            if end_index < total_params:
                # 优化：使用after_idle代替固定延迟，让系统自动调度
                self.params_grid_frame.after_idle(lambda: create_batch(end_index))
            else:
                # 所有参数创建完成，进行布局
                self._finalize_params_layout(show_progress)
        
        # 开始批量创建
        create_batch(0)
    
    def _create_param_widget_optimized(self, index: int, param_data: Dict[str, Any]):
        """创建单个参数控件（优化版）"""
        param_name = param_data.get('name', _('new_parameter').format(n=index + 1))
        param_type = param_data.get('type', 'Float')
        param_value = param_data.get('value', '')
        param_key = param_data.get('key_value', '')
        
        # 缓存常用样式
        if not hasattr(self, '_cached_font'):
            self._cached_font = ('Microsoft YaHei UI', 9)
            self._cached_type_values = ['Float', 'Float2', 'Float3', 'Float4', 'Float5', 'Int', 'Int2', 'Bool']
        
        # 参数容器
        param_frame = ttk.LabelFrame(self.params_grid_frame, 
                                   text=f"{param_name[:30]}")
        
        # 参数类型
        type_frame = ttk.Frame(param_frame)
        type_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(type_frame, text=_('type_label'), font=self._cached_font).pack(side=tk.LEFT)
        type_var = tk.StringVar(value=param_type)
        type_combo = ttk.Combobox(type_frame, textvariable=type_var, 
                                font=self._cached_font,
                                values=self._cached_type_values,
                                state='readonly')
        type_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # 参数Key值（只读）
        key_frame = ttk.Frame(param_frame)
        key_frame.pack(fill=tk.X, padx=5, pady=2)
        
        key_label = ttk.Label(key_frame, text=_('key_label'), font=self._cached_font)
        key_label.pack(side=tk.LEFT)
        key_var = tk.StringVar(value=str(param_key))
        key_entry = ttk.Entry(key_frame, textvariable=key_var, 
                            font=self._cached_font, state='readonly')
        key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # 参数名称
        name_frame = ttk.Frame(param_frame)
        name_frame.pack(fill=tk.X, padx=5, pady=2)
        
        name_label = ttk.Label(name_frame, text=_('name_label'), font=self._cached_font)
        name_label.pack(side=tk.LEFT)
        name_var = tk.StringVar(value=param_name)
        name_entry = ttk.Entry(name_frame, textvariable=name_var, 
                             font=self._cached_font)
        name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # 参数值编辑区域
        value_frame = ttk.Frame(param_frame)
        value_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # 判断参数类型
        is_array = param_type in ['Float2', 'Float3', 'Float4', 'Float5', 'Int2']
        is_bool = param_type == 'Bool'
        
        if is_bool:
            # Bool类型：使用复选框
            ttk.Label(value_frame, text=_('value_label_short'), font=self._cached_font).pack(side=tk.LEFT)
            value_var = tk.StringVar(value=str(param_value).lower() if param_value else 'false')
            bool_combo = ttk.Combobox(value_frame, textvariable=value_var,
                                    font=self._cached_font,
                                    values=['true', 'false'],
                                    state='readonly', width=10)
            bool_combo.pack(side=tk.LEFT, padx=(5, 0))
            value_vars = None
        elif is_array:
            # 数组类型：横向分布编辑
            array_values = self._parse_array_value_correctly(param_value)
            
            ttk.Label(value_frame, text=_('array_values_label').format(count=len(array_values)), 
                     font=self._cached_font).pack(anchor='w')
            
            # 水平排列的输入框
            array_container = ttk.Frame(value_frame)
            array_container.pack(fill=tk.X, pady=(2, 0))
            
            value_vars = []
            for i, val in enumerate(array_values):
                col_frame = ttk.Frame(array_container)
                col_frame.pack(side=tk.LEFT, padx=(0, 5))
                
                ttk.Label(col_frame, text=f"[{i}]", font=('Microsoft YaHei UI', 8)).pack()
                var = tk.StringVar(value=str(val).strip())
                entry = ttk.Entry(col_frame, textvariable=var, 
                                font=self._cached_font, width=8)
                entry.pack()
                value_vars.append(var)
            
            value_var = None  # 数组模式不使用单一变量
        else:
            # 单值类型：普通编辑
            ttk.Label(value_frame, text=_('value_label_short'), font=self._cached_font).pack(side=tk.LEFT)
            value_var = tk.StringVar(value=str(param_value) if param_value else '')
            value_entry = ttk.Entry(value_frame, textvariable=value_var, 
                                  font=self._cached_font)
            value_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
            value_vars = None
        
        # 操作按钮
        button_frame = ttk.Frame(param_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text=_('delete_button'), 
                  command=lambda idx=index: self._remove_param(idx)).pack(side=tk.RIGHT)
        
        # 保存控件引用
        self.param_widgets[index] = {
            'frame': param_frame,
            'type_var': type_var,
            'name_var': name_var,
            'key_var': key_var,
            'value_var': value_var,
            'value_vars': value_vars,  # 数组值列表
            'is_array': is_array,
            'is_bool': is_bool,
            'data': param_data
        }
    
    def _create_param_widget(self, index: int, param_data: Dict[str, Any]):
        """创建单个参数控件（兼容性保持）"""
        return self._create_param_widget_optimized(index, param_data)
        
        # 参数Key值（只读）
        key_frame = ttk.Frame(param_frame)
        key_frame.pack(fill=tk.X, padx=5, pady=2)
        
        key_label = ttk.Label(key_frame, text=_('key_label'), font=('Microsoft YaHei UI', 9))
        key_label.pack(side=tk.LEFT)
        key_var = tk.StringVar(value=str(param_key))
        key_entry = ttk.Entry(key_frame, textvariable=key_var, 
                            font=('Microsoft YaHei UI', 9), state='readonly')
        key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # 参数名称
        name_frame = ttk.Frame(param_frame)
        name_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.name_label = ttk.Label(name_frame, text=_('name_label'), font=('Microsoft YaHei UI', 9))
        self.name_label.pack(side=tk.LEFT)
        name_var = tk.StringVar(value=param_name)
        name_entry = ttk.Entry(name_frame, textvariable=name_var, 
                             font=('Microsoft YaHei UI', 9))
        name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # 参数值编辑区域
        value_frame = ttk.Frame(param_frame)
        value_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # 判断参数类型
        is_array = param_type in ['Float2', 'Float3', 'Float4', 'Float5', 'Int2']
        is_bool = param_type == 'Bool'
        
        if is_bool:
            # Bool类型：使用复选框
            ttk.Label(value_frame, text=_('value_label_short'), font=('Microsoft YaHei UI', 9)).pack(side=tk.LEFT)
            value_var = tk.StringVar(value=str(param_value).lower() if param_value else 'false')
            bool_combo = ttk.Combobox(value_frame, textvariable=value_var,
                                    font=('Microsoft YaHei UI', 9),
                                    values=['true', 'false'],
                                    state='readonly', width=10)
            bool_combo.pack(side=tk.LEFT, padx=(5, 0))
            value_vars = None
        elif is_array:
            # 数组类型：横向分布编辑
            array_values = self._parse_array_value_correctly(param_value)
            
            ttk.Label(value_frame, text=_('array_values_label').format(count=len(array_values)), 
                     font=('Microsoft YaHei UI', 9)).pack(anchor='w')
            
            # 水平排列的输入框
            array_container = ttk.Frame(value_frame)
            array_container.pack(fill=tk.X, pady=(2, 0))
            
            value_vars = []
            for i, val in enumerate(array_values):
                col_frame = ttk.Frame(array_container)
                col_frame.pack(side=tk.LEFT, padx=(0, 5))
                
                ttk.Label(col_frame, text=f"[{i}]", font=('Microsoft YaHei UI', 8)).pack()
                var = tk.StringVar(value=str(val).strip())
                entry = ttk.Entry(col_frame, textvariable=var, 
                                font=('Microsoft YaHei UI', 9), width=8)
                entry.pack()
                value_vars.append(var)
            
            value_var = None  # 数组模式不使用单一变量
        else:
            # 单值类型：普通编辑
            ttk.Label(value_frame, text=_('value_label_short'), font=('Microsoft YaHei UI', 9)).pack(side=tk.LEFT)
            value_var = tk.StringVar(value=str(param_value) if param_value else '')
            value_entry = ttk.Entry(value_frame, textvariable=value_var, 
                                  font=('Microsoft YaHei UI', 9))
            value_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
            value_vars = None
        
        # 操作按钮
        button_frame = ttk.Frame(param_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text=_('delete_button'), 
                  command=lambda idx=index: self._remove_param(idx)).pack(side=tk.RIGHT)
        
        # 保存控件引用
        self.param_widgets[index] = {
            'frame': param_frame,
            'type_var': type_var,
            'name_var': name_var,
            'key_var': key_var,
            'value_var': value_var,
            'value_vars': value_vars,  # 数组值列表
            'is_array': is_array,
            'is_bool': is_bool,
            'data': param_data
        }

    def _parse_array_value_correctly(self, value):
        """正确解析数组值"""
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
            # 如果不是数组格式，直接返回
            return [value_str] if value_str else ['0.0']
        
        # 如果是列表格式（来自XML）
        if isinstance(value, list):
            # 直接返回列表中的数值，去除特殊字符
            result = []
            for item in value:
                item_str = str(item).strip()
                if item_str and item_str not in ['[', ']', ',', ' ']:
                    result.append(item_str)
            return result if result else ['0.0']
        
        return [str(value)]
    
    def _add_param(self):
        """添加新参数"""
        if not hasattr(self, 'param_widgets'):
            self.param_widgets = {}
        
        # 计算新索引（找到最大索引+1）
        new_index = max(self.param_widgets.keys()) + 1 if self.param_widgets else 0
        
        # 创建新参数数据
        new_param = {
            'type': 'float',
            'name': _('new_parameter').format(n=new_index + 1),
            'value': '0.0'
        }
        
        # 创建控件
        self._create_param_widget(new_index, new_param)
        
        # 重新布局
        self._layout_params_grid()
        
        # 更新滚动区域
        self.params_grid_frame.after(50, self._update_scroll_region)
    
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
        
        # 更新滚动区域
        self.params_grid_frame.after(50, self._update_scroll_region)
    
    def _refresh_params(self):
        """刷新参数显示"""
        self._load_params()
    
    def _export_material(self):
        """导出材质"""
        if self.current_material and self.on_material_export:
            # 检查是否需要添加到自动封包队列
            add_to_autopack = self.autopack_var.get() if hasattr(self, 'autopack_var') else False
            # 调用导出方法，传递自动封包选项
            self.on_material_export(add_to_autopack=add_to_autopack)
    
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
        
        # 更新参数（保持原始顺序）
        params = []
        # 按索引顺序处理参数，保持原始顺序
        for index in sorted(self.param_widgets.keys()):
            widget_data = self.param_widgets[index]
            param = {
                'type': widget_data['type_var'].get(),
                'name': widget_data['name_var'].get(),
                'key': widget_data['key_var'].get()  # 保持原始Key值
            }
            
            # 处理参数值（Bool、数组或单值）
            if widget_data.get('is_bool') and widget_data.get('value_var'):
                # Bool类型：确保值为true/false
                bool_val = widget_data['value_var'].get().lower()
                param['value'] = bool_val if bool_val in ['true', 'false'] else 'false'
            elif widget_data.get('is_array') and widget_data.get('value_vars'):
                # 数组模式：收集所有数组元素为列表
                array_values = [var.get() for var in widget_data['value_vars']]
                param['value'] = array_values  # 保存为列表，导出时转换
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
    
    def update_language(self):
        """更新界面语言"""
        try:
            # 更新标题
            if hasattr(self, 'title_label'):
                self.title_label.config(text=_("material_info_panel"))
            
            # 更新基本信息标签框
            if hasattr(self, 'basic_frame'):
                self.basic_frame.config(text=_("basic_info"))
            
            # 更新基本信息字段标签
            if hasattr(self, 'basic_labels'):
                field_translations = {
                    'filename': _('material_name'),
                    'shader_path': _('shader_path'),
                    'source_path': _('material_file_path'),
                    'compression': _('compression_type'),
                    'key_value': _('key_value')  # 修复字段名
                }
                for field, label_widget in self.basic_labels.items():
                    if field in field_translations:
                        label_widget.config(text=f"{field_translations[field]}:")
            
            # 更新可编辑参数标签框
            if hasattr(self, 'params_frame'):
                self.params_frame.config(text=_("editable_params"))
            
            # 更新按钮文本
            if hasattr(self, 'add_param_btn'):
                self.add_param_btn.config(text=_("add_parameter"))
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.config(text=_("menu_refresh"))
            if hasattr(self, 'save_as_btn'):
                self.save_as_btn.config(text=_('save_as_button'))
            if hasattr(self, 'autopack_check'):
                self.autopack_check.config(text=_('add_to_autopack'))
            
            # 更新空状态提示
            if hasattr(self, 'empty_label'):
                self.empty_label.config(text=_("select_material_detail_hint"))
                
            # 重新加载当前材质以更新参数标签
            if self.current_material:
                current_material = self.current_material
                self.current_material = None  # 清空当前材质
                self.display_material(current_material)  # 重新显示以更新所有标签
                
        except Exception as e:
            print(f"Error updating material panel language: {e}")