"""
FSmatbinBD 版本信息管理
用于动态标题栏、打包配置、关于对话框等
"""

# 主版本号 (Major.Minor.Patch)
VERSION_MAJOR = 1
VERSION_MINOR = 1
VERSION_PATCH = 2
VERSION = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"

# 软件名称
APP_NAME = "FSmatbinBD"
APP_FULL_NAME = "FromSoftware Material Binary Database"

# 版本描述
VERSION_NAME = "Card UI Edition"  # 本版本代号
BUILD_DATE = "2025-12-16"

# 开发者信息
AUTHOR = "FSmatbinBD Team"
COPYRIGHT = f"© 2024-2025 {AUTHOR}"

# 窗口标题格式
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

# 完整版本信息 (用于关于对话框)
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
    }

# 版本字符串 (用于打包)
__version__ = VERSION
