# FSmatbinBD V1.1 - 3D Material Library Query & Management System

A Python-based 3D material library query and management tool designed for ER/NR game, supporting material data querying, importing, exporting, and batch processing.

## 🚀 Core Features

- **🔍 Smart Material Search**: Quickly find and browse material resources in the library
- **📊 Visual Material Preview**: Intuitive display of material properties and parameter information
- **📁 Batch File Processing**: Support for batch import and export of material files
- **📦 BND Batch Extraction**: Efficient batch extraction based on WitchyBND
- **🗄️ Database Management**: SQLite database storage with backup and recovery support
- **🌐 Bilingual Interface**: Complete Chinese and English interface support
- **🎨 Modern UI**: Clean and user-friendly graphical interface design

## 📋 System Requirements

- **Python 3.7+**
- **Operating System**: Windows 10/11 (Recommended)
- **Memory**: 4GB+ RAM recommended
- **Storage**: At least 1GB available space

## 🛠️ Installation & Usage

### Quick Start

1. **Download the project** and extract to local directory
2. **Double-click to run** one of the following files:
   - `FSmatbinDB.bat` (Windows Batch)
   - `start_matbin_library.ps1` (PowerShell Script)
   - Or directly run `python main.py`

### Basic Operations

1. **Launch Program**: Run the startup files above and wait for interface to load
2. **Browse Materials**: Browse imported material library in the main interface
3. **Search Materials**: Use search box to quickly locate specific materials
4. **Import Materials**: Click import button to select and batch import material files
5. **Export Data**: Export selected material data to desired format

## ⚠️ Important Notes

### WitchyBND Tool Configuration

**Batch extraction functionality depends on the WitchyBND tool**. Before use, please:

1. **Download WitchyBND**: Visit [WitchyBND Official Repository](https://github.com/ividyon/WitchyBND)
2. **Placement**: Place the downloaded WitchyBND.exe file in the project's `tools/WitchyBND/` folder
3. **Verify Installation**: Ensure `tools/WitchyBND/WitchyBND.exe` file exists and is executable

### Usage Reminders

- **Data Backup**: Regularly backup the database file (`data/databases/materials.db`)
- **File Paths**: Avoid using file paths with special characters
- **Memory Usage**: Processing large batches may consume significant memory; consider closing unnecessary applications
- **Permissions**: Some operations may require administrator privileges

## 🎯 Main Interface Guide

- **Material List Panel**: Displays all imported materials with sorting and filtering support
- **Material Details Panel**: View detailed information and parameters of selected materials
- **Sampler Panel**: Manage and configure material samplers
- **Tools Panel**: Provides batch operations and data management functions

## 🙏 Acknowledgments

The batch extraction functionality of this project is based on the excellent open-source project **WitchyBND**. Special thanks to:

- **WitchyBND Project**: [https://github.com/ividyon/WitchyBND](https://github.com/ividyon/WitchyBND)
- **Author**: ividyon

## 📞 Support & Feedback

If you encounter issues or have suggestions for improvement, please contact us through:

- **GitHub Issues**: Submit issue reports in this repository
- **Feature Requests**: Welcome to propose new feature requirements
- **Bug Reports**: Please provide detailed steps to reproduce the issue

---


**Note**: This software is an open-source project for educational and research purposes only. Please comply with relevant laws and regulations during use.
