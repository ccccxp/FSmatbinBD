# FSmatbinBD V1.1 - 材质库查询系统

一个用于查询和管理材质库的Python应用程序，支持材质数据的导入、导出和可视化管理。

## 功能特性

- 🔍 材质库查询和搜索
- 📊 材质数据可视化显示
- 📁 支持材质文件的导入导出
- 🎨 现代化的GUI界面
- 🔄 数据库备份和恢复
- 🌐 多语言支持（中英文）
- 📦 支持AutoPack功能

## 项目结构

```
FSmatbinBD_V1.1/
├── main.py                 # 主程序入口
├── data/                   # 数据文件夹
│   └── databases/          # 数据库文件
├── src/                    # 源代码
│   ├── core/              # 核心模块
│   ├── gui/               # 图形界面
│   └── utils/             # 工具函数
├── scripts/               # 测试和诊断脚本
├── tools/                 # 外部工具
└── readme/               # 文档资料
```

## 环境要求

- Python 3.7+
- PyQt5/PyQt6
- SQLite3
- 其他依赖见requirements.txt

## 快速开始

1. 克隆仓库：
```bash
git clone https://github.com/ccccxp/FSmatbinDB.git
cd FSmatbinDB
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 运行程序：
```bash
python main.py
```

或者使用提供的批处理文件：
- Windows: `start_simple.bat`
- PowerShell: `start_matbin_library.ps1`

## 使用说明

1. **材质查询**: 在主界面中输入关键词搜索材质
2. **数据导入**: 支持XML格式的材质数据导入
3. **数据导出**: 可将材质数据导出为多种格式
4. **库管理**: 管理和组织材质库资源

## 开发说明

### 核心模块

- `database.py`: 数据库操作和管理
- `xml_parser.py`: XML文件解析器
- `i18n.py`: 国际化支持
- `autopack_manager.py`: AutoPack功能管理

### GUI模块

- `main_window.py`: 主窗口界面
- `material_panel.py`: 材质显示面板
- `sampler_panel.py`: 采样器面板
- `library_panel.py`: 库管理面板

## 版本历史

- V1.1: 当前版本，增强的GUI和稳定性改进
- V1.0: 初始版本

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 许可证

[在此添加您的许可证信息]

## 联系方式

如有问题或建议，请通过GitHub Issues联系。