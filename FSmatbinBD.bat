@echo off
chcp 65001 > nul
title 材质库管理系统

echo ================================================
echo           材质库管理系统
echo ================================================
echo.

REM 检查Python是否存在
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: 未找到Python解释器
    echo 请确保已安装Python 3.7+并添加到系统PATH
    pause
    exit /b 1
)

REM 检查必需文件
if not exist "main.py" (
    echo ❌ 错误: 未找到main.py文件
    echo 请确保在项目根目录运行此脚本
    pause
    exit /b 1
)

if not exist "tools\WitchyBND\WitchyBND.exe" (
    echo ❌ 错误: 未找到WitchyBND工具
    echo 请运行setup_tools.py整合工具
    pause
    exit /b 1
)

echo ✓ 环境检查完成
echo ✓ 启动材质库管理系统...
echo.

REM 启动应用
python main.py

if %errorlevel% neq 0 (
    echo.
    echo ❌ 应用启动失败
    pause
)
