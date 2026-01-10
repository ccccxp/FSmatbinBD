<div align="center">
  <img src="src/gui_qt/assets/app_icon.png" alt="FSMatbinBD Logo" width="128" height="128">

  # FSMatbinBD
  
  **FromSoftware 游戏材质库管理工具**
  
  [![Build Status](https://img.shields.io/github/actions/workflow/status/ccccxp/FSmatbinBD/release.yml?branch=main&style=flat-square)](https://github.com/ccccxp/FSmatbinBD/actions)
  [![Release](https://img.shields.io/github/v/release/ccccxp/FSmatbinBD?style=flat-square)](https://github.com/ccccxp/FSmatbinBD/releases)
  [![License](https://img.shields.io/github/license/ccccxp/FSmatbinBD?style=flat-square)](LICENSE)
  [![Platform](https://img.shields.io/badge/platform-Windows-blue?style=flat-square)](https://github.com/ccccxp/FSmatbinBD/releases)

  [**English**](README.md) | [**简体中文**](README_CN.md)

</div>

<br/>

FSMatbinBD 是一个针对 **Elden Ring**、**Dark Souls 3**、**Sekiro** 及 **Nightreign** 等 FromSoftware 游戏的材质文件（MTD/MATBIN）解析与管理工具。

该工具旨在将游戏材质档案解包并索引至本地 SQLite 数据库，以便用户快速检索材质属性、查找兼容的模型材质，并支持对材质数据进行批量编辑和重打包。

## 功能特性

- **材质库导入**
  - 支持解析 `.mtdbnd.dcx` 和 `.matbinbnd.dcx` 档案。
  - 索引信息包含 Shader 路径、参数值、纹理槽位等元数据。
  - 支持多库切换，可同时管理不同游戏的材质数据。

- **搜索与筛选**
  - 支持按材质名称、文件名或 Shader 路径进行关键词搜索。
  - 提供结构化筛选功能，可按 Shader 类型、采样器数量、Alpha 混合模式等内部属性过滤。

- **相似度匹配**
  - 基于纹理槽位、Shader 参数及命名规则计算材质相似度。
  - 辅助用户在跨游戏移植模型时（如从 DS3 到 ER）快速定位目标游戏中的兼容材质。

- **编辑与批处理**
  - 查看并编辑材质的具体参数。
  - 提供批量纹理路径替换功能，支持字符串匹配或正则表达式。
  - 集成 [WitchyBND](https://github.com/ividyon/WitchyBND) 接口，编辑后可自动重打包为有效的 DCX 文件。

## 安装说明

### 选项 1：完整版 (Full)
包含预置的数据库文件，适合直接使用。

1. 在 [Releases](https://github.com/ccccxp/FSmatbinBD/releases) 页面下载 `FSMatbinBD_vX.X.X_Windows_x64_Full.zip`。
2. 解压并运行 `FSMatbinBD.exe`。

### 选项 2：独立版 (Lite)
仅包含程序本体，体积较小。用户可自行导入游戏文件。

1. 下载 `FSMatbinBD_vX.X.X_Windows_x64_Lite.zip`。
2. 解压并运行程序。
3. **配置数据库**：
   - **导入**：点击工具栏的 `材质库管理` → `导入 DCX`，选择游戏解包后的材质档案（如 `allmaterialbnd.mtdbnd.dcx`）。
   - **或**：单独下载 `materials.db` 并放置于 `internal/data/databases/` 目录中。

## 工作流示例：模型移植

以将 Dark Souls 3 模型移植到 Elden Ring 为例：

1. **参考**：从源模型导出材质配置信息（可通过 FLVER Editor 查看）。
2. **匹配**：使用 FSMatbinBD 的 **匹配相似** 功能，在目标游戏库中查找Shader需求或纹理输入相近的材质。
3. **编辑**：使用 **批量替换** 功能调整纹理路径，使其符合目标游戏的目录结构。
4. **输出**：工具将修改后的数据重打包为 `.matbin` 文件，供游戏读取。

## 源码构建

环境要求：Python 3.11+

```bash
git clone https://github.com/ccccxp/FSmatbinBD.git
cd FSmatbinBD
pip install -r requirements.txt
python qt_main.py
```

## 致谢

- **[WitchyBND](https://github.com/ividyon/WitchyBND)**：用于处理 FromSoftware 游戏档案的解包与重打包。
- **SoulsMods 社区**：提供了大量关于文件格式的研究资料。

## 许可证

本项目采用 MIT 许可证，详情请参阅 [LICENSE](LICENSE) 文件。
