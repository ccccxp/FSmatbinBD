#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深色标题栏工具模块
为所有弹窗添加Windows深色标题栏支持
"""

import sys
from PySide6.QtCore import QTimer
from typing import Optional
from PySide6.QtWidgets import QDialog, QWidget


def apply_dark_titlebar_to_dialog(dialog: QDialog, delay_ms: int = 100):
    """
    为QDialog添加深色标题栏（Windows 10/11）
    
    Args:
        dialog: QDialog实例
        delay_ms: 延迟应用的毫秒数（确保窗口句柄已创建）
    """
    if sys.platform != 'win32':
        return
    
    def apply():
        try:
            import ctypes
            hwnd = int(dialog.winId())
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            value = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(value),
                ctypes.sizeof(value)
            )
        except Exception as e:
            # 静默失败，不影响主功能
            pass
    
    QTimer.singleShot(delay_ms, apply)


class DarkTitleBarMixin:
    """
    深色标题栏Mixin类
    可以混入任何QDialog子类以自动应用深色标题栏
    
    使用方法:
        class MyDialog(DarkTitleBarMixin, QDialog):
            def __init__(self, parent=None):
                super().__init__(parent)
                self._init_dark_titlebar()  # 调用此方法启用深色标题栏
    """
    
    def _init_dark_titlebar(self):
        """初始化深色标题栏"""
        if isinstance(self, QDialog):
            apply_dark_titlebar_to_dialog(self)


def apply_dark_titlebar_to_window(widget: QWidget, delay_ms: int = 100):
    """
    为任意QWidget窗口添加深色标题栏
    
    Args:
        widget: QWidget实例（必须是顶层窗口）
        delay_ms: 延迟应用的毫秒数
    """
    if sys.platform != 'win32':
        return
    
    def apply():
        try:
            import ctypes
            hwnd = int(widget.winId())
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            value = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(value),
                ctypes.sizeof(value)
            )
        except Exception:
            pass
    
    QTimer.singleShot(delay_ms, apply)
