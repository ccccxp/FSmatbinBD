# -*- mode: python ; coding: utf-8 -*-
"""
FSmatbinBD PyInstaller Spec 文件
用于将应用打包为 Windows 可执行程序

使用方法:
    pyinstaller FSMatbinBD.spec --noconfirm
"""

import os
import sys
import json
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

# 获取项目根目录（基于 spec 文件位置）
PROJECT_ROOT = os.path.dirname(os.path.abspath(SPEC))

# 确保项目根目录在 sys.path 中，以便 collect_submodules 能正确发现模块
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 从 version.json 读取版本信息
version_file = os.path.join(PROJECT_ROOT, 'version.json')
VERSION = '1.0.0'
APP_NAME = 'FSMatbinBD'
if os.path.exists(version_file):
    try:
        with open(version_file, 'r', encoding='utf-8') as f:
            v_config = json.load(f)
            VERSION = v_config.get('version', '1.0.0')
    except Exception:
        pass

# 定义需要包含的数据文件（使用相对路径）
datas = []

# GUI 资源文件
assets_dir = os.path.join(PROJECT_ROOT, 'src', 'gui_qt', 'assets')
if os.path.exists(assets_dir):
    datas.append((assets_dir, 'src/gui_qt/assets'))

# 主题文件
theme_dir = os.path.join(PROJECT_ROOT, 'src', 'gui_qt', 'theme')
if os.path.exists(theme_dir):
    datas.append((theme_dir, 'src/gui_qt/theme'))

# 工具目录 (WitchyBND)
tools_dir = os.path.join(PROJECT_ROOT, 'tools')
if os.path.exists(tools_dir):
    datas.append((tools_dir, 'tools'))

# 数据目录（包含预置的数据库文件）
data_dir = os.path.join(PROJECT_ROOT, 'data')
if os.path.exists(data_dir):
    datas.append((data_dir, 'data'))

# 配置文件
autopack_config = os.path.join(PROJECT_ROOT, 'autopack_config.json')
if os.path.exists(autopack_config):
    datas.append((autopack_config, '.'))

version_json = os.path.join(PROJECT_ROOT, 'version.json')
if os.path.exists(version_json):
    datas.append((version_json, '.'))

# 图标路径
icon_path = os.path.join(PROJECT_ROOT, 'src', 'gui_qt', 'assets', 'app_icon.png')
icon_list = [icon_path] if os.path.exists(icon_path) else []

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'qt_main.py')],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # PySide6 核心模块
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtSvg',
        'PySide6.QtSvgWidgets',
    ] + collect_submodules('src'),  # 自动收集所有 src.* 子模块
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', '_tkinter', 'matplotlib', 'numpy', 'pandas',
        'scipy', 'PIL', 'cv2', 'IPython', 'jupyter', 'notebook',
        'pytest', 'setuptools', 'wheel', 'pip'
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_list,
    contents_directory='internal',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)
