#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辅助函数 - 通用工具函数
"""

import os
import json
import shutil
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)

def ensure_dir(path: str) -> bool:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        path: 目录路径
        
    Returns:
        是否创建成功
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"创建目录失败 {path}: {str(e)}")
        return False

def safe_remove(path: str) -> bool:
    """
    安全删除文件或目录
    
    Args:
        path: 文件或目录路径
        
    Returns:
        是否删除成功
    """
    try:
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
        return True
    except Exception as e:
        logger.error(f"删除失败 {path}: {str(e)}")
        return False

def get_file_size(path: str) -> int:
    """
    获取文件大小
    
    Args:
        path: 文件路径
        
    Returns:
        文件大小（字节），失败返回-1
    """
    try:
        return os.path.getsize(path)
    except Exception:
        return -1

def format_file_size(size: int) -> str:
    """
    格式化文件大小显示
    
    Args:
        size: 文件大小（字节）
        
    Returns:
        格式化的大小字符串
    """
    if size < 0:
        return "未知"
    elif size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.1f} GB"

def format_timestamp(timestamp: Union[str, datetime, float, int]) -> str:
    """
    格式化时间戳
    
    Args:
        timestamp: 时间戳
        
    Returns:
        格式化的时间字符串
    """
    try:
        if isinstance(timestamp, str):
            # 尝试解析ISO格式
            if 'T' in timestamp:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        elif isinstance(timestamp, (int, float)):
            dt = datetime.fromtimestamp(timestamp)
        elif isinstance(timestamp, datetime):
            dt = timestamp
        else:
            return str(timestamp)
        
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return str(timestamp)

def validate_xml_name(name: str) -> bool:
    """
    验证XML元素名称是否有效
    
    Args:
        name: XML元素名称
        
    Returns:
        是否有效
    """
    if not name:
        return False
    
    # XML名称不能包含特殊字符
    invalid_chars = ['<', '>', '&', '"', "'", ' ', '\t', '\n', '\r']
    return not any(char in name for char in invalid_chars)

def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除无效字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        清理后的文件名
    """
    # Windows文件名无效字符
    invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
    
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # 移除开头和结尾的空格和点
    filename = filename.strip(' .')
    
    # 确保文件名不为空
    if not filename:
        filename = "unnamed"
    
    return filename

def deep_merge_dict(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """
    深度合并字典
    
    Args:
        base: 基础字典
        update: 更新字典
        
    Returns:
        合并后的字典
    """
    result = base.copy()
    
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dict(result[key], value)
        else:
            result[key] = value
    
    return result

def safe_json_load(file_path: str, default: Any = None) -> Any:
    """
    安全加载JSON文件
    
    Args:
        file_path: JSON文件路径
        default: 失败时的默认值
        
    Returns:
        解析后的数据或默认值
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"加载JSON文件失败 {file_path}: {str(e)}")
        return default

def safe_json_save(data: Any, file_path: str) -> bool:
    """
    安全保存JSON文件
    
    Args:
        data: 要保存的数据
        file_path: JSON文件路径
        
    Returns:
        是否保存成功
    """
    try:
        # 确保目录存在
        ensure_dir(os.path.dirname(file_path))
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存JSON文件失败 {file_path}: {str(e)}")
        return False

def parse_param_value(value_str: str, param_type: str) -> Any:
    """
    解析参数值字符串
    
    Args:
        value_str: 值字符串
        param_type: 参数类型
        
    Returns:
        解析后的值
    """
    try:
        param_type = param_type.lower().strip()
        value_str = value_str.strip()
        
        if param_type == 'bool':
            return value_str.lower() in ['true', '1', 'yes', 'on', 'enabled']
        elif param_type == 'int':
            return int(value_str)
        elif param_type == 'float':
            return float(value_str)
        elif param_type in ['int2', 'float2', 'float3', 'float4', 'float5']:
            # 解析数组
            if ',' in value_str:
                parts = [p.strip() for p in value_str.split(',')]
            else:
                parts = value_str.split()
            
            if param_type.startswith('int'):
                return [int(p) for p in parts if p]
            else:
                return [float(p) for p in parts if p]
        else:
            return value_str
    except Exception as e:
        logger.warning(f"解析参数值失败 '{value_str}' ({param_type}): {str(e)}")
        return value_str

def format_param_value(value: Any, param_type: str) -> str:
    """
    格式化参数值为字符串
    
    Args:
        value: 参数值
        param_type: 参数类型
        
    Returns:
        格式化的字符串
    """
    try:
        if value is None:
            return ""
        
        param_type = param_type.lower().strip()
        
        if param_type == 'bool':
            return str(value).lower()
        elif isinstance(value, list):
            return ', '.join(str(v) for v in value)
        else:
            return str(value)
    except Exception:
        return str(value) if value is not None else ""

def truncate_string(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    截断字符串
    
    Args:
        text: 原始字符串
        max_length: 最大长度
        suffix: 截断后缀
        
    Returns:
        截断后的字符串
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def get_relative_path(full_path: str, base_path: str) -> str:
    """
    获取相对路径
    
    Args:
        full_path: 完整路径
        base_path: 基础路径
        
    Returns:
        相对路径
    """
    try:
        return os.path.relpath(full_path, base_path)
    except Exception:
        return full_path

def is_valid_path(path: str) -> bool:
    """
    检查路径是否有效
    
    Args:
        path: 路径字符串
        
    Returns:
        是否有效
    """
    try:
        # 检查路径是否包含无效字符
        invalid_chars = ['<', '>', '|', '?', '*']
        if any(char in path for char in invalid_chars):
            return False
        
        # 检查路径长度（Windows限制）
        if len(path) > 260:
            return False
        
        return True
    except Exception:
        return False

def backup_file(file_path: str, backup_suffix: str = ".bak") -> Optional[str]:
    """
    备份文件
    
    Args:
        file_path: 原文件路径
        backup_suffix: 备份文件后缀
        
    Returns:
        备份文件路径，失败返回None
    """
    try:
        if not os.path.exists(file_path):
            return None
        
        backup_path = file_path + backup_suffix
        shutil.copy2(file_path, backup_path)
        return backup_path
    except Exception as e:
        logger.error(f"备份文件失败 {file_path}: {str(e)}")
        return None

class ProgressTracker:
    """进度跟踪器"""
    
    def __init__(self, total: int = 100):
        self.total = total
        self.current = 0
        self.start_time = datetime.now()
    
    def update(self, progress: int):
        """更新进度"""
        self.current = min(progress, self.total)
    
    def increment(self, step: int = 1):
        """增加进度"""
        self.current = min(self.current + step, self.total)
    
    def get_progress(self) -> float:
        """获取进度百分比"""
        return (self.current / self.total) * 100 if self.total > 0 else 0
    
    def get_elapsed_time(self) -> float:
        """获取已用时间（秒）"""
        return (datetime.now() - self.start_time).total_seconds()
    
    def get_eta(self) -> Optional[float]:
        """获取预计剩余时间（秒）"""
        if self.current == 0:
            return None
        
        elapsed = self.get_elapsed_time()
        remaining = self.total - self.current
        
        if remaining <= 0:
            return 0
        
        return (elapsed / self.current) * remaining
    
    def is_complete(self) -> bool:
        """是否完成"""
        return self.current >= self.total