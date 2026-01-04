#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高性能材质匹配器 - 快速匹配版本
"""

from typing import Dict, List, Optional
from src.core.material_matcher import MaterialMatcher
import time

class FastMaterialMatcher(MaterialMatcher):
    """高性能快速材质匹配器"""
    
    def __init__(self, database_manager):
        super().__init__(database_manager)
        
        # 快速匹配配置
        self.max_results_per_search = 10000  # 不限制结果数量
        self.similarity_threshold_boost = 10.0  # 提高10%的相似度要求
    
    def find_similar_materials_fast(self, source_material: Dict, target_library_id: int, 
                                  priority_order: List[str], similarity_threshold: float) -> List[Dict]:
        """
        快速匹配：优先匹配关键要素（材质名称、着色器路径、采样器类型）
        适用于快速查找明显相关的材质，不保证找全所有相关材质
        """
        # 快速匹配模式 - 移除详细输出
        
        try:
            # 获取目标库中的所有材质
            target_materials = self.database_manager.get_materials_by_library(target_library_id)
            
            # 获取源材质的详细信息
            source_details = self._get_material_details(source_material)
            
            # 预筛选使用固定核心权重，最终相似度计算使用用户优先级
            prefilter_weights = self._calculate_fast_weights()
            final_weights = self._calculate_weights(priority_order)
            
            library_name = self._get_library_name(target_library_id)
            
            results = []
            processed_count = 0
            progress_interval = max(100, len(target_materials) // 10)  # 显示10次进度
            start_time = time.time()
            
            for target_material in target_materials:
                try:
                    processed_count += 1
                    
                    # 静默进度，不输出详细信息
                    
                    # 跳过同一个材质
                    if (source_material.get('id') == target_material.get('id') and 
                        source_material.get('library_id') == target_material.get('library_id')):
                        continue
                    
                    # 第一阶段：使用固定核心权重进行预筛选
                    prefilter_similarity_info = self._calculate_similarity_optimized(
                        source_details, 
                        target_material,  
                        prefilter_weights  # 使用固定核心权重
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
                        final_weights  # 使用用户自定义权重
                    )
                    
                    # 调试信息：显示两阶段的相似度差异（仅前几个结果）
                    # 移除详细匹配输出
                    
                    final_similarity = final_similarity_info['total']
                    
                    # 检查最终相似度是否满足原始阈值（使用用户权重计算的结果）
                    if final_similarity >= similarity_threshold:
                        results.append({
                            'material': target_material,
                            'similarity': final_similarity,
                            'details': final_similarity_info['details'],  # 使用用户权重计算的详情
                            'library_name': library_name,
                            'source_material': source_material,  # 添加源材质信息
                            'target_material': target_material   # 添加目标材质信息
                        })
                        
                        # 不再限制结果数量，移除早期退出
                        
                except Exception as e:
                    continue
            
            # 按相似度排序
            results.sort(key=lambda x: x['similarity'], reverse=True)
            
            return results
            
        except Exception as e:
            return []
    
    def _calculate_fast_weights_from_priority(self, priority_order: List[str]) -> Dict[str, float]:
        """
        基于用户优先级计算快速匹配权重 - 只关注关键属性但尊重用户优先级
        """
        # 快速匹配只关注这三个关键属性
        fast_features = ['material_keywords', 'shader_path', 'sampler_types']
        
        # 如果没有优先级或优先级中没有关键属性，使用默认快速权重
        if not priority_order or not any(feature in fast_features for feature in priority_order):
            return self._calculate_fast_weights()
        
        weights = {}
        
        # 只为快速匹配的关键属性分配权重
        for feature in fast_features:
            weights[feature] = 0.0
        
        # 根据用户优先级分配权重
        total_priority_features = 0
        for feature in priority_order:
            if feature in fast_features:
                total_priority_features += 1
        
        if total_priority_features > 0:
            # 根据优先级顺序分配权重
            remaining_weight = 1.0
            for i, feature in enumerate(priority_order):
                if feature in fast_features:
                    # 优先级越高，权重越大
                    priority_weight = remaining_weight * 0.6  # 每个级别分配60%的剩余权重
                    weights[feature] = priority_weight
                    remaining_weight *= 0.4
            
            # 重新规范化权重
            total_weight = sum(weights.values())
            if total_weight > 0:
                for feature in weights:
                    weights[feature] = weights[feature] / total_weight
        else:
            # 如果优先级中没有快速匹配关键属性，使用均等权重
            for feature in fast_features:
                weights[feature] = 1.0 / len(fast_features)
        
        # 其他属性权重为0（快速匹配忽略）
        weights['sampler_paths'] = 0.0
        weights['parameters'] = 0.0
        weights['sampler_count'] = 0.0
        
        return weights
    
    def _calculate_fast_weights(self) -> Dict[str, float]:
        """
        计算快速匹配专用权重 - 只关注三个核心特征，忽略用户优先级
        采样器类型和着色器路径为主要权重，材质名称为最低权重
        """
        return {
            'sampler_types': 0.40,        # 采样器类型权重最高
            'shader_path': 0.40,          # 着色器路径权重与采样器类型一致
            'material_keywords': 0.20,    # 材质名称权重最低
            'sampler_paths': 0.0,         # 采样器路径权重为0（忽略）
            'parameters': 0.0,            # 参数权重为0（忽略）
            'sampler_count': 0.0          # 采样器数量权重为0（忽略）
        }
    
    def _fast_core_prefilter(self, source_details: Dict, target_material: Dict) -> bool:
        """
        核心特征快速预筛选 - 只检查材质名称、着色器路径、采样器类型的基本匹配
        """
        try:
            from difflib import SequenceMatcher
            
            # 1. 材质名称快速匹配
            source_name = source_details.get('filename', '').lower()
            target_name = target_material.get('filename', target_material.get('file_name', '')).lower()
            
            name_match_score = 0.0
            if source_name and target_name:
                # 快速名称相似度检查
                name_similarity = SequenceMatcher(None, source_name, target_name).ratio()
                name_match_score = name_similarity
                
                # 如果名称相似度很高，直接通过
                if name_similarity > 0.6:
                    return True
            
            # 2. 着色器路径快速匹配
            source_shader = source_details.get('shader_path', '').lower()
            target_shader = target_material.get('shader_path', '').lower()
            
            shader_match_score = 0.0
            if source_shader and target_shader:
                # 提取着色器关键词
                source_shader_parts = set(source_shader.split('/'))
                target_shader_parts = set(target_shader.split('/'))
                
                if source_shader_parts and target_shader_parts:
                    common_parts = source_shader_parts.intersection(target_shader_parts)
                    max_parts = max(len(source_shader_parts), len(target_shader_parts))
                    if max_parts > 0:
                        shader_match_score = len(common_parts) / max_parts
            
            # 3. 综合评估
            # 至少要有一定的名称相似度或着色器匹配度
            combined_score = name_match_score * 0.6 + shader_match_score * 0.4
            
            # 预筛选阈值：比较宽松，主要是过滤掉完全无关的材质
            return combined_score >= 0.15  # 15%的匹配度才能通过预筛选
            
        except Exception:
            # 如果预筛选出错，保守地允许通过
            return True