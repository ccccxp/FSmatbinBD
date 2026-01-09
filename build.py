"""
FSMatbinBD 本地打包脚本
用于在本地环境中构建可执行程序

使用方法:
    python build.py          # 普通打包
    python build.py --clean  # 清理后打包
    python build.py --onefile  # 单文件模式（可选）
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.absolute()

# 版本信息
VERSION = "1.2.1"
APP_NAME = 'FSMatbinBD'


def clean_build():
    """清理构建目录"""
    dirs_to_clean = ['build', 'dist']
    for d in dirs_to_clean:
        path = PROJECT_ROOT / d
        if path.exists():
            print(f"清理目录: {path}")
            shutil.rmtree(path)
    
    # 清理 .pyc 文件
    for pyc in PROJECT_ROOT.rglob('*.pyc'):
        pyc.unlink()
    for pycache in PROJECT_ROOT.rglob('__pycache__'):
        shutil.rmtree(pycache)


def build_exe(onefile=False):
    """使用 PyInstaller 构建可执行程序"""
    
    # 检查 PyInstaller 是否安装
    try:
        import PyInstaller
        print(f"PyInstaller 版本: {PyInstaller.__version__}")
    except ImportError:
        print("错误: 未安装 PyInstaller")
        print("请运行: pip install pyinstaller")
        return False
    
    # 构建命令
    spec_file = PROJECT_ROOT / 'FSMatbinBD.spec'
    
    if spec_file.exists():
        cmd = [sys.executable, '-m', 'PyInstaller', str(spec_file), '--noconfirm']
    else:
        # 如果没有 spec 文件，使用命令行参数
        cmd = [
            sys.executable, '-m', 'PyInstaller',
            '--name', APP_NAME,
            '--windowed',  # 无控制台窗口
            '--noconfirm',
            '--clean',
            '--add-data', f'src/gui_qt/assets{os.pathsep}src/gui_qt/assets',
            '--add-data', f'src/gui_qt/theme{os.pathsep}src/gui_qt/theme',
            '--add-data', f'tools/tools_config.json{os.pathsep}tools',
            '--add-data', f'autopack_config.json{os.pathsep}.',
            '--icon', 'src/gui_qt/assets/app_icon.png',
            '--hidden-import', 'PySide6.QtCore',
            '--hidden-import', 'PySide6.QtGui',
            '--hidden-import', 'PySide6.QtWidgets',
            'qt_main.py'
        ]
        
        if onefile:
            cmd.append('--onefile')
    
    print(f"执行命令: {' '.join(cmd)}")
    
    # 执行打包
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    
    if result.returncode != 0:
        print("打包失败!")
        return False
    
    print("打包成功!")
    return True


def copy_additional_files():
    """复制额外文件到输出目录"""
    dist_dir = PROJECT_ROOT / 'dist' / APP_NAME
    
    if not dist_dir.exists():
        print("警告: dist 目录不存在")
        return
    
    # 复制 README
    for readme in ['README.md', 'README_中文.md']:
        src = PROJECT_ROOT / readme
        if src.exists():
            shutil.copy(src, dist_dir)
            print(f"复制: {readme}")
    
    # 复制配置文件
    config = PROJECT_ROOT / 'autopack_config.json'
    if config.exists():
        shutil.copy(config, dist_dir)
        print("复制: autopack_config.json")
    
    # 复制工具目录
    tools_src = PROJECT_ROOT / 'tools' / 'WitchyBND'
    if tools_src.exists():
        tools_dst = dist_dir / 'tools' / 'WitchyBND'
        if tools_dst.exists():
            shutil.rmtree(tools_dst)
        shutil.copytree(tools_src, tools_dst)
        print("复制: tools/WitchyBND")
    
    # 创建必要的目录结构
    for subdir in ['data/databases', 'data/exports', 'autopack']:
        (dist_dir / subdir).mkdir(parents=True, exist_ok=True)
    
    print("额外文件复制完成")


def create_archive():
    """创建发布压缩包"""
    dist_dir = PROJECT_ROOT / 'dist' / APP_NAME
    
    if not dist_dir.exists():
        print("警告: dist 目录不存在，无法创建压缩包")
        return None
    
    archive_name = f"{APP_NAME}-v{VERSION}-windows"
    archive_path = PROJECT_ROOT / 'dist' / archive_name
    
    # 创建 ZIP 压缩包
    shutil.make_archive(str(archive_path), 'zip', dist_dir.parent, APP_NAME)
    
    final_path = f"{archive_path}.zip"
    print(f"压缩包已创建: {final_path}")
    return final_path


def main():
    parser = argparse.ArgumentParser(description='FSMatbinBD 打包脚本')
    parser.add_argument('--clean', action='store_true', help='清理构建目录后再打包')
    parser.add_argument('--onefile', action='store_true', help='打包为单个可执行文件')
    parser.add_argument('--no-archive', action='store_true', help='不创建压缩包')
    args = parser.parse_args()
    
    print(f"=== FSMatbinBD 打包脚本 v{VERSION} ===")
    print(f"项目目录: {PROJECT_ROOT}")
    print()
    
    # 切换到项目目录
    os.chdir(PROJECT_ROOT)
    
    if args.clean:
        print("--- 清理构建目录 ---")
        clean_build()
        print()
    
    print("--- 开始打包 ---")
    if not build_exe(onefile=args.onefile):
        sys.exit(1)
    print()
    
    print("--- 复制额外文件 ---")
    copy_additional_files()
    print()
    
    if not args.no_archive:
        print("--- 创建压缩包 ---")
        archive_path = create_archive()
        print()
    
    print("=== 打包完成 ===")
    print(f"输出目录: {PROJECT_ROOT / 'dist' / APP_NAME}")


if __name__ == '__main__':
    main()
