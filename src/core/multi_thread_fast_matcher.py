#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多线程快速匹配器 - 专门用于快速搜索的第一层
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Callable
from src.core.fast_material_matcher import FastMaterialMatcher


class MultiThreadFastMatcher(FastMaterialMatcher):
    """多线程快速匹配器 - 专门优化第一层快速搜索"""
    
    def __init__(self, database_manager):
        super().__init__(database_manager)
        
        # 多线程配置 - 高性能优化
        self.max_workers = 16  # 增加到16线程进行高速处理
        self.chunk_size = 200  # 优化块大小
        self.stop_event = threading.Event()  # 添加停止事件
        
    def find_similar_materials_fast_parallel(self, source_material: Dict, target_library_id: int, 
                                           priority_order: List[str], similarity_threshold: float) -> List[Dict]:
        """
        多线程快速匹配：使用并行处理的两阶段策略
        """
        # 多线程快速匹配模式 - 移除详细输出
        
        try:
            # 获取目标库中的所有材质
            target_materials = self.database_manager.get_materials_by_library(target_library_id)
            
            # 获取源材质的详细信息
            source_details = self._get_material_details(source_material)
            
            # 预筛选使用固定核心权重，最终相似度计算使用用户优先级
            prefilter_weights = self._calculate_fast_weights()
            final_weights = self._calculate_weights(priority_order)
            library_name = self._get_library_name(target_library_id)
            
            # 将材质分块处理
            chunks = self._split_into_chunks(target_materials, self.chunk_size)
            
            start_time = time.time()
            all_results = []
            processed_count = 0
            total_materials = len(target_materials)
            
            # 使用线程池并行处理
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交所有任务
                future_to_chunk = {
                    executor.submit(
                        self._process_fast_chunk,
                        chunk_id,
                        chunk,
                        source_material,
                        source_details,
                        prefilter_weights,
                        final_weights,
                        library_name,
                        similarity_threshold
                    ): (chunk_id, len(chunk))
                    for chunk_id, chunk in enumerate(chunks)
                }
                
                # 收集结果
                for future in as_completed(future_to_chunk):
                    chunk_id, chunk_size = future_to_chunk[future]
                    try:
                        chunk_results = future.result()
                        all_results.extend(chunk_results)
                        processed_count += chunk_size
                        
                        progress = (processed_count / total_materials) * 100
                            
                    except Exception as e:
                        continue
            
            # 按相似度排序
            all_results.sort(key=lambda x: x['similarity'], reverse=True)
            
            return all_results
            
        except Exception as e:
            return []
    
    def _split_into_chunks(self, materials: List[Dict], chunk_size: int) -> List[List[Dict]]:
        """将材质列表分割成块"""
        chunks = []
        for i in range(0, len(materials), chunk_size):
            chunks.append(materials[i:i + chunk_size])
        return chunks
    
    def _process_fast_chunk(self, chunk_id: int, chunk: List[Dict], source_material: Dict,
                           source_details: Dict, prefilter_weights: Dict, final_weights: Dict,
                           library_name: str, similarity_threshold: float) -> List[Dict]:
        """处理一个材质块 - 快速匹配专用"""
        results = []
        
        try:
            for target_material in chunk:
                try:
                    # 跳过同一个材质
                    if (source_material.get('id') == target_material.get('id') and 
                        source_material.get('library_id') == target_material.get('library_id')):
                        continue
                    
                    # 第一阶段：使用固定核心权重进行预筛选
                    prefilter_similarity_info = self._calculate_similarity_optimized(
                        source_details, 
                        target_material,  
                        prefilter_weights
                    )
                    
                    prefilter_similarity = prefilter_similarity_info['total']
                    prefilter_threshold = min(100.0, similarity_threshold + self.similarity_threshold_boost)
                    
                    # 如果预筛选不通过，跳过
                    if prefilter_similarity < prefilter_threshold:
                        continue
                    
                    # 第二阶段：使用用户优先级权重计算最终相似度
                    final_similarity_info = self._calculate_similarity_optimized(
                        source_details, 
                        target_material,  
                        final_weights
                    )
                    
                    final_similarity = final_similarity_info['total']
                    
                    # 检查最终相似度是否满足原始阈值
                    if final_similarity >= similarity_threshold:
                        results.append({
                            'material': target_material,
                            'similarity': final_similarity,
                            'details': final_similarity_info['details'],
                            'library_name': library_name,
                            'source_material': source_material,  # 添加源材质信息
                            'target_material': target_material   # 添加目标材质信息
                        })
                        
                except Exception as e:
                    continue
            
            return results
            
        except Exception as e:
            pass
            return []