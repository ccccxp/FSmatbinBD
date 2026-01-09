# FSMatbinBD - FromSoftware Material Database Browser

[![Build and Release](https://github.com/ccccxp/FSmatbinBD/actions/workflows/release.yml/badge.svg)](https://github.com/ccccxp/FSmatbinBD/actions/workflows/release.yml)

[中文版](README_CN.md)

A desktop tool for browsing, searching, and managing material data from FromSoftware games (Elden Ring, Sekiro, etc.).

## ✨ Features

- **Material Library Management**: Import DCX files, auto-parse and build local database
- **Fast Search**: Keyword search, advanced filters (shader path, sampler type, etc.)
- **Material Matching**: Smart matching of similar materials for replacement assistance
- **Batch Operations**: Bulk texture path replacement and more
- **High Performance**: 8-thread concurrent import for lightning-fast processing

## 🚀 Quick Start

### Download Release
Download the latest `.zip` from [Releases](https://github.com/ccccxp/FSmatbinBD/releases), extract and run `FSMatbinBD.exe`.

### Run from Source
```bash
pip install -r requirements.txt
python qt_main.py
```

## 📦 Build
```bash
python build_app.py
```
Output in `dist/FSMatbinBD/`.

## 📁 Structure
```
├── src/                  # Source code
│   ├── core/             # Business logic
│   └── gui_qt/           # PySide6 GUI
├── tools/                # External tools (WitchyBND)
├── data/databases/       # Local material database
└── .github/workflows/    # CI/CD
```

## 🔧 Tech Stack
- Python 3.11+ | PySide6 (Qt6) | SQLite | PyInstaller

## 📄 License
MIT License