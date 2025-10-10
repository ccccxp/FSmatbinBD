# 材质库管理系统启动脚本
# PowerShell版本

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "           材质库管理系统" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# 检查Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python版本: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ 错误: 未找到Python解释器" -ForegroundColor Red
    Write-Host "请确保已安装Python 3.7+并添加到系统PATH" -ForegroundColor Yellow
    Read-Host "按Enter键退出"
    exit 1
}

# 检查必需文件
if (-not (Test-Path "main.py")) {
    Write-Host "❌ 错误: 未找到main.py文件" -ForegroundColor Red
    Write-Host "请确保在项目根目录运行此脚本" -ForegroundColor Yellow
    Read-Host "按Enter键退出"
    exit 1
}

if (-not (Test-Path "tools\WitchyBND\WitchyBND.exe")) {
    Write-Host "❌ 错误: 未找到WitchyBND工具" -ForegroundColor Red
    Write-Host "请运行setup_tools.py整合工具" -ForegroundColor Yellow
    Read-Host "按Enter键退出"
    exit 1
}

Write-Host "✓ 环境检查完成" -ForegroundColor Green
Write-Host "✓ 启动材质库管理系统..." -ForegroundColor Green
Write-Host ""

# 启动应用
try {
    python main.py
} catch {
    Write-Host ""
    Write-Host "❌ 应用启动失败" -ForegroundColor Red
    Read-Host "按Enter键退出"
}
