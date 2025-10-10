#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3D材质库查询程序 - 主程序
作者: GitHub Copilot
日期: 2024年
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.gui.main_window import MaterialDatabaseApp
from src.core.i18n import language_manager, _

def main():
    """主程序入口"""
    try:
        # 初始化语言管理器
        lang_manager = language_manager
        
        # 创建主窗口
        root = tk.Tk()
        root.title(_("app_title") + " " + _("version"))
        
        # 设置窗口图标和样式
        root.configure(bg='#f0f0f0')
        
        # 创建应用程序实例
        app = MaterialDatabaseApp(root)
        
        # 设置窗口关闭事件
        def on_closing():
            if messagebox.askokcancel(_('menu_exit'), _('confirm_exit_message')):
                app.cleanup()
                root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        # 启动主循环
        root.mainloop()
        
    except Exception as e:
        messagebox.showerror(_("error"), f"Startup failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()