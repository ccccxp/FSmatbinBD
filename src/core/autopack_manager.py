#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动封包管理器
"""

import os
import json
import shutil
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class AutoPackManager:
    """自动封包管理器"""
    
    def __init__(self, autopack_dir: str = "autopack", config_file: str = "autopack_config.json"):
        """
        初始化自动封包管理器
        
        Args:
            autopack_dir: 自动封包目录
            config_file: 配置文件路径
        """
        self.autopack_dir = autopack_dir
        self.config_file = config_file
        self.pending_list = []  # 待封包列表
        
        # 确保目录存在
        os.makedirs(self.autopack_dir, exist_ok=True)
        
        # 加载配置
        self.load_config()
    
    def load_config(self):
        """加载自动封包配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.pending_list = config.get('pending_list', [])
        except Exception as e:
            logger.warning(f"加载自动封包配置失败: {str(e)}")
            self.pending_list = []
    
    def save_config(self):
        """保存自动封包配置"""
        try:
            config = {
                'pending_list': self.pending_list,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存自动封包配置失败: {str(e)}")
    
    def add_to_autopack(self, xml_file: str, original_matbin_path: str = None) -> str:
        """
        将XML文件添加到自动封包列表（使用多线程优化）
        
        Args:
            xml_file: XML文件路径
            original_matbin_path: 原始.matbin文件路径
            
        Returns:
            生成的.matbin文件路径
        """
        try:
            from .witchybnd_processor import WitchyBNDProcessor
            processor = WitchyBNDProcessor()
            
            # 使用多线程批量方法转换单个文件（为了保持接口一致性和性能）
            results = processor.pack_xml_to_matbin_batch([xml_file])
            matbin_file = results.get(xml_file)
            if not matbin_file:
                raise ValueError(f"XML转MATBIN失败: {xml_file}")
            
            # 移动到autopack目录
            output_filename = os.path.basename(matbin_file)
            target_path = os.path.join(self.autopack_dir, output_filename)
            shutil.move(matbin_file, target_path)
            matbin_file = target_path
            
            # 添加到待封包列表
            pack_item = {
                'id': len(self.pending_list) + 1,
                'xml_file': xml_file,
                'matbin_file': matbin_file,
                'original_path': original_matbin_path,
                'target_path': '',  # 用户指定的封包路径
                'added_time': datetime.now().isoformat(),
                'filename': os.path.basename(matbin_file)
            }
            
            self.pending_list.append(pack_item)
            self.save_config()
            
            logger.info(f"已添加到自动封包: {xml_file} -> {matbin_file}")
            return matbin_file
            
        except Exception as e:
            logger.error(f"添加到自动封包失败: {str(e)}")
            raise
    
    def get_pending_list(self) -> List[Dict]:
        """获取待封包列表"""
        return self.pending_list.copy()
    
    def get_statistics(self) -> Dict[str, int]:
        """获取统计信息"""
        return {
            'total_pending': len(self.pending_list),
            'with_target_path': len([item for item in self.pending_list if item.get('target_path')]),
            'without_target_path': len([item for item in self.pending_list if not item.get('target_path')])
        }
    
    def update_target_path(self, item_ids: List[int], target_path: str):
        """更新目标路径"""
        for item in self.pending_list:
            if item['id'] in item_ids:
                item['target_path'] = target_path
        self.save_config()
    
    def remove_from_pending(self, item_ids: List[int]):
        """从待封包列表中移除项目"""
        self.pending_list = [item for item in self.pending_list if item['id'] not in item_ids]
        self.save_config()
    
    def execute_autopack(self, base_pack_dir: str) -> Dict[str, any]:
        """
        执行自动封包（使用多线程优化）
        
        Args:
            base_pack_dir: 基础封包目录
            
        Returns:
            封包结果信息
        """
        result = {
            'success': False,
            'packed_count': 0,
            'failed_count': 0,
            'packed_files': [],
            'failed_files': [],
            'error': None
        }
        
        try:
            # 筛选有目标路径的项目
            items_to_pack = [item for item in self.pending_list if item.get('target_path')]
            
            if not items_to_pack:
                raise ValueError("没有指定封包路径的项目")
            
            # 按目标路径分组
            path_groups = {}
            for item in items_to_pack:
                target_path = item['target_path']
                if target_path not in path_groups:
                    path_groups[target_path] = []
                path_groups[target_path].append(item)
            
            # 执行封包 - 使用多线程批量操作优化大量文件处理
            total_packed = 0
            total_failed = 0
            
            for target_path, items in path_groups.items():
                full_target_path = os.path.join(base_pack_dir, target_path)
                os.makedirs(full_target_path, exist_ok=True)
                
                # 如果项目数量较多，可以考虑使用批量复制操作
                batch_copy_success = 0
                batch_copy_failed = 0
                
                for item in items:
                    try:
                        # 复制.matbin文件到目标路径
                        source_file = item['matbin_file']
                        target_file = os.path.join(full_target_path, item['filename'])
                        
                        if os.path.exists(source_file):
                            shutil.copy2(source_file, target_file)
                            result['packed_files'].append({
                                'source': source_file,
                                'target': target_file,
                                'xml_file': item['xml_file']
                            })
                            batch_copy_success += 1
                            logger.info(f"封包成功: {source_file} -> {target_file}")
                        else:
                            raise FileNotFoundError(f"源文件不存在: {source_file}")
                            
                    except Exception as e:
                        result['failed_files'].append({
                            'file': item.get('matbin_file', '未知'),
                            'error': str(e)
                        })
                        batch_copy_failed += 1
                        logger.error(f"封包失败: {item.get('matbin_file', '未知')} - {str(e)}")
                
                total_packed += batch_copy_success
                total_failed += batch_copy_failed
                
                logger.info(f"路径 {target_path}: 成功 {batch_copy_success}, 失败 {batch_copy_failed}")
            
            result['packed_count'] = total_packed
            result['failed_count'] = total_failed
            result['success'] = total_packed > 0
            
            # 清理已成功封包的项目
            if total_packed > 0:
                packed_ids = [item['id'] for item in items_to_pack 
                             if any(pf['source'] == item['matbin_file'] for pf in result['packed_files'])]
                self.remove_from_pending(packed_ids)
            
            logger.info(f"自动封包完成: 成功 {total_packed}, 失败 {total_failed}")
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"执行自动封包失败: {str(e)}")
        
        return result
    
    def clear_autopack_dir(self):
        """清理autopack目录"""
        try:
            if os.path.exists(self.autopack_dir):
                for file in os.listdir(self.autopack_dir):
                    file_path = os.path.join(self.autopack_dir, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
            logger.info("清理autopack目录完成")
        except Exception as e:
            logger.error(f"清理autopack目录失败: {str(e)}")