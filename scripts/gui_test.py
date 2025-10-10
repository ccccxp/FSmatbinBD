#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速 GUI 启动测试 - 验证本地化界面组件是否正常工作
"""

import tkinter as tk
import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.i18n import language_manager, _
from src.gui.main_window import MaterialDatabaseApp

def quick_gui_test():
    """快速启动 GUI 进行本地化测试"""
    # 创建根窗口
    root = tk.Tk()
    
    # 初始化应用
    try:
        app = MaterialDatabaseApp(root)
        
        # 显示一个简单的状态消息
        print("GUI 启动成功！")
        print(f"当前语言: {language_manager.current_language}")
        print(f"应用标题: {_('app_title')}")
        print(f"版本: {_('version')}")
        
        # 注意：这将启动 GUI 主循环，用户需要手动关闭窗口
        print("正在启动 GUI 界面...")
        print("注意：关闭窗口后脚本将结束")
        
        root.mainloop()
        
    except Exception as e:
        print(f"GUI 启动失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理
        try:
            if 'app' in locals():
                app.cleanup()
        except:
            pass

if __name__ == "__main__":
    quick_gui_test()