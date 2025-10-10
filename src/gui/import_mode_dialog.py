#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导入模式选择对话框
"""

import tkinter as tk
from tkinter import ttk
from src.core.i18n import _

class ImportModeDialog:
    """导入模式选择对话框"""
    
    def __init__(self, parent, title=None):
        self.parent = parent
        self.result = None
        
        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title or _("import_mode_title"))
        self.dialog.geometry("350x400")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.dialog.geometry("+%d+%d" % (
            parent.winfo_rootx() + (parent.winfo_width() // 2) - 175,
            parent.winfo_rooty() + (parent.winfo_height() // 2) - 200
        ))
        
        # 绑定关闭事件
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
        
        # 创建界面
        self._create_ui()
        
        # 等待用户操作
        self.dialog.wait_window()
    
    def _create_ui(self):
        """创建用户界面"""
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text=_("select_import_mode"), 
                               font=('TkDefaultFont', 12, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # 选项框架
        options_frame = ttk.Frame(main_frame)
        options_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # 文件夹导入选项 - 改为按钮
        folder_frame = ttk.LabelFrame(options_frame, text=_("import_mode_folder"), padding=15)
        folder_frame.pack(fill=tk.X, pady=(0, 15))
        
        folder_btn = ttk.Button(folder_frame, text=_("import_mode_folder"), 
                               style='Primary.TButton',
                               command=lambda: self._select_mode("folder"))
        folder_btn.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(folder_frame, text=_('select_folder_with_xml'), 
                 font=('TkDefaultFont', 9)).pack(anchor=tk.W)
        
        # DCX文件导入选项 - 改为按钮
        dcx_frame = ttk.LabelFrame(options_frame, text=_("import_mode_dcx"), padding=15)
        dcx_frame.pack(fill=tk.X, pady=(0, 15))
        
        dcx_btn = ttk.Button(dcx_frame, text=_("import_mode_dcx"), 
                            style='Success.TButton',
                            command=lambda: self._select_mode("dcx"))
        dcx_btn.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(dcx_frame, text=_('select_dcx_for_auto_unpack'), 
                 font=('TkDefaultFont', 9)).pack(anchor=tk.W)
        
        # XML文件导入选项 - 改为按钮
        xml_frame = ttk.LabelFrame(options_frame, text=_("import_mode_xml"), padding=15)
        xml_frame.pack(fill=tk.X, pady=(0, 15))
        
        xml_btn = ttk.Button(xml_frame, text=_("import_mode_xml"), 
                            style='LightYellow.TButton',
                            command=lambda: self._select_mode("xml"))
        xml_btn.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(xml_frame, text=_('select_single_xml'), 
                 font=('TkDefaultFont', 9)).pack(anchor=tk.W)
        
        # 取消按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text=_("cancel"), 
                  command=self._on_cancel).pack(side=tk.RIGHT)
    
    def _select_mode(self, mode):
        """选择模式并直接进入下一步"""
        self.result = mode
        self.dialog.destroy()
    
    def _on_cancel(self):
        """取消按钮点击事件"""
        self.result = None
        self.dialog.destroy()