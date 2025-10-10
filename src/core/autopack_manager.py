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
            # 调试日志
            logger.info(f"开始执行自动封包，基础目录: {base_pack_dir}")
            logger.info(f"当前待封包列表项目数: {len(self.pending_list)}")
            
            # 首先检查是否有任何待封包项目
            if not self.pending_list:
                from .i18n import _
                result['error'] = "待封包列表为空"
                result['success'] = False
                logger.warning("封包失败: 待封包列表为空")
                return result
            
            # 筛选有目标路径的项目
            items_to_pack = [item for item in self.pending_list if item.get('target_path')]
            logger.info(f"筛选后有目标路径的项目数: {len(items_to_pack)}")
            
            if not items_to_pack:
                from .i18n import _
                result['error'] = _('no_target_path_items')
                result['success'] = False
                logger.warning("封包失败: 没有指定封包路径的项目")
                return result
            
            # 按目标路径分组
            path_groups = {}
            for item in items_to_pack:
                target_path = item['target_path']
                if target_path not in path_groups:
                    path_groups[target_path] = []
                path_groups[target_path].append(item)
            
            # 执行封包 - 按目标路径分组处理
            total_packed = 0
            total_failed = 0
            
            # 处理每个路径分组
            for target_path, items in path_groups.items():
                # 创建目标目录
                if target_path:
                    full_target_path = os.path.join(base_pack_dir, target_path)
                else:
                    full_target_path = base_pack_dir
                    
                os.makedirs(full_target_path, exist_ok=True)
                logger.info(f"处理目标路径: {target_path}, 完整路径: {full_target_path}")
                
                # 复制当前分组的matbin文件到目标目录
                matbin_files_copied = []
                for item in items:
                    try:
                        source_file = item['matbin_file']
                        target_file = os.path.join(full_target_path, item['filename'])
                        
                        if os.path.exists(source_file):
                            shutil.copy2(source_file, target_file)
                            matbin_files_copied.append(target_file)
                            logger.info(f"文件复制成功: {source_file} -> {target_file}")
                        else:
                            raise FileNotFoundError(f"源文件不存在: {source_file}")
                            
                    except Exception as e:
                        result['failed_files'].append({
                            'filename': item.get('filename', '未知'),
                            'error': str(e)
                        })
                        total_failed += 1
                        logger.error(f"文件复制失败: {item.get('matbin_file', '未知')} - {str(e)}")
                        continue
                
                # 记录当前分组的成功文件
                for copied_file in matbin_files_copied:
                    result['packed_files'].append({
                        'source': item['matbin_file'],
                        'target': copied_file,
                        'xml_file': item['xml_file'],
                        'target_path': target_path
                    })
                
                total_packed += len(matbin_files_copied)
                logger.info(f"路径分组 '{target_path}': 成功复制 {len(matbin_files_copied)} 个文件")
            
            # 如果有文件成功复制，使用WitchyBND对整个基础目录进行BND封包
            if total_packed > 0:
                try:
                    # 生成BND文件名（使用基础目录的名称）
                    bnd_name = os.path.basename(base_pack_dir.rstrip(os.sep))
                    bnd_file = self._create_bnd_package(base_pack_dir, bnd_name)
                    
                    if bnd_file:
                        # 更新所有已复制文件的信息，添加BND文件引用
                        for packed_item in result['packed_files']:
                            packed_item['bnd_file'] = bnd_file
                        
                        logger.info(f"BND封包成功: {bnd_file} (包含 {total_packed} 个文件)")
                    else:
                        logger.warning(f"BND封包失败，但文件复制成功")
                        
                except Exception as e:
                    logger.warning(f"BND封包失败，但文件复制成功: {str(e)}")
            
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
    
    def _create_bnd_package(self, source_dir: str, target_name: str) -> Optional[str]:
        """
        使用WitchyBND将基础目录重新打包为BND文件
        
        Args:
            source_dir: 包含matbin文件的基础目录
            target_name: 目标BND文件名称（不含扩展名）
            
        Returns:
            生成的BND文件路径，失败时返回None
        """
        try:
            from .witchybnd_processor import WitchyBNDProcessor
            processor = WitchyBNDProcessor()
            
            # 检查源目录是否存在且包含文件
            if not os.path.exists(source_dir):
                logger.error(f"源目录不存在: {source_dir}")
                return None
                
            files_in_dir = os.listdir(source_dir)
            if not files_in_dir:
                logger.warning(f"源目录为空: {source_dir}")
                return None
                
            logger.info(f"准备打包基础目录: {source_dir}, 包含 {len(files_in_dir)} 个文件")
            
            # BND文件将生成在基础目录的父目录中
            parent_dir = os.path.dirname(source_dir.rstrip(os.sep))
            expected_bnd_file = os.path.join(parent_dir, f"{target_name}.bnd")
            
            # 如果目标BND文件已存在，先删除
            if os.path.exists(expected_bnd_file):
                os.remove(expected_bnd_file)
                logger.info(f"删除已存在的BND文件: {expected_bnd_file}")
            
            # 使用WitchyBND重新打包整个基础目录
            # WitchyBND会将目录打包成同名的BND文件
            success, error = processor._run_witchy_drag_drop(source_dir)
            
            if success:
                # 检查可能生成的BND文件位置
                # WitchyBND根据目录名和配置可能生成不同格式的文件
                base_name = os.path.basename(source_dir.rstrip(os.sep))
                possible_bnd_files = [
                    # 标准BND文件
                    os.path.join(parent_dir, f"{target_name}.bnd"),
                    os.path.join(parent_dir, f"{base_name}.bnd"),
                    source_dir + ".bnd",
                    # MATBINBND文件（可能有DCX压缩）
                    os.path.join(parent_dir, f"{base_name.replace('-matbinbnd-dcx-wmatbinbnd', '')}.matbinbnd.dcx"),
                    os.path.join(parent_dir, f"{base_name.replace('-matbinbnd-dcx-wmatbinbnd', '')}.matbinbnd"),
                    os.path.join(parent_dir, f"{target_name}.matbinbnd.dcx"),
                    os.path.join(parent_dir, f"{target_name}.matbinbnd"),
                    # 其他可能的位置
                    os.path.join(parent_dir, f"{base_name}.dcx"),
                    source_dir + ".dcx"
                ]
                
                for possible_file in possible_bnd_files:
                    if os.path.exists(possible_file):
                        file_size = os.path.getsize(possible_file)
                        logger.info(f"封包文件创建成功: {possible_file} ({file_size} 字节)")
                        return possible_file
                
                logger.warning("WitchyBND执行成功但未找到生成的封包文件")
                logger.info(f"检查的位置: {possible_bnd_files}")
                # 列出父目录的所有文件以帮助调试
                try:
                    all_files = os.listdir(parent_dir)
                    logger.info(f"父目录 {parent_dir} 中的所有文件: {all_files}")
                except Exception as e:
                    logger.error(f"无法列出父目录文件: {e}")
                return None
            else:
                logger.error(f"WitchyBND执行失败: {error}")
                return None
                
        except Exception as e:
            logger.error(f"创建BND封包失败: {str(e)}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            return None
    
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