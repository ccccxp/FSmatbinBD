# FSMatbinBD - FromSoftware 材质库查询工具

[![Build and Release](https://github.com/ccccxp/FSmatbinBD/actions/workflows/release.yml/badge.svg)](https://github.com/ccccxp/FSmatbinBD/actions/workflows/release.yml)

[English](README.md)

一款用于浏览、搜索和管理 FromSoftware 游戏（艾尔登法环、只狼等）材质数据的桌面工具。

## ✨ 主要功能

- **材质库管理**：导入 DCX 文件，自动解析并建立本地数据库
- **快速搜索**：支持关键词搜索、高级筛选（着色器路径、采样器类型等）
- **材质匹配**：智能匹配相似材质，辅助材质替换操作
- **批量操作**：支持批量替换纹理路径等高级功能
- **极速性能**：8线程并发导入，处理大型材质库飞快

## 🚀 快速开始

### 从 Release 下载
从 [Releases](https://github.com/ccccxp/FSmatbinBD/releases) 下载最新 `.zip` 包，解压后运行 `FSMatbinBD.exe`。

### 从源码运行
```bash
pip install -r requirements.txt
python qt_main.py
```

## 📦 打包构建
```bash
python build_app.py
```
输出位于 `dist/FSMatbinBD/`。

## 📁 项目结构
```
├── src/                  # 核心代码
│   ├── core/             # 业务逻辑
│   └── gui_qt/           # PySide6 界面
├── tools/                # 外部工具 (WitchyBND)
├── data/databases/       # 本地材质数据库
└── .github/workflows/    # CI/CD
```

## 🔧 技术栈
- Python 3.11+ | PySide6 (Qt6) | SQLite | PyInstaller

## 📄 许可证
MIT License
