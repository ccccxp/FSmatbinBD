#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资源路径辅助模块 - 支持 PyInstaller 打包后的路径解析

打包后的应用程序资源文件路径与开发环境不同：
- 开发环境：相对于项目根目录
- 打包环境：相对于可执行文件所在目录下的 internal 子目录（使用 contents_directory='internal'）
"""

import os
import sys


def get_base_path() -> str:
    """
    获取应用程序基础路径（资源文件所在的根目录）
    
    - 开发环境：返回项目根目录
    - PyInstaller 打包后（onedir + contents_directory='internal'）：返回 internal 子目录
    - PyInstaller 打包后（onefile）：返回临时解压目录 _MEIPASS
    
    Returns:
        基础路径字符串
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的环境
        if hasattr(sys, '_MEIPASS'):
            # onefile 模式，使用 _MEIPASS 临时目录
            return sys._MEIPASS
        else:
            # onedir 模式，检查是否使用了 contents_directory='internal'
            exe_dir = os.path.dirname(sys.executable)
            internal_dir = os.path.join(exe_dir, 'internal')
            if os.path.isdir(internal_dir):
                # 使用了 contents_directory='internal'
                return internal_dir
            else:
                # 没有使用 contents_directory
                return exe_dir
    else:
        # 开发环境，返回项目根目录
        # 假设此文件位于 src/utils/resource_path.py
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_exe_dir() -> str:
    """
    获取可执行文件所在目录（用于用户数据存储）
    
    Returns:
        可执行文件所在目录
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return get_base_path()


def get_resource_path(relative_path: str) -> str:
    """
    获取资源文件的绝对路径（支持打包环境）
    
    Args:
        relative_path: 相对于项目根目录的路径，如 'src/gui_qt/assets/app_icon.png'
        
    Returns:
        资源文件的绝对路径
    """
    base_path = get_base_path()
    full_path = os.path.join(base_path, relative_path)
    return os.path.normpath(full_path)


def get_data_path(relative_path: str = "") -> str:
    """
    获取数据目录路径（用户数据，如数据库）
    
    打包后，数据文件在 internal 子目录中（只读），
    但用户生成的数据应该放在可执行文件同级目录
    
    Args:
        relative_path: 相对于数据目录的路径
        
    Returns:
        数据文件的绝对路径
    """
    # 打包环境和开发环境都使用 get_base_path，
    # 因为数据文件被打包到 internal 目录中
    base_path = get_base_path()
    
    if relative_path:
        return os.path.normpath(os.path.join(base_path, relative_path))
    return base_path


def get_user_data_path(relative_path: str = "") -> str:
    """
    获取用户数据目录路径（用于存储用户生成的数据）
    
    打包后，用户数据应放在可执行文件同级目录（可写）
    
    Args:
        relative_path: 相对于用户数据目录的路径
        
    Returns:
        用户数据文件的绝对路径
    """
    base_path = get_exe_dir()
    
    if relative_path:
        return os.path.normpath(os.path.join(base_path, relative_path))
    return base_path


def get_tools_path(tool_name: str = "") -> str:
    """
    获取工具目录路径（如 WitchyBND）
    
    Args:
        tool_name: 工具名称或相对路径
        
    Returns:
        工具的绝对路径
    """
    # 工具被打包到 internal/tools 目录中
    tools_dir = get_resource_path("tools")
    if tool_name:
        return os.path.normpath(os.path.join(tools_dir, tool_name))
    return tools_dir


def get_assets_path(asset_name: str = "") -> str:
    """
    获取 GUI 资源文件路径
    
    Args:
        asset_name: 资源文件名
        
    Returns:
        资源文件的绝对路径
    """
    assets_dir = get_resource_path("src/gui_qt/assets")
    if asset_name:
        return os.path.normpath(os.path.join(assets_dir, asset_name))
    return assets_dir


def get_database_path(db_name: str = "materials.db") -> str:
    """
    获取数据库文件路径
    
    打包后数据库位于 internal/data/databases/ 目录
    
    Args:
        db_name: 数据库文件名
        
    Returns:
        数据库文件的绝对路径
    """
    return get_data_path(os.path.join("data", "databases", db_name))


def ensure_data_dirs():
    """
    确保用户数据目录存在（打包后首次运行时需要创建）
    
    注意：这些目录在用户数据目录下创建，而不是在 internal 目录下
    """
    user_base = get_user_data_path()
    dirs_to_create = [
        os.path.join(user_base, "temp"),
        os.path.join(user_base, "output"),
        os.path.join(user_base, "logs"),
    ]
    
    for dir_path in dirs_to_create:
        os.makedirs(dir_path, exist_ok=True)


# 缓存基础路径
_BASE_PATH = None

def get_cached_base_path() -> str:
    """获取缓存的基础路径（性能优化）"""
    global _BASE_PATH
    if _BASE_PATH is None:
        _BASE_PATH = get_base_path()
    return _BASE_PATH


# 调试信息
def print_path_info():
    """打印路径调试信息"""
    print("=" * 50)
    print("资源路径调试信息:")
    print(f"  frozen: {getattr(sys, 'frozen', False)}")
    print(f"  _MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}")
    print(f"  sys.executable: {sys.executable}")
    print(f"  base_path: {get_base_path()}")
    print(f"  data_path: {get_data_path()}")
    print(f"  assets_path: {get_assets_path()}")
    print(f"  database_path: {get_database_path()}")
    print(f"  tools_path: {get_tools_path()}")
    print("=" * 50)


if __name__ == "__main__":
    print_path_info()
