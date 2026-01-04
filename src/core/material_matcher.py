#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
材质匹配器核心模块
Material Matcher Core Module
"""

import re
import json
from typing import Dict, List, Tuple, Optional, Any
from difflib import SequenceMatcher
from difflib import SequenceMatcher
import math

class MaterialMatcher:
    """材质匹配器"""
    
    def __init__(self, database_manager):
        self.database_manager = database_manager
        
        # 添加缓存以减少数据库查询
        self._library_cache = {}
        self._material_details_cache = {}
        
        # 匹配权重配置
        self.default_weights = {
            'sampler_types': 0.30,      # 采样器类型
            'shader_path': 0.25,        # 着色器路径
            'sampler_count': 0.15,      # 采样器数量
            'parameters': 0.15,         # 可编辑参数
            'material_keywords': 0.10,   # 材质名称关键词
            'sampler_paths': 0.05        # 采样器路径
        }
        
        # 关键词提取正则表达式
        self.keyword_patterns = {
            'sampler_types': [
                r'(?i)([A-Z]+)(?=_)',           # 大写字母开头的前缀
                r'(?i)(MetallicMap|NormalMap|DiffuseMap|SpecularMap|RoughnessMap|AOMap|HeightMap|EmissiveMap)',
                r'(?i)(Texture2D|TextureCube|Texture3D)',
                r'(?i)(AMSN|AMSO|AMSS|AMSB)',
                r'(?i)(Mb\d+)',                 # Mb后跟数字
            ],
            'shader_path': [
                r'(?i)(cloth|hair|metal|skin|glass|fabric|leather|wood|stone|water)',
                r'(?i)(DetailBlend|LayerBlend|MultiLayer)',
                r'(?i)(PBR|Phong|Lambert|Blinn)',
            ],
            'material_keywords': [
                r'(?i)(hair|cloth|metal|skin|fabric|leather|wood|stone|glass|water|plastic)',
                r'(?i)(rough|smooth|glossy|matte|transparent|opaque)',
                r'(?i)(female|male|character|environment|prop)',
            ]
        }
    
    def find_similar_materials(self, source_material: Dict, target_library_id: int, 
                              priority_order: List[str], similarity_threshold: float) -> List[Dict]:
        """
        精确搜索 - 使用两层搜索策略确保找到相似材质
        
        Args:
            source_material: 源材质信息
            target_library_id: 目标库ID
            priority_order: 匹配优先级顺序
            similarity_threshold: 相似度阈值
        
        Returns:
            匹配结果列表，每个结果包含材质信息、相似度和详细匹配信息
        """
        # 精确搜索：两层搜索策略（静默模式）
        
        # 第一层：带预筛选的快速搜索
        results = self._perform_prefiltered_search(source_material, target_library_id, 
                                                  priority_order, similarity_threshold)
        
        # 如果第一层返回0个结果，进行第二层全面搜索
        if len(results) == 0:
            results = self._perform_comprehensive_search(source_material, target_library_id, 
                                                        priority_order, similarity_threshold)
        
        return results
    
    def _perform_prefiltered_search(self, source_material: Dict, target_library_id: int, 
                                   priority_order: List[str], similarity_threshold: float) -> List[Dict]:
        """
        第一层：带预筛选的快速搜索
        """
        try:
            # 获取目标库中的所有材质
            target_materials = self.database_manager.get_materials_by_library(target_library_id)
            
            # 获取源材质的详细信息
            source_details = self._get_material_details(source_material)
            
            results = []
            processed_count = 0
            prefilter_passed = 0
            progress_interval = max(100, len(target_materials) // 20)  # 显示20次进度
            
            # 预计算权重和库名称，避免重复计算
            weights = self._calculate_weights(priority_order)
            library_name = self._get_library_name(target_library_id)
            
            # 第一阶段：快速预筛选，只收集候选材质
            candidate_materials = []
            
            for target_material in target_materials:
                try:
                    processed_count += 1
                    
                    # 静默进度
                    
                    # 跳过同一个材质
                    if (source_material.get('id') == target_material.get('id') and 
                        source_material.get('library_id') == target_material.get('library_id')):
                        continue
                    
                    # 快速预筛选 - 只做简单的匹配判断
                    if self._quick_prefilter(source_details, target_material, similarity_threshold):
                        candidate_materials.append(target_material)
                        prefilter_passed += 1
                        
                except Exception as e:
                    continue
            
            # 第一层预筛选完成（静默）
            
            # 如果候选材质数量为0，直接返回空结果（将触发第二层搜索）
            if len(candidate_materials) == 0:
                return results
            
            # 第二阶段：对候选材质进行完整相似度计算（静默）
            
            for i, target_material in enumerate(candidate_materials):
                try:
                    
                    # 获取目标材质详细信息（用于计算数量）
                    target_details = self._get_material_details(target_material)
                    
                    # 计算详细相似度
                    similarity_info = self._calculate_similarity_optimized(
                        source_details, 
                        target_material, 
                        weights
                    )
                    
                    total_similarity = similarity_info['total']
                    
                    # 检查是否满足阈值
                    if total_similarity >= similarity_threshold:
                        # 将采样器/参数信息添加到详情中，便于UI显示
                        details = similarity_info['details'].copy()
                        details['source_sampler_count'] = len(source_details.get('samplers', []))
                        details['target_sampler_count'] = len(target_details.get('samplers', []))
                        details['source_param_count'] = len(source_details.get('parameters', []))
                        details['target_param_count'] = len(target_details.get('parameters', []))
                        
                        results.append({
                            'material': target_material,
                            'similarity': total_similarity,
                            'details': details,
                            'library_name': library_name,
                            'source_material': source_material,  # 添加源材质信息
                            'target_material': target_material   # 添加目标材质信息
                        })
                        
                        # 早期退出：如果找到足够多的结果就停止
                        if len(results) >= 1000:  # 最多1000个结果
                            break
                        
                except Exception as e:
                    continue
            
            # 按相似度排序
            results.sort(key=lambda x: x['similarity'], reverse=True)
            
            return results
            
        except Exception as e:
            return []
    
    def _perform_comprehensive_search(self, source_material: Dict, target_library_id: int, 
                                     priority_order: List[str], similarity_threshold: float) -> List[Dict]:
        """
        第二层：全面搜索 - 跳过所有预筛选，降低相似度阈值
        """
        try:
            # 第二层全面搜索：跳过所有预筛选，降低相似度阈值（静默）
            
            # 获取目标库中的所有材质
            target_materials = self.database_manager.get_materials_by_library(target_library_id)
            

            
            # 降低相似度阈值（用于初筛）
            relaxed_threshold = max(10.0, similarity_threshold * 0.3)  # 降到原来的30%，最低10%
            # 降低相似度阈值（静默）
            
            # 获取源材质的详细信息
            source_details = self._get_material_details(source_material)
            
            results = []
            processed_count = 0
            progress_interval = max(100, len(target_materials) // 20)  # 显示20次进度
            
            # 预计算权重和库名称
            weights = self._calculate_weights(priority_order)
            library_name = self._get_library_name(target_library_id)
            
            # 静默权重和阈值配置
            
            for target_material in target_materials:
                try:
                    processed_count += 1
                    
                    # 静默进度
                    
                    # 跳过同一个材质
                    if (source_material.get('id') == target_material.get('id') and 
                        source_material.get('library_id') == target_material.get('library_id')):
                        continue
                    
                    # 🚨 关键：直接计算相似度，绝对不使用任何预筛选！
                    target_details = self._get_material_details(target_material)
                    similarity_info = self._calculate_similarity_optimized(
                        source_details, 
                        target_details, 
                        weights
                    )
                    
                    total_similarity = similarity_info['total']
                    
                    # 检查是否满足放宽后的阈值
                    if total_similarity >= relaxed_threshold:
                        # 将采样器/参数信息添加到详情中，便于UI显示
                        details = similarity_info['details'].copy()
                        details['source_sampler_count'] = len(source_details.get('samplers', []))
                        details['target_sampler_count'] = len(target_details.get('samplers', []))
                        details['source_param_count'] = len(source_details.get('parameters', []))
                        details['target_param_count'] = len(target_details.get('parameters', []))
                        
                        results.append({
                            'material': target_material,
                            'similarity': total_similarity,
                            'details': details,
                            'library_name': library_name,
                            'source_material': source_material,  # 添加源材质信息
                            'target_material': target_material   # 添加目标材质信息
                        })
                        
                        # 静默匹配
                        
                except Exception as e:
                    continue
            
            # 按相似度排序
            results.sort(key=lambda x: x['similarity'], reverse=True)
            
            # 🚨 重要：用原始阈值再过滤一次，确保返回结果符合用户设置
            filtered_results = [r for r in results if r['similarity'] >= similarity_threshold]
            
            return filtered_results
            
        except Exception as e:
            return []
    
    def _get_material_details(self, material: Dict) -> Dict:
        """获取材质详细信息（带缓存）"""
        material_id = material.get('id')
        
        # 如果没有有效的id，静默修复
        if material_id is None or material_id == '' or material_id == 0:
            # 使用文件名作为替代ID，不输出警告（这种情况很少见且不影响功能）
            material_id = material.get('filename', material.get('file_name', f'temp_{hash(str(material))}'))
        
        # 检查缓存
        if material_id in self._material_details_cache:
            return self._material_details_cache[material_id]
        
        details = {
            'basic_info': material,
            'samplers': [],
            'parameters': [],
            'shader_path': material.get('shader_path', '') or material.get('shader_name', '') or material.get('shader', ''),
            'keywords': [],
            'filename': material.get('filename', '') or material.get('file_name', '') or material.get('name', '')
        }
        
        # 从材质名称提取关键词（使用下划线分隔）
        material_name = details['filename']
        if material_name:
            details['keywords'] = self._extract_material_keywords(material_name)
        
        try:
            # 只有存在有效ID时才获取采样器信息
            if material.get('id'):
                samplers = self.database_manager.get_samplers(material['id'])
                if isinstance(samplers, list):
                    for sampler in samplers:
                        sampler_info = {
                            'name': sampler.get('name', ''),
                            'path': sampler.get('path', ''),
                            'type': sampler.get('type', ''),
                            'keywords': self._extract_keywords(sampler.get('type', ''), 'sampler_types')
                        }
                        details['samplers'].append(sampler_info)
                
                # 获取参数信息
                parameters = self.database_manager.get_parameters(material['id'])
                if isinstance(parameters, list):
                    for param in parameters:
                        param_info = {
                            'name': param.get('name', ''),
                            'type': param.get('type', ''),
                            'value': param.get('value', ''),
                            'default_value': param.get('default_value', '')
                        }
                        details['parameters'].append(param_info)
                
        except Exception as e:
            pass
            # 即使出错也要设置基本信息，确保程序能继续运行
        
        # 缓存结果
        if material_id:
            self._material_details_cache[material_id] = details
        
        return details
    
    def _calculate_similarity_optimized(self, source_details: Dict, target_material: Dict, 
                                      weights: Dict[str, float]) -> Dict:
        """优化版本的相似度计算 - 使用预计算的权重"""
        
        # 获取目标材质详细信息
        target_details = self._get_material_details(target_material)
        
        # 计算各项匹配分数
        scores = {}
        
        try:
            # 1. 采样器类型匹配
            source_samplers = source_details.get('samplers', [])
            target_samplers = target_details.get('samplers', [])
            
            if not isinstance(source_samplers, list):
                source_samplers = []
            if not isinstance(target_samplers, list):
                target_samplers = []
                
            scores['sampler_types'] = self._match_sampler_types(source_samplers, target_samplers)
            
            # 2. 着色器路径匹配
            source_shader = source_details.get('shader_path', '')
            target_shader = target_details.get('shader_path', '')
            scores['shader_path'] = self._match_shader_path(source_shader, target_shader)
            
            # 3. 采样器数量匹配
            scores['sampler_count'] = self._match_sampler_count(len(source_samplers), len(target_samplers))
            
            # 4. 参数匹配
            source_parameters = source_details.get('parameters', [])
            target_parameters = target_details.get('parameters', [])
            
            if not isinstance(source_parameters, list):
                source_parameters = []
            if not isinstance(target_parameters, list):
                target_parameters = []
                
            scores['parameters'] = self._match_parameters(source_parameters, target_parameters)
            
            # 5. 材质关键词匹配（使用新的下划线分隔算法）
            source_keywords = source_details.get('keywords', [])
            target_keywords = target_details.get('keywords', [])
            
            if not isinstance(source_keywords, list):
                source_keywords = []
            if not isinstance(target_keywords, list):
                target_keywords = []
                
            scores['material_keywords'] = self._match_material_keywords(source_keywords, target_keywords)
            
            # 6. 采样器路径匹配
            scores['sampler_paths'] = self._match_sampler_paths(source_samplers, target_samplers)
            
            # 使用预计算的权重计算加权总分
            total_score = 0.0
            for feature, weight in weights.items():
                if feature in scores:
                    total_score += scores[feature] * weight
            
            # 应用门槛惩罚机制：最高优先级特征得分低时惩罚总分
            total_score = self._apply_threshold_penalty(total_score, scores, weights)
            
            return {
                'total': total_score,
                'details': scores,
                'weights': weights
            }
            
        except Exception as e:
            print(f"计算相似度时出错: {e}")
            raise e
    
    def _calculate_similarity(self, source_details: Dict, target_material: Dict, 
                            priority_order: List[str]) -> Dict:
        """计算材质相似度"""
        
        # 获取目标材质详细信息
        target_details = self._get_material_details(target_material)
        
        # 计算各项匹配分数
        scores = {}
        
        try:
            # 1. 采样器类型匹配
            source_samplers = source_details.get('samplers', [])
            target_samplers = target_details.get('samplers', [])
            
            # 确保是列表类型
            if not isinstance(source_samplers, list):
                print(f"警告: source_samplers 不是列表类型: {type(source_samplers)}")
                source_samplers = []
            if not isinstance(target_samplers, list):
                print(f"警告: target_samplers 不是列表类型: {type(target_samplers)}")
                target_samplers = []
                
            scores['sampler_types'] = self._match_sampler_types(
                source_samplers, 
                target_samplers
            )
            
            # 2. 着色器路径匹配
            source_shader = source_details.get('shader_path', '')
            target_shader = target_details.get('shader_path', '')
            
            scores['shader_path'] = self._match_shader_path(
                source_shader, 
                target_shader
            )
            
            # 3. 采样器数量匹配
            scores['sampler_count'] = self._match_sampler_count(
                len(source_samplers), 
                len(target_samplers)
            )
            
            # 4. 参数匹配
            source_parameters = source_details.get('parameters', [])
            target_parameters = target_details.get('parameters', [])
            
            # 确保是列表类型
            if not isinstance(source_parameters, list):
                print(f"警告: source_parameters 不是列表类型: {type(source_parameters)}")
                source_parameters = []
            if not isinstance(target_parameters, list):
                print(f"警告: target_parameters 不是列表类型: {type(target_parameters)}")
                target_parameters = []
                
            scores['parameters'] = self._match_parameters(
                source_parameters, 
                target_parameters
            )
            
            # 5. 材质关键词匹配（使用新的下划线分隔算法）
            source_keywords = source_details.get('keywords', [])
            target_keywords = target_details.get('keywords', [])
            
            # 确保是列表类型
            if not isinstance(source_keywords, list):
                print(f"警告: source_keywords 不是列表类型: {type(source_keywords)}")
                source_keywords = []
            if not isinstance(target_keywords, list):
                print(f"警告: target_keywords 不是列表类型: {type(target_keywords)}")
                target_keywords = []
                
            scores['material_keywords'] = self._match_material_keywords(
                source_keywords, 
                target_keywords
            )
            
            # 6. 采样器路径匹配
            scores['sampler_paths'] = self._match_sampler_paths(
                source_samplers, 
                target_samplers
            )
            
            # 根据优先级计算加权总分
            total_score = 0.0
            weights = self._calculate_weights(priority_order)
            
            for feature, weight in weights.items():
                if feature in scores:
                    total_score += scores[feature] * weight
            
            return {
                'total': total_score,
                'details': scores,
                'weights': weights
            }
            
        except Exception as e:
            print(f"计算相似度时出错: {e}")
            print(f"source_details类型: {type(source_details)}")
            print(f"target_details类型: {type(target_details)}")
            print(f"priority_order类型: {type(priority_order)}")
            raise e
    
    def _apply_threshold_penalty(self, total_score: float, scores: Dict[str, float], 
                                  weights: Dict[str, float]) -> float:
        """应用门槛惩罚机制：最高权重特征得分低时惩罚总分"""
        if not scores or not weights:
            return total_score
        
        # 找到权重最高的特征
        max_weight_feature = max(weights.keys(), key=lambda f: weights.get(f, 0))
        core_score = scores.get(max_weight_feature, 50)
        
        # 应用惩罚
        if core_score < 30:
            # 核心特征得分 < 30%，严重惩罚（总分 × 0.2~0.3）
            penalty_factor = max(0.2, core_score / 100)
        elif core_score < 50:
            # 核心特征得分 < 50%，中等惩罚（总分 × 0.5~0.6）
            penalty_factor = max(0.5, core_score / 100)
        else:
            # 核心特征得分 >= 50%，无惩罚
            penalty_factor = 1.0
        
        return total_score * penalty_factor
    
    def _match_sampler_types(self, source_samplers: List[Dict], target_samplers: List[Dict]) -> float:
        """匹配采样器类型 - 改进版：类型覆盖度80% + 关键词相似度20%"""
        if not source_samplers and not target_samplers:
            return 100.0
        if not source_samplers or not target_samplers:
            return 0.0
        
        # 1. 提取采样器类型统计（使用最后一个关键词作为类型）
        source_type_stats = self._get_sampler_type_stats(source_samplers)
        target_type_stats = self._get_sampler_type_stats(target_samplers)
        
        if not source_type_stats:
            return 50.0  # 源无有效类型，给中等分数
        
        # 2. 计算类型覆盖度（源类型是否被目标覆盖，允许目标更多）
        type_coverage_score = 0.0
        for sampler_type, source_count in source_type_stats.items():
            target_count = target_type_stats.get(sampler_type, 0)
            if target_count >= source_count:
                # 目标完全覆盖源的该类型
                type_coverage_score += 1.0
            elif target_count > 0:
                # 部分覆盖
                type_coverage_score += target_count / source_count
            # 目标没有该类型：0分
        
        type_coverage = (type_coverage_score / len(source_type_stats)) * 100.0
        
        # 3. 计算采样器关键词相似度（匹配相同类型的采样器对）
        keyword_similarity = self._calculate_sampler_keyword_similarity(
            source_samplers, target_samplers, source_type_stats, target_type_stats
        )
        
        # 4. 综合得分：类型覆盖80% + 关键词相似20%
        return type_coverage * 0.80 + keyword_similarity * 0.20
    
    def _get_sampler_type_stats(self, samplers: List[Dict]) -> Dict[str, int]:
        """统计采样器类型（使用最后一个关键词作为类型）"""
        type_stats = {}
        for sampler in samplers:
            sampler_type = self._extract_sampler_type(sampler)
            if sampler_type:
                type_stats[sampler_type] = type_stats.get(sampler_type, 0) + 1
        return type_stats
    
    def _extract_sampler_type(self, sampler: Dict) -> str:
        """提取采样器类型（最后一个_后的关键词）"""
        # 优先从 type 字段提取，其次从 name 字段
        sampler_name = sampler.get('type', '') or sampler.get('name', '')
        if not sampler_name:
            return ''
        
        # 按 _ 分隔，取最后一个关键词作为类型
        parts = sampler_name.split('_')
        if parts:
            return parts[-1]
        return sampler_name
    
    def _calculate_sampler_keyword_similarity(self, source_samplers: List[Dict], 
                                               target_samplers: List[Dict],
                                               source_type_stats: Dict[str, int],
                                               target_type_stats: Dict[str, int]) -> float:
        """计算采样器关键词相似度（考虑完整关键词链）"""
        if not source_samplers:
            return 100.0
        
        total_similarity = 0.0
        matched_count = 0
        
        for source_sampler in source_samplers:
            source_type = self._extract_sampler_type(source_sampler)
            if not source_type:
                continue
            
            # 在目标中找到相同类型的采样器
            best_similarity = 0.0
            for target_sampler in target_samplers:
                target_type = self._extract_sampler_type(target_sampler)
                if target_type == source_type:
                    # 计算完整关键词相似度
                    similarity = self._compare_sampler_keywords(source_sampler, target_sampler)
                    best_similarity = max(best_similarity, similarity)
            
            total_similarity += best_similarity
            matched_count += 1
        
        return (total_similarity / max(1, matched_count)) * 100.0
    
    def _compare_sampler_keywords(self, source_sampler: Dict, target_sampler: Dict) -> float:
        """比较两个采样器的完整关键词相似度"""
        source_name = source_sampler.get('type', '') or source_sampler.get('name', '')
        target_name = target_sampler.get('type', '') or target_sampler.get('name', '')
        
        if not source_name or not target_name:
            return 0.0
        
        # 提取所有关键词
        source_keywords = [kw.lower() for kw in source_name.split('_') if kw]
        target_keywords = [kw.lower() for kw in target_name.split('_') if kw]
        
        if not source_keywords:
            return 1.0
        
        # 计算关键词匹配度（源关键词有多少在目标中）
        matched = sum(1 for kw in source_keywords if kw in target_keywords)
        return matched / len(source_keywords)
    
    def _match_shader_path(self, source_path: str, target_path: str) -> float:
        """匹配着色器路径 - 修复版本"""
        if not source_path and not target_path:
            return 100.0  # 两个都为空，完全匹配
        if not source_path or not target_path:
            return 0.0    # 其中一个为空，返回0分
        
        # 首先检查路径是否完全相同
        if source_path.lower().strip() == target_path.lower().strip():
            return 100.0  # 完全相同，返回100%
        
        # 路径字符串相似度
        text_similarity = SequenceMatcher(None, source_path.lower(), target_path.lower()).ratio()
        
        # 如果文本相似度很高（>0.9），直接基于文本相似度评分
        if text_similarity > 0.9:
            return text_similarity * 100.0
        
        # 提取路径关键词
        source_keywords = self._extract_keywords(source_path, 'shader_path')
        target_keywords = self._extract_keywords(target_path, 'shader_path')
        
        # 关键词匹配度
        keyword_similarity = 0.0
        if source_keywords and target_keywords:
            common_keywords = set(source_keywords).intersection(set(target_keywords))
            max_keywords = max(len(source_keywords), len(target_keywords))
            keyword_similarity = len(common_keywords) / max_keywords
        elif not source_keywords and not target_keywords:
            # 如果都没有关键词，基于文本相似度
            keyword_similarity = text_similarity
        
        # 综合评分，给文本相似度更高权重
        return (keyword_similarity * 0.3 + text_similarity * 0.7) * 100.0
    
    def _match_sampler_count(self, source_count: int, target_count: int) -> float:
        """匹配采样器数量 - 改进版：允许目标多于源"""
        if source_count == 0 and target_count == 0:
            return 100.0
        if source_count == 0:
            return 50.0  # 源无采样器，目标有，给中等分
        
        # 允许目标多于源（源是子集）
        if target_count >= source_count:
            # 目标越接近源，分数越高；超出越多，适当扣分
            excess_ratio = (target_count - source_count) / source_count
            return max(50.0, 100.0 - excess_ratio * 30.0)  # 超出越多扣分，最低50
        else:
            # 目标少于源，严重扣分
            missing_ratio = (source_count - target_count) / source_count
            return max(0.0, 100.0 - missing_ratio * 100.0)  # 缺失多少扣多少
    
    def _match_parameters(self, source_params: List[Dict], target_params: List[Dict]) -> float:
        """
        全面匹配参数 - 考虑参数名称匹配和参数值相似度
        
        计算逻辑:
        1. 参数名称匹配度 (权重40%)
        2. 相同参数名称的参数值相似度 (权重60%)
        """
        if not source_params and not target_params:
            return 100.0
        if not source_params or not target_params:
            return 0.0
        
        # 将参数转换为字典，便于按名称查找
        source_dict = {param.get('name', ''): param for param in source_params if param.get('name')}
        target_dict = {param.get('name', ''): param for param in target_params if param.get('name')}
        
        if not source_dict and not target_dict:
            return 100.0
        if not source_dict or not target_dict:
            return 0.0
        
        # 1. 参数名称匹配度计算
        source_names = set(source_dict.keys())
        target_names = set(target_dict.keys())
        
        common_names = source_names.intersection(target_names)  # 相同的参数名
        all_names = source_names.union(target_names)            # 所有参数名
        
        # 名称匹配度：相同参数名数量 / 所有参数名数量
        name_match_ratio = len(common_names) / len(all_names) if all_names else 1.0
        
        # 2. 参数值相似度计算
        value_similarities = []
        
        for param_name in common_names:
            source_param = source_dict[param_name]
            target_param = target_dict[param_name]
            
            # 比较参数值
            value_similarity = self._compare_parameter_values(source_param, target_param)
            value_similarities.append(value_similarity)
        
        # 平均参数值相似度
        avg_value_similarity = sum(value_similarities) / len(value_similarities) if value_similarities else 0.0
        
        # 3. 综合评分
        # 如果没有相同的参数名，则只基于名称匹配度
        if not common_names:
            return name_match_ratio * 100.0
        
        # 名称匹配度40% + 参数值相似度60%
        final_score = (name_match_ratio * 0.4 + avg_value_similarity * 0.6) * 100.0
        
        return final_score
    
    def _compare_parameter_values(self, source_param: Dict, target_param: Dict) -> float:
        """
        比较两个参数的值相似度
        
        支持多种参数类型：数值、字符串、布尔值等
        """
        source_value = source_param.get('value')
        target_value = target_param.get('value')
        
        # 如果值都为空，认为完全相同
        if source_value is None and target_value is None:
            return 1.0
        
        # 如果其中一个为空，相似度为0
        if source_value is None or target_value is None:
            return 0.0
        
        # 尝试数值比较
        try:
            source_num = float(source_value)
            target_num = float(target_value)
            
            # 完全相同
            if source_num == target_num:
                return 1.0
            
            # 数值相似度计算（基于相对差异）
            if source_num == 0 and target_num == 0:
                return 1.0
            elif source_num == 0 or target_num == 0:
                # 一个为0，另一个不为0，相似度较低
                return 0.1
            else:
                # 计算相对差异
                relative_diff = abs(source_num - target_num) / max(abs(source_num), abs(target_num))
                # 转换为相似度 (差异越小，相似度越高)
                similarity = max(0.0, 1.0 - relative_diff)
                return similarity
                
        except (ValueError, TypeError):
            # 非数值类型，进行字符串比较
            source_str = str(source_value).lower().strip()
            target_str = str(target_value).lower().strip()
            
            # 完全相同
            if source_str == target_str:
                return 1.0
            
            # 字符串相似度（使用序列匹配）
            from difflib import SequenceMatcher
            similarity = SequenceMatcher(None, source_str, target_str).ratio()
            return similarity
    
    def _match_keywords(self, source_keywords: List[str], target_keywords: List[str]) -> float:
        """
        匹配关键词 - 改进版本
        
        同时考虑：
        1. 关键词精确匹配
        2. 关键词部分匹配
        3. 完整名称的字符串相似度（避免误判）
        """
        if not source_keywords and not target_keywords:
            return 100.0
        if not source_keywords or not target_keywords:
            return 0.0
        
        source_set = set(keyword.lower() for keyword in source_keywords if keyword)
        target_set = set(keyword.lower() for keyword in target_keywords if keyword)
        
        if not source_set or not target_set:
            return 0.0
        
        # 1. 精确匹配分数
        common_keywords = source_set.intersection(target_set)
        max_keywords = max(len(source_set), len(target_set))
        exact_score = (len(common_keywords) / max_keywords) * 100.0 if max_keywords > 0 else 0.0
        
        # 2. 部分匹配分数（用于关键词间的模糊匹配）
        partial_score = 0.0
        if exact_score < 50.0:
            partial_matches = 0
            total_comparisons = 0
            
            for source_kw in source_set:
                for target_kw in target_set:
                    # 过滤掉太短的关键词（避免单字符误匹配）
                    if len(source_kw) <= 1 or len(target_kw) <= 1:
                        continue
                    
                    total_comparisons += 1
                    # 检查部分匹配（包含关系或相似度）
                    if (source_kw in target_kw or target_kw in source_kw):
                        partial_matches += 1
                    elif SequenceMatcher(None, source_kw, target_kw).ratio() > 0.7:
                        partial_matches += 0.5  # 相似度匹配权重较低
            
            if total_comparisons > 0:
                partial_score = (partial_matches / total_comparisons) * 60.0  # 部分匹配最高60分
        
        # 3. 完整名称相似度（防止过度依赖关键词）
        # 将所有关键词连接成完整字符串进行比较
        source_full = "_".join(sorted(source_set))
        target_full = "_".join(sorted(target_set))
        string_similarity = SequenceMatcher(None, source_full, target_full).ratio() * 100.0
        
        # 综合评分：精确匹配50% + 部分匹配30% + 字符串相似度20%
        if exact_score >= 50.0:
            # 高精确匹配时，主要看精确度
            final_score = exact_score * 0.7 + string_similarity * 0.3
        else:
            # 低精确匹配时，综合各项指标
            final_score = exact_score * 0.5 + partial_score * 0.3 + string_similarity * 0.2
        
        return max(0.0, min(100.0, final_score))
    
    def _match_sampler_paths(self, source_samplers: List[Dict], target_samplers: List[Dict]) -> float:
        """匹配采样器路径"""
        if not source_samplers and not target_samplers:
            return 100.0
        if not source_samplers or not target_samplers:
            return 0.0   # 返回0分，由零分保护机制处理
        
        source_paths = [sampler.get('path', '') for sampler in source_samplers]
        target_paths = [sampler.get('path', '') for sampler in target_samplers]
        
        # 计算路径相似度矩阵
        similarities = []
        for source_path in source_paths:
            for target_path in target_paths:
                if source_path and target_path:
                    sim = SequenceMatcher(None, source_path.lower(), target_path.lower()).ratio()
                    similarities.append(sim)
        
        if not similarities:
            return 0.0
        
        # 返回平均相似度
        return (sum(similarities) / len(similarities)) * 100.0
    
    def _extract_material_keywords(self, material_name: str) -> List[str]:
        """
        从材质名称提取关键词 - 使用下划线分隔
        
        例如: AEG301_221_C[c2030]_BD_Fabric
        关键词: ['AEG301', '221', 'C[c2030]', 'BD', 'Fabric']
        """
        if not material_name:
            return []
        
        # 移除文件扩展名
        name = material_name
        for ext in ['.matbin', '.xml', '.matxml', '.mtd']:
            if name.lower().endswith(ext):
                name = name[:-len(ext)]
        
        # 按下划线分隔
        keywords = [kw.strip() for kw in name.split('_') if kw.strip()]
        
        # 过滤掉太短的关键词（1-2个字符的可能是无意义的）
        keywords = [kw for kw in keywords if len(kw) >= 2]
        
        return keywords
    
    def _match_material_keywords(self, source_keywords: List[str], target_keywords: List[str]) -> float:
        """
        匹配材质关键词 - 按用户需求的算法
        
        计算: 已匹配的关键词数量 / 源材质关键词数量
        例如: 源材质有5个关键词，目标包含其中1个(BD)，则相似度为 1/5 = 20%
        """
        if not source_keywords:
            return 100.0  # 源材质没有关键词，认为完全匹配
        if not target_keywords:
            return 0.0  # 目标没有关键词，无法匹配
        
        # 转为小写进行比较
        source_set = set(kw.lower() for kw in source_keywords if kw)
        target_set = set(kw.lower() for kw in target_keywords if kw)
        
        if not source_set:
            return 100.0
        
        # 计算源关键词中有多少个在目标中匹配
        matched_count = 0
        for src_kw in source_set:
            for tgt_kw in target_set:
                # 精确匹配或包含关系
                if src_kw == tgt_kw or src_kw in tgt_kw or tgt_kw in src_kw:
                    matched_count += 1
                    break  # 每个源关键词只匹配一次
        
        # 相似度 = 匹配数 / 源关键词总数
        similarity = (matched_count / len(source_set)) * 100.0
        return similarity

    def _extract_keywords(self, text: str, pattern_type: str) -> List[str]:
        """提取关键词"""
        if not text or pattern_type not in self.keyword_patterns:
            return []
        
        keywords = []
        patterns = self.keyword_patterns[pattern_type]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            keywords.extend(matches)
        
        # 去重并过滤空值
        return list(set(keyword for keyword in keywords if keyword.strip()))
    
    def _calculate_weights(self, priority_order: List[str]) -> Dict[str, float]:
        """根据优先级顺序计算权重"""
        # 如果没有提供优先级顺序，使用默认权重
        if not priority_order:
            return self.default_weights.copy()
        
        weights = {}
        
        # 首先为所有特征分配基础权重
        for feature in self.default_weights:
            weights[feature] = self.default_weights[feature]
        
        # 然后根据优先级顺序调整权重
        for i, feature in enumerate(priority_order):
            if feature in self.default_weights:
                # 优先级越高，权重增强越多
                priority_boost = (len(priority_order) - i) * 0.1
                weights[feature] = min(1.0, weights[feature] + priority_boost)
        
        # 重新规范化权重，确保总和为1.0
        total_weight = sum(weights.values())
        if total_weight > 0:
            for feature in weights:
                weights[feature] = weights[feature] / total_weight
        
        return weights
    
    def _calculate_weights_with_groups(self, priority_groups: List[List[str]]) -> Dict[str, float]:
        """根据优先级分组计算权重（支持同级优先级）"""
        if not priority_groups:
            return self.default_weights.copy()
        
        weights = {}
        
        # 首先为所有特征分配基础权重
        for feature in self.default_weights:
            weights[feature] = self.default_weights[feature] * 0.5  # 降低基础权重
        
        # 按组分配权重
        total_groups = len(priority_groups)
        for group_index, group in enumerate(priority_groups):
            # 组的权重：优先级越高权重越大
            group_weight = (total_groups - group_index) * 0.3
            # 组内权重均分
            individual_weight = group_weight / len(group) if group else 0
            
            for feature in group:
                if feature in weights:
                    weights[feature] += individual_weight
        
        # 重新规范化权重，确保总和为1.0
        total_weight = sum(weights.values())
        if total_weight > 0:
            for feature in weights:
                weights[feature] = weights[feature] / total_weight
        
        return weights
    
    def _get_library_name(self, library_id: int) -> str:
        """获取库名称（带缓存）"""
        if library_id in self._library_cache:
            return self._library_cache[library_id]
        
        try:
            libraries = self.database_manager.get_libraries()
            for lib in libraries:
                if lib['id'] == library_id:
                    name = lib['name']
                    self._library_cache[library_id] = name
                    return name
            name = f"Library {library_id}"
            self._library_cache[library_id] = name
            return name
        except:
            name = f"Library {library_id}"
            self._library_cache[library_id] = name
            return name
    
    def _quick_prefilter(self, source_details: Dict, target_material: Dict, threshold: float) -> bool:
        """
        快速预筛选 - 基于关键特征进行快速筛选：名称相似度、着色器、采样器类型
        只有通过预筛选的材质才会进行详细的相似度计算
        """
        try:
            # 1. 材质名称快速相似度检查
            source_name = source_details.get('filename', '').lower()
            target_name = target_material.get('filename', target_material.get('file_name', '')).lower()
            
            if source_name and target_name:
                # 使用快速字符串匹配算法
                name_similarity = SequenceMatcher(None, source_name, target_name).ratio()
                # 如果名称相似度很高，直接通过
                if name_similarity > 0.7:
                    return True
                # 如果名称相似度极低，可能需要其他特征补偿
                if name_similarity < 0.1:
                    # 需要更强的其他特征匹配才能通过
                    pass
            
            # 2. 着色器路径快速匹配
            source_shader = source_details.get('shader_path', '').lower()
            target_shader = target_material.get('shader_path', '').lower()
            shader_match_score = 0.0
            
            if source_shader and target_shader:
                # 提取着色器关键词进行快速比较
                source_shader_keywords = set(source_shader.split('/'))
                target_shader_keywords = set(target_shader.split('/'))
                
                # 计算关键词重合度
                common_keywords = source_shader_keywords.intersection(target_shader_keywords)
                max_keywords = max(len(source_shader_keywords), len(target_shader_keywords))
                
                if max_keywords > 0:
                    shader_match_score = len(common_keywords) / max_keywords
                    
                # 如果着色器完全不匹配，很难通过预筛选
                if shader_match_score < 0.2 and len(common_keywords) == 0:
                    return False
            
            # 3. 采样器类型快速检查（只检查基础信息，不获取完整采样器数据）
            source_samplers = source_details.get('samplers', [])
            # 对于目标材质，我们只能做基本检查，因为还没有获取详细信息
            
            # 采样器数量检查
            source_sampler_count = len(source_samplers)
            # 如果源材质有很多采样器，目标材质应该也有一些采样器的可能性
            # 但这里我们无法获取目标材质的详细采样器信息，所以暂时跳过
            
            # 4. 综合评估
            # 计算一个快速的预筛选分数
            prefilter_score = 0.0
            
            # 名称权重：40%
            if source_name and target_name:
                name_similarity = SequenceMatcher(None, source_name, target_name).ratio()
                prefilter_score += name_similarity * 0.4
            
            # 着色器权重：60%
            prefilter_score += shader_match_score * 0.6
            
            # 预筛选阈值：只有达到一定分数的材质才能通过
            # 这个阈值比最终阈值要低很多，但足以过滤掉大部分不相关的材质
            prefilter_threshold = max(0.15, threshold * 0.2)  # 预筛选阈值为最终阈值的20%，最低15%
            
            return prefilter_score >= prefilter_threshold
            
        except Exception as e:
            # 如果预筛选出错，保守地允许进入详细计算
            print(f"预筛选过程中出错: {str(e)}")
            return True
    
    def get_parameter_comparison_details(self, source_params: List[Dict], target_params: List[Dict]) -> Dict:
        """
        获取参数比较的详细信息
        
        返回包含以下信息的字典：
        - common_count: 相同参数名称的数量
        - source_only_count: 仅源材质有的参数数量
        - target_only_count: 仅目标材质有的参数数量 
        - common_params: 相同参数名称的列表
        - value_match_details: 相同参数名称的值匹配详情
        """
        if not source_params and not target_params:
            return {
                'common_count': 0,
                'source_only_count': 0,
                'target_only_count': 0,
                'common_params': [],
                'value_match_details': []
            }
        
        # 将参数转换为字典
        source_dict = {param.get('name', ''): param for param in source_params if param.get('name')}
        target_dict = {param.get('name', ''): param for param in target_params if param.get('name')}
        
        source_names = set(source_dict.keys())
        target_names = set(target_dict.keys())
        
        common_names = source_names.intersection(target_names)
        source_only_names = source_names - target_names
        target_only_names = target_names - source_names
        
        # 计算相同参数的值匹配详情
        value_match_details = []
        for param_name in common_names:
            source_param = source_dict[param_name]
            target_param = target_dict[param_name]
            value_similarity = self._compare_parameter_values(source_param, target_param)
            
            value_match_details.append({
                'name': param_name,
                'similarity': value_similarity,
                'source_value': source_param.get('value'),
                'target_value': target_param.get('value')
            })
        
        return {
            'common_count': len(common_names),
            'source_only_count': len(source_only_names),
            'target_only_count': len(target_only_names),
            'common_params': list(common_names),
            'source_only_params': list(source_only_names),
            'target_only_params': list(target_only_names),
            'value_match_details': value_match_details
        }

    def clear_cache(self):
        """清理缓存"""
        self._library_cache.clear()
        self._material_details_cache.clear()