#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
现代黑暗主题配置
"""

import tkinter as tk
from tkinter import ttk

class ModernDarkTheme:
    """现代黑暗主题"""
    
    # 颜色配置
    COLORS = {
        'bg_primary': '#1e1e1e',      # 主背景色
        'bg_secondary': '#2d2d2d',    # 次要背景色
        'bg_tertiary': '#3c3c3c',     # 第三级背景色
        'fg_primary': '#ffffff',      # 主文字色
        'fg_secondary': '#cccccc',    # 次要文字色
        'fg_disabled': '#808080',     # 禁用文字色
        'accent_blue': '#007acc',     # 蓝色强调色
        'accent_green': '#16a085',    # 绿色强调色
        'accent_red': '#e74c3c',      # 红色强调色
        'accent_orange': '#f39c12',   # 橙色强调色
        'border': '#555555',          # 边框色
        'hover': '#404040',           # 悬停色
        'selected': '#094771',        # 选中色
    }
    
    @classmethod
    def apply_theme(cls, root):
        """应用现代黑暗主题"""
        style = ttk.Style()
        
        # 设置主题
        style.theme_use('clam')
        
        # 配置根窗口
        root.configure(bg=cls.COLORS['bg_primary'])
        
        # 设置默认字体（改善文字清晰度）
        default_font = ('Microsoft YaHei UI', 9)
        root.option_add('*Font', default_font)
        
        # 配置基本样式
        cls._configure_basic_styles(style)
        cls._configure_button_styles(style)
        cls._configure_frame_styles(style)
        cls._configure_entry_styles(style)
        cls._configure_treeview_styles(style)
        cls._configure_listbox_styles(style)
        cls._configure_text_styles(style)
        cls._configure_label_styles(style)
        
    @classmethod
    def _configure_basic_styles(cls, style):
        """配置基本样式"""
        style.configure('.',
                       background=cls.COLORS['bg_primary'],
                       foreground=cls.COLORS['fg_primary'],
                       bordercolor=cls.COLORS['border'],
                       darkcolor=cls.COLORS['bg_secondary'],
                       lightcolor=cls.COLORS['bg_tertiary'],
                       insertcolor=cls.COLORS['fg_primary'],
                       selectbackground=cls.COLORS['selected'],
                       selectforeground=cls.COLORS['fg_primary'],
                       fieldbackground=cls.COLORS['bg_secondary'],
                       font=('Microsoft YaHei UI', 9))
    
    @classmethod
    def _configure_button_styles(cls, style):
        """配置按钮样式"""
        # 默认按钮
        style.configure('TButton',
                       background=cls.COLORS['bg_secondary'],
                       foreground=cls.COLORS['fg_primary'],
                       borderwidth=1,
                       focuscolor='none',
                       relief='flat')
        
        style.map('TButton',
                 background=[('active', cls.COLORS['hover']),
                            ('pressed', cls.COLORS['bg_tertiary'])])
        
        # 蓝色按钮（主要操作）
        style.configure('Primary.TButton',
                       background=cls.COLORS['accent_blue'],
                       foreground=cls.COLORS['fg_primary'],
                       borderwidth=0,
                       focuscolor='none',
                       relief='flat')
        
        style.map('Primary.TButton',
                 background=[('active', '#0086d1'),
                            ('pressed', '#005a9e')])
        
        # 绿色按钮（成功操作）
        style.configure('Success.TButton',
                       background=cls.COLORS['accent_green'],
                       foreground=cls.COLORS['fg_primary'],
                       borderwidth=0,
                       focuscolor='none',
                       relief='flat')
        
        style.map('Success.TButton',
                 background=[('active', '#1abc9c'),
                            ('pressed', '#138d75')])
        
        # 红色按钮（危险操作）
        style.configure('Danger.TButton',
                       background=cls.COLORS['accent_red'],
                       foreground=cls.COLORS['fg_primary'],
                       borderwidth=0,
                       focuscolor='none',
                       relief='flat')
        
        style.map('Danger.TButton',
                 background=[('active', '#ec7063'),
                            ('pressed', '#c0392b')])
        
        # 淡黄色按钮（解析DCX）
        style.configure('LightYellow.TButton',
                       background='#f4d03f',  # 淡黄色
                       foreground='#2c3e50',  # 深色文字
                       borderwidth=0,
                       focuscolor='none',
                       relief='flat')
        
        style.map('LightYellow.TButton',
                 background=[('active', '#f7dc6f'),
                            ('pressed', '#f1c40f')])
        
        # 橙色按钮（自动封包）
        style.configure('Orange.TButton',
                       background='#e67e22',  # 橙色
                       foreground=cls.COLORS['fg_primary'],
                       borderwidth=0,
                       focuscolor='none',
                       relief='flat')
        
        style.map('Orange.TButton',
                 background=[('active', '#eb984e'),
                            ('pressed', '#d35400')])
    
    @classmethod
    def _configure_frame_styles(cls, style):
        """配置框架样式"""
        style.configure('TFrame',
                       background=cls.COLORS['bg_primary'],
                       borderwidth=0)
        
        style.configure('TLabelFrame',
                       background=cls.COLORS['bg_primary'],
                       foreground=cls.COLORS['fg_primary'],
                       borderwidth=1,
                       relief='solid',
                       bordercolor=cls.COLORS['border'])
        
        style.configure('TLabelFrame.Label',
                       background=cls.COLORS['bg_primary'],
                       foreground='#66b3ff',  # 浅蓝色标题
                       font=('Microsoft YaHei UI', 12, 'bold'))  # 增加到12号字体
    
    @classmethod
    def _configure_entry_styles(cls, style):
        """配置输入框样式"""
        style.configure('TEntry',
                       fieldbackground=cls.COLORS['bg_secondary'],
                       background=cls.COLORS['bg_secondary'],
                       foreground=cls.COLORS['fg_primary'],
                       borderwidth=1,
                       bordercolor=cls.COLORS['border'],
                       lightcolor=cls.COLORS['border'],
                       darkcolor=cls.COLORS['border'],
                       insertcolor=cls.COLORS['fg_primary'])
        
        style.map('TEntry',
                 bordercolor=[('focus', cls.COLORS['accent_blue'])],
                 lightcolor=[('focus', cls.COLORS['accent_blue'])],
                 darkcolor=[('focus', cls.COLORS['accent_blue'])])
        
        # 组合框
        style.configure('TCombobox',
                       fieldbackground=cls.COLORS['bg_secondary'],
                       background=cls.COLORS['bg_secondary'],
                       foreground=cls.COLORS['fg_primary'],
                       borderwidth=1,
                       arrowcolor=cls.COLORS['fg_primary'])
        
        style.map('TCombobox',
                 fieldbackground=[('readonly', cls.COLORS['bg_secondary'])],
                 bordercolor=[('focus', cls.COLORS['accent_blue'])])
    
    @classmethod
    def _configure_treeview_styles(cls, style):
        """配置树形视图样式"""
        style.configure('Treeview',
                       background=cls.COLORS['bg_secondary'],
                       foreground=cls.COLORS['fg_primary'],
                       fieldbackground=cls.COLORS['bg_secondary'],
                       borderwidth=1,
                       bordercolor=cls.COLORS['border'])
        
        style.configure('Treeview.Heading',
                       background=cls.COLORS['bg_tertiary'],
                       foreground=cls.COLORS['fg_primary'],
                       borderwidth=1,
                       bordercolor=cls.COLORS['border'])
        
        style.map('Treeview',
                 background=[('selected', cls.COLORS['selected'])],
                 foreground=[('selected', cls.COLORS['fg_primary'])])
        
        style.map('Treeview.Heading',
                 background=[('active', cls.COLORS['hover'])])
    
    @classmethod
    def _configure_listbox_styles(cls, style):
        """配置列表框样式（需要特殊处理）"""
        pass  # Listbox 不使用 ttk，需要单独配置
    
    @classmethod
    def _configure_text_styles(cls, style):
        """配置文本样式"""
        style.configure('TText',
                       background=cls.COLORS['bg_secondary'],
                       foreground=cls.COLORS['fg_primary'],
                       borderwidth=1,
                       bordercolor=cls.COLORS['border'])
    
    @classmethod
    def _configure_label_styles(cls, style):
        """配置标签样式"""
        style.configure('TLabel',
                       background=cls.COLORS['bg_primary'],
                       foreground=cls.COLORS['fg_primary'])
        
        # 标题样式
        style.configure('Heading.TLabel',
                       background=cls.COLORS['bg_primary'],
                       foreground=cls.COLORS['fg_primary'],
                       font=('Microsoft YaHei UI', 12, 'bold'))
        
        # 大标题样式（浅蓝色，更醒目）
        style.configure('Title.TLabel',
                       background=cls.COLORS['bg_primary'],
                       foreground='#4da6ff',  # 浅蓝色
                       font=('Microsoft YaHei UI', 16, 'bold'))  # 增加到16号字体
        
        # 子标题样式
        style.configure('Subtitle.TLabel',
                       background=cls.COLORS['bg_primary'],
                       foreground='#66b3ff',  # 更浅的蓝色
                       font=('Microsoft YaHei UI', 11, 'bold'))
        
        # 信息样式
        style.configure('Info.TLabel',
                       background=cls.COLORS['bg_primary'],
                       foreground=cls.COLORS['fg_secondary'],
                       font=('Microsoft YaHei UI', 9))
    
    @classmethod
    def configure_listbox(cls, listbox):
        """单独配置 Listbox 样式"""
        listbox.configure(
            background=cls.COLORS['bg_secondary'],
            foreground=cls.COLORS['fg_primary'],
            selectbackground=cls.COLORS['selected'],
            selectforeground=cls.COLORS['fg_primary'],
            borderwidth=1,
            relief='solid',
            highlightcolor=cls.COLORS['accent_blue'],
            highlightbackground=cls.COLORS['border'],
            highlightthickness=1
        )
    
    @classmethod
    def configure_text(cls, text_widget):
        """单独配置 Text 样式"""
        text_widget.configure(
            background=cls.COLORS['bg_secondary'],
            foreground=cls.COLORS['fg_primary'],
            insertbackground=cls.COLORS['fg_primary'],
            selectbackground=cls.COLORS['selected'],
            selectforeground=cls.COLORS['fg_primary'],
            borderwidth=1,
            relief='solid',
            highlightcolor=cls.COLORS['accent_blue'],
            highlightbackground=cls.COLORS['border'],
            highlightthickness=1
        )