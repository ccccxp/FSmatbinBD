#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件 - 程序配置项
"""

import os

# 数据库配置
DATABASE_CONFIG = {
    'default_db_path': os.path.join('data', 'databases', 'materials.db'),
    'backup_enabled': True,
    'backup_interval': 3600,  # 备份间隔（秒）
}

# 界面配置
GUI_CONFIG = {
    'window_size': '1400x900',
    'min_size': '1000x600',
    'theme': 'clam',
    'font_family': '微软雅黑',
    'font_size': 9,
}

# XML解析配置
PARSER_CONFIG = {
    'supported_extensions': ['.xml'],
    'encoding': 'utf-8',
    'validate_xml': True,
}

# 导出配置
EXPORT_CONFIG = {
    'default_export_dir': 'exports',
    'xml_declaration': True,
    'pretty_print': True,
    'encoding': 'utf-8',
}

# 日志配置
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file_enabled': True,
    'file_path': 'logs/app.log',
}

# 应用信息
APP_INFO = {
    'name': '3D材质库查询程序',
    'version': '1.0.0',
    'author': 'GitHub Copilot',
    'description': '用于解析和查询3D材质配置文件的程序',
}