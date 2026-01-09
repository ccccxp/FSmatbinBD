#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FSmatbinBD 构建脚本
用于将应用打包为 Windows 可执行程序

使用方法:
    python build_app.py                    # 使用当前版本号构建
    python build_app.py --version 1.2.0    # 指定新版本号构建
    python build_app.py --spec             # 使用 spec 文件构建
"""

import PyInstaller.__main__
import os
import shutil
import sys
import json
from datetime import datetime


def load_version_config(base_dir: str) -> dict:
    """加载版本配置"""
    version_file = os.path.join(base_dir, 'version.json')
    if os.path.exists(version_file):
        with open(version_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "version": "1.0.0",
        "build_date": datetime.now().strftime("%Y-%m-%d"),
        "app_name": "FSMatbinBD",
        "description": "FS材质库查询工具",
        "author": "FSMatbinBD Team",
        "repository": ""
    }


def save_version_config(base_dir: str, config: dict):
    """保存版本配置"""
    version_file = os.path.join(base_dir, 'version.json')
    with open(version_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    print(f"  ✓ 版本配置已更新: {version_file}")


def update_version(base_dir: str, new_version: str = None) -> str:
    """
    更新版本号
    
    Args:
        base_dir: 项目根目录
        new_version: 新版本号（如果为 None，则不修改）
        
    Returns:
        当前版本号
    """
    config = load_version_config(base_dir)
    current_version = config.get('version', '1.0.0')
    
    if new_version and new_version != current_version:
        print(f"\n[版本更新] {current_version} -> {new_version}")
        config['version'] = new_version
        config['build_date'] = datetime.now().strftime("%Y-%m-%d")
        save_version_config(base_dir, config)
        return new_version
    else:
        # 仅更新构建日期
        config['build_date'] = datetime.now().strftime("%Y-%m-%d")
        save_version_config(base_dir, config)
        print(f"\n[当前版本] {current_version} (构建日期已更新)")
        return current_version


def build(version: str = None):
    """执行 PyInstaller 构建"""
    # 获取项目根目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 更新版本号
    current_version = update_version(base_dir, version)
    
    # 定义路径
    assets_src = os.path.join(base_dir, 'src', 'gui_qt', 'assets')
    theme_src = os.path.join(base_dir, 'src', 'gui_qt', 'theme')
    tools_src = os.path.join(base_dir, 'tools')
    data_src = os.path.join(base_dir, 'data')
    icon_path = os.path.join(assets_src, 'app_icon.png')
    autopack_config = os.path.join(base_dir, 'autopack_config.json')
    version_config = os.path.join(base_dir, 'version.json')
    
    # 清理之前的构建
    dist_dir = os.path.join(base_dir, 'dist')
    build_dir = os.path.join(base_dir, 'build')
    
    print("=" * 60)
    print(f"FSmatbinBD 构建脚本 - v{current_version}")
    print("=" * 60)
    print("\n[1/5] 清理之前的构建...")
    
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir, ignore_errors=True)
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir, ignore_errors=True)

    # Windows 使用分号作为路径分隔符
    sep = ';' if sys.platform.startswith('win') else ':'
    
    # 构建参数
    args = [
        os.path.join(base_dir, 'qt_main.py'),   # 入口脚本
        '--name=FSMatbinBD',                     # 可执行文件名
        '--noconsole',                           # 不显示控制台窗口
        '--onedir',                              # 目录模式（比 onefile 启动更快）
        '--clean',                               # 清理缓存
        '--contents-directory=internal',         # 依赖放入 internal 子目录
        f'--specpath={base_dir}',               # spec 文件位置
    ]

    print("\n[2/5] 添加数据文件...")
    
    # 添加 GUI 资源
    if os.path.exists(assets_src):
        args.append(f'--add-data={assets_src}{sep}src/gui_qt/assets')
        print(f"  ✓ 添加 assets: {assets_src}")
    
    # 添加主题文件
    if os.path.exists(theme_src):
        args.append(f'--add-data={theme_src}{sep}src/gui_qt/theme')
        print(f"  ✓ 添加 theme: {theme_src}")
    
    # 添加工具目录 (WitchyBND)
    if os.path.exists(tools_src):
        args.append(f'--add-data={tools_src}{sep}tools')
        print(f"  ✓ 添加 tools: {tools_src}")
    
    # 添加数据目录
    if os.path.exists(data_src):
        args.append(f'--add-data={data_src}{sep}data')
        print(f"  ✓ 添加 data: {data_src}")
    
    # 添加 autopack 配置
    if os.path.exists(autopack_config):
        args.append(f'--add-data={autopack_config}{sep}.')
        print(f"  ✓ 添加 autopack_config.json")
    
    # 添加版本配置
    if os.path.exists(version_config):
        args.append(f'--add-data={version_config}{sep}.')
        print(f"  ✓ 添加 version.json (v{current_version})")
    
    # 注意：支付二维码已内嵌到源码中，无需单独打包
    
    # 添加图标
    if os.path.exists(icon_path):
        args.append(f'--icon={icon_path}')
        print(f"  ✓ 添加图标: {icon_path}")
    
    # Hidden imports
    hidden_imports = [
        'PySide6.QtCore',
        'PySide6.QtGui', 
        'PySide6.QtWidgets',
        'PySide6.QtSvg',
        'PySide6.QtSvgWidgets',
        'src.core.i18n',
        'src.core.database',
        'src.core.xml_parser',
        'src.core.autopack_manager',
        'src.core.material_matcher',
        'src.core.multi_thread_matcher',
        'src.core.fast_material_matcher',
        'src.core.multi_thread_fast_matcher',
        'src.core.witchybnd_processor',
        'src.core.witchybnd_drag_drop',
        'src.core.version',
        'src.core.about_secure',
        'src.core.material_replacer',
        'src.core.material_replace_models',
        'src.core.material_json_parser',
        'src.core.sampler_type_parser',
        'src.core.undo_redo_manager',
        'src.utils.resource_path',
        'src.utils.config',
        'src.utils.helpers',
        'src.gui_qt.main_window',
        'src.gui_qt.material_tree_panel',
        'src.gui_qt.material_editor_panel',
        'src.gui_qt.material_matching_dialog_qt',
        'src.gui_qt.advanced_search_dialog_qt',
        'src.gui_qt.autopack_dialog_qt',
        'src.gui_qt.library_manager_dialog_qt',
        'src.gui_qt.dcx_import_dialog_qt',
        'src.gui_qt.import_dialogs_qt',
        'src.gui_qt.sampler_panel',
        'src.gui_qt.models',
        'src.gui_qt.loading_overlay',
        'src.gui_qt.smooth_scroll',
        'src.gui_qt.color_picker_dialog',
        'src.gui_qt.dark_titlebar',
        'src.gui_qt.about_dialog_qt',
        'src.gui_qt.batch_replace_dialog',
        'src.gui_qt.material_replace_dialog',
        'src.gui_qt.material_replace_editor',
        'src.gui_qt.texture_edit_panel',
        'src.gui_qt.standard_dialogs',
        'src.gui_qt.theme.palette',
        'src.gui_qt.theme.qss',
    ]
    
    for imp in hidden_imports:
        args.append(f'--hidden-import={imp}')
    
    # 排除不需要的包
    excludes = [
        'tkinter', '_tkinter', 'matplotlib', 'numpy', 'pandas',
        'scipy', 'PIL', 'cv2', 'IPython', 'jupyter', 'notebook',
        'pytest', 'setuptools', 'wheel', 'pip',
    ]
    
    for exc in excludes:
        args.append(f'--exclude-module={exc}')

    print(f"\n[3/5] 开始 PyInstaller 构建...")
    print(f"  入口文件: qt_main.py")
    print(f"  输出目录: {dist_dir}")
    print(f"  版本号: v{current_version}")
    
    # 运行 PyInstaller
    PyInstaller.__main__.run(args)
    
    # 构建完成
    exe_path = os.path.join(dist_dir, 'FSMatbinBD', 'FSMatbinBD.exe')
    
    print("\n" + "=" * 60)
    print(f"[4/5] 构建完成! - v{current_version}")
    print("=" * 60)
    
    if os.path.exists(exe_path):
        # 获取文件大小
        exe_size = os.path.getsize(exe_path) / (1024 * 1024)  # MB
        print(f"\n✓ 可执行文件: {exe_path}")
        print(f"✓ 版本号: v{current_version}")
        print(f"✓ 文件大小: {exe_size:.2f} MB")
        print(f"\n运行程序: {exe_path}")
    else:
        print(f"\n✗ 构建失败，未找到可执行文件")
        return 1
    
    return 0


def build_with_spec(version: str = None):
    """使用 spec 文件构建"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    spec_file = os.path.join(base_dir, 'FSMatbinBD.spec')
    
    if not os.path.exists(spec_file):
        print(f"错误: 找不到 spec 文件: {spec_file}")
        return 1
    
    # 更新版本号
    current_version = update_version(base_dir, version)
    
    print(f"使用 spec 文件构建 (v{current_version})...")
    PyInstaller.__main__.run([spec_file, '--clean'])
    return 0


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='FSmatbinBD 构建脚本')
    parser.add_argument('--spec', action='store_true', 
                       help='使用 FSMatbinBD.spec 文件构建')
    parser.add_argument('--version', '-v', type=str, default=None,
                       help='指定新版本号 (例如: 1.2.0)，不指定则使用当前版本')
    args = parser.parse_args()
    
    if args.spec:
        sys.exit(build_with_spec(args.version))
    else:
        sys.exit(build(args.version))
