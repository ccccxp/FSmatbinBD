"""
FSmatbinBD 版本信息管理
从 version.json 配置文件动态读取版本信息
用于动态标题栏、打包配置、关于对话框等
"""

import json
import os
from typing import Dict, Any, Optional

# 尝试导入资源路径模块（打包后使用）
try:
    from src.utils.resource_path import get_base_path
except ImportError:
    def get_base_path():
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _find_version_file() -> Optional[str]:
    """查找版本文件"""
    possible_paths = [
        # 开发环境 - 项目根目录
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'version.json'),
        # 打包环境 - 使用 resource_path
        os.path.join(get_base_path(), 'version.json'),
        # 打包环境 - internal 目录
        os.path.join(get_base_path(), 'internal', 'version.json'),
        # 当前工作目录
        os.path.join(os.getcwd(), 'version.json'),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None


def _load_version_data() -> Dict[str, Any]:
    """加载版本信息"""
    version_file = _find_version_file()
    
    if version_file and os.path.exists(version_file):
        try:
            with open(version_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"警告: 无法读取版本文件: {e}")
    
    # 默认版本信息
    return {
        "version": "1.0.0",
        "build_date": "2026-01-04",
        "app_name": "FSMatbinBD",
        "description": "FS材质库查询工具 - FromSoftware Material Database Browser",
        "author": "FSMatbinBD Team",
        "repository": ""
    }


# 加载版本数据
_VERSION_DATA = _load_version_data()

# 主版本信息（从配置文件读取）
VERSION = _VERSION_DATA.get('version', '1.0.0')
BUILD_DATE = _VERSION_DATA.get('build_date', '')
APP_NAME = _VERSION_DATA.get('app_name', 'FSMatbinBD')
APP_FULL_NAME = _VERSION_DATA.get('description', 'FromSoftware Material Binary Database')
AUTHOR = _VERSION_DATA.get('author', 'FSMatbinBD Team')
REPOSITORY = _VERSION_DATA.get('repository', '')

# 解析版本号
_version_parts = VERSION.split('.')
VERSION_MAJOR = int(_version_parts[0]) if len(_version_parts) > 0 else 1
VERSION_MINOR = int(_version_parts[1]) if len(_version_parts) > 1 else 0
VERSION_PATCH = int(_version_parts[2]) if len(_version_parts) > 2 else 0

# 版本描述
VERSION_NAME = "Card UI Edition"
COPYRIGHT = f"© 2024-2026 {AUTHOR}"

# 完整版本字符串
FULL_VERSION = f"v{VERSION} ({BUILD_DATE})"


def get_window_title(library_name: str = None) -> str:
    """
    生成动态窗口标题
    
    Args:
        library_name: 当前打开的库名称
        
    Returns:
        格式化的窗口标题字符串
    """
    base_title = f"{APP_NAME} V{VERSION}"
    
    if library_name:
        return f"{base_title} - [{library_name}]"
    else:
        return base_title


def get_version_info() -> dict:
    """
    返回完整的版本信息字典
    
    Returns:
        包含所有版本信息的字典
    """
    return {
        "name": APP_NAME,
        "full_name": APP_FULL_NAME,
        "version": VERSION,
        "version_name": VERSION_NAME,
        "build_date": BUILD_DATE,
        "author": AUTHOR,
        "copyright": COPYRIGHT,
        "repository": REPOSITORY,
        "full_version": FULL_VERSION,
    }


def get_version() -> str:
    """获取版本号"""
    return VERSION


def get_full_version() -> str:
    """获取完整版本字符串"""
    return FULL_VERSION


def get_build_date() -> str:
    """获取构建日期"""
    return BUILD_DATE


def reload_version():
    """重新加载版本信息（用于动态更新）"""
    global _VERSION_DATA, VERSION, BUILD_DATE, APP_NAME, APP_FULL_NAME, AUTHOR, REPOSITORY
    global VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH, FULL_VERSION, COPYRIGHT
    
    _VERSION_DATA = _load_version_data()
    VERSION = _VERSION_DATA.get('version', '1.0.0')
    BUILD_DATE = _VERSION_DATA.get('build_date', '')
    APP_NAME = _VERSION_DATA.get('app_name', 'FSMatbinBD')
    APP_FULL_NAME = _VERSION_DATA.get('description', 'FromSoftware Material Binary Database')
    AUTHOR = _VERSION_DATA.get('author', 'FSMatbinBD Team')
    REPOSITORY = _VERSION_DATA.get('repository', '')
    
    _version_parts = VERSION.split('.')
    VERSION_MAJOR = int(_version_parts[0]) if len(_version_parts) > 0 else 1
    VERSION_MINOR = int(_version_parts[1]) if len(_version_parts) > 1 else 0
    VERSION_PATCH = int(_version_parts[2]) if len(_version_parts) > 2 else 0
    
    COPYRIGHT = f"© 2024-2026 {AUTHOR}"
    FULL_VERSION = f"v{VERSION} ({BUILD_DATE})"


# 版本字符串 (用于打包)
__version__ = VERSION
