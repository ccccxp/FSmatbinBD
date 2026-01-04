#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高性能材质匹配器 - 超级优化版本
"""

from typing import Dict, List, Optional
from src.core.material_matcher import MaterialMatcher
import time

class FastMaterialMatcher(MaterialMatcher):
    """高性能材质匹配器"""
    
    def __init__(self, database_manager):
        super().__init__(database_manager)
        
        # 性能配置
        self.max_results_per_search = 10000  # 大幅提高限制，主要依靠阈值过滤
        self.similarity_threshold_boost = 0.0  # 不提高阈值，确保找到所有符合条件的材质
    
    def find_similar_materials_fast(self, source_material: Dict, target_library_id: int, 
                                  priority_order: List[str], similarity_threshold: float) -> List[Dict]:
        """
        两层搜索策略：
        1. 快速预筛选搜索
        2. 如果结果为0，进行精确搜索
        """
        print(f"🎯 FastMaterialMatcher.find_similar_materials_fast() 被调用！类型: {type(self)}")
        print(f"🎯 方法路径: {self.__class__.__module__}.{self.__class__.__name__}")
        
        # 检查是否是正确的实例
        if "MultiThreadMaterialMatcher" in str(type(self)):
            print("⚠️  注意：这是MultiThreadMaterialMatcher实例，可能有方法冲突！")
        try:
            print(f"\n🔍 === 开始两层搜索策略 === 🔍")
            print(f"📝 源材质: {source_material.get('filename', 'Unknown')}")
            print(f"📊 相似度阈值: {similarity_threshold}%")
            
            # 第一层：快速预筛选搜索
            print("🚀 第一层：执行快速预筛选搜索...")
            results = self._perform_fast_search(source_material, target_library_id, 
                                              priority_order, similarity_threshold)
            
            print(f"🎯 第一层搜索结果: {len(results)} 个匹配")
            
            # 如果快速搜索返回0个结果，进行第二层精确搜索
            if len(results) == 0:
                print("� �📢 第一层未找到结果，启动第二层精确搜索...")
                results = self._perform_precise_search(source_material, target_library_id, 
                                                     priority_order, similarity_threshold)
                print(f"🎯 第二层搜索结果: {len(results)} 个匹配")
            else:
                print(f"✅ 第一层找到足够结果，跳过第二层搜索")
            
            print(f"🏁 === 两层搜索完成，最终结果: {len(results)} 个 === 🏁")
            return results
            
        except Exception as e:
            raise Exception(f"材质匹配失败: {str(e)}")
    
    def _perform_fast_search(self, source_material: Dict, target_library_id: int, 
                           priority_order: List[str], similarity_threshold: float) -> List[Dict]:
        """
        第一层：快速预筛选搜索
        """
        try:
            # 获取目标库中的所有材质
            target_materials = self.database_manager.get_materials_by_library(target_library_id)
            
            print(f"快速预筛选: 处理 {len(target_materials)} 个材质...")
            
            # 获取源材质的详细信息
            source_details = self._get_material_details(source_material)
            
            results = []
            processed_count = 0
            progress_interval = max(1, len(target_materials) // 20)  # 每5%显示进度
            
            # 使用用户配置的优先级权重
            weights = self._calculate_weights(priority_order)
            library_name = self._get_library_name(target_library_id)
            
            start_time = time.time()
            
            # 预筛选统计
            prefilter_passed = 0
            prefilter_total = 0
            
            for target_material in target_materials:
                try:
                    processed_count += 1
                    
                    # 显示进度
                    if processed_count % progress_interval == 0:
                        elapsed = time.time() - start_time
                        progress = (processed_count / len(target_materials)) * 100
                        rate = processed_count / elapsed if elapsed > 0 else 0
                        print(f"快速预筛选进度: {progress:.1f}% ({processed_count}/{len(target_materials)}) - 速度: {rate:.0f}材质/秒")
                    
                    # 跳过同一个材质
                    if (source_material.get('id') == target_material.get('id') and 
                        source_material.get('library_id') == target_material.get('library_id')):
                        continue
                    
                    # 严格的快速预筛选 - 只通过明显相关的材质
                    prefilter_total += 1
                    prefilter_result = self._strict_prefilter(source_details, target_material, similarity_threshold)
                    
                    # 调试前几个材质的预筛选结果
                    if prefilter_total <= 5:
                        target_name = target_material.get('filename', 'Unknown')
                        print(f"  调试预筛选 {prefilter_total}: {target_name} -> {'通过' if prefilter_result else '被排除'}")
                    
                    if not prefilter_result:
                        continue
                    prefilter_passed += 1
                    
                    # 计算详细相似度
                    target_details = self._get_material_details(target_material)
                    similarity_info = self._calculate_similarity_optimized(
                        source_details, 
                        target_details, 
                        weights
                    )
                    
                    total_similarity = similarity_info['total']
                    
                    # 检查是否满足阈值
                    if total_similarity >= similarity_threshold:
                        results.append({
                            'material': target_material,
                            'similarity': total_similarity,
                            'details': similarity_info['details'],
                            'library_name': library_name
                        })
                        
                        # 早期退出
                        if len(results) >= self.max_results_per_search:
                            print(f"快速预筛选找到 {self.max_results_per_search} 个匹配结果，停止搜索")
                            break
                        
                except Exception as e:
                    continue
            
            # 按相似度排序
            results.sort(key=lambda x: x['similarity'], reverse=True)
            
            elapsed = time.time() - start_time
            prefilter_rate = (prefilter_passed / prefilter_total * 100) if prefilter_total > 0 else 0
            print(f"快速预筛选完成: 处理了{processed_count}个材质，预筛选通过{prefilter_passed}/{prefilter_total}({prefilter_rate:.1f}%)，找到{len(results)}个匹配结果，耗时{elapsed:.1f}秒")
            
            return results
            
        except Exception as e:
            raise Exception(f"快速预筛选失败: {str(e)}")
    
    def _perform_precise_search(self, source_material: Dict, target_library_id: int, 
                              priority_order: List[str], similarity_threshold: float) -> List[Dict]:
        """
        第二层：精确搜索 - 从头开始搜索全部材质，降低阈值以找到潜在匹配
        """
        print("🔥 启动第二层精确搜索 - 从头开始搜索全部材质...")
        
        # 第二层搜索关键策略：
        # 1. 降低相似度阈值以找到更多潜在匹配
        # 2. 从全部材质开始搜索，不做任何预筛选
        # 3. 使用用户定义的权重进行精确计算
        
        # 降低相似度阈值 - 从原阈值降到更宽松的水平
        relaxed_threshold = max(0.1, similarity_threshold * 0.3)  # 降到原来的30%，最低10%
        print(f"🎯 降低相似度阈值: {similarity_threshold}% -> {relaxed_threshold}%")
        
        try:
            # 直接使用单线程进行全面搜索，避免多线程复杂性
            results = self._single_thread_precise_search(source_material, target_library_id, 
                                                       priority_order, relaxed_threshold)
            print(f"🎊 第二层精确搜索完成: 找到{len(results)}个匹配结果")
            return results
            
        except Exception as e:
            print(f"❌ 精确搜索失败: {str(e)}")
            return []
    
    def _single_thread_precise_search(self, source_material: Dict, target_library_id: int, 
                                    priority_order: List[str], similarity_threshold: float) -> List[Dict]:
        """
        单线程精确搜索 - 从头开始搜索全部材质，不使用任何预筛选
        """
        print("🔍 第二层精确搜索：从头开始搜索全部材质，不使用任何预筛选...")
        
        target_materials = self.database_manager.get_materials_by_library(target_library_id)
        print(f"📊 目标材质库总数: {len(target_materials)} 个材质")
        
        source_details = self._get_material_details(source_material)
        weights = self._calculate_weights(priority_order)  # 使用用户定义的完整权重
        library_name = self._get_library_name(target_library_id)
        
        results = []
        processed_count = 0
        start_time = time.time()
        progress_interval = max(100, len(target_materials) // 20)  # 显示20次进度
        
        print(f"💡 使用权重配置: {weights}")
        print(f"🎯 相似度阈值: {similarity_threshold}")
        
        for target_material in target_materials:
            try:
                processed_count += 1
                
                # 显示进度
                if processed_count % progress_interval == 0:
                    elapsed = time.time() - start_time
                    progress = (processed_count / len(target_materials)) * 100
                    rate = processed_count / elapsed if elapsed > 0 else 0
                    print(f"🔄 精确搜索进度: {progress:.1f}% ({processed_count}/{len(target_materials)}) - 速度: {rate:.0f}材质/秒")
                
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
                
                # 检查是否满足阈值
                if total_similarity >= similarity_threshold:
                    results.append({
                        'material': target_material,
                        'similarity': total_similarity,
                        'details': similarity_info['details'],
                        'library_name': library_name
                    })
                    
                    # 显示找到的匹配
                    if len(results) <= 10:  # 只显示前10个匹配
                        target_name = target_material.get('filename', 'Unknown')
                        print(f"  ✅ 找到匹配 #{len(results)}: {target_name} (相似度: {total_similarity:.1f}%)")
                        
            except Exception as e:
                continue
        
        # 按相似度排序
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        elapsed = time.time() - start_time
        print(f"✅ 第二层精确搜索完成: 处理{processed_count}个材质，找到{len(results)}个匹配结果，耗时{elapsed:.1f}秒")
        
        return results
    
    def _strict_prefilter(self, source_details: Dict, target_material: Dict, threshold: float) -> bool:
        """
        严格预筛选 - 只通过明显相关的材质，避免无关材质干扰
        """
        try:
            # 严格预筛选：检查材质名称、着色器路径、采样器类型的基本相似性
            
            # 1. 检查材质名称相似性
            source_filename = source_details.get('filename', '').lower()
            target_filename = target_material.get('filename', '').lower()
            
            # 提取文件名的主要部分（去掉扩展名）
            source_name = source_filename.replace('.matbin', '').replace('.xml', '')
            target_name = target_filename.replace('.matbin', '').replace('.xml', '')
            
            # 检查名称相似性
            name_similarity = self._calculate_name_similarity(source_name, target_name)
            
            # 2. 检查着色器路径相似性
            source_shader = source_details.get('shader_path', '')
            target_shader = target_material.get('shader_path', '')
            shader_similarity = self._calculate_shader_similarity(source_shader, target_shader)
            
            # 3. 检查采样器类型相似性
            sampler_similarity = self._calculate_sampler_type_similarity(source_details, target_material)
            
            # 4. 组合判断 - 至少一个维度要有一定相似性
            min_name_threshold = 0.3      # 名称相似度至少30%
            min_shader_threshold = 0.2    # 着色器相似度至少20%
            min_sampler_threshold = 0.15  # 采样器类型相似度至少15%
            
            # 任何一个维度达标就通过
            if (name_similarity >= min_name_threshold or 
                shader_similarity >= min_shader_threshold or 
                sampler_similarity >= min_sampler_threshold):
                return True
            
            # 5. 特殊情况：如果阈值很低（<=15%），放宽限制
            if threshold <= 15.0:
                if (name_similarity >= 0.1 or 
                    shader_similarity >= 0.1 or 
                    sampler_similarity >= 0.05):
                    return True
            
            return False
            
        except Exception as e:
            # 预筛选失败时保守通过
            return True
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """
        计算材质名称的相似度
        """
        if not name1 or not name2:
            return 0.0
        
        # 简单的子串匹配
        if name1 == name2:
            return 1.0
        
        if name1 in name2 or name2 in name1:
            return 0.8
        
        # 检查共同的词汇部分
        words1 = set(name1.lower().replace('_', ' ').replace('[', ' ').replace(']', ' ').split())
        words2 = set(name2.lower().replace('_', ' ').replace('[', ' ').replace(']', ' ').split())
        
        if not words1 or not words2:
            return 0.0
        
        common_words = words1.intersection(words2)
        total_words = words1.union(words2)
        
        return len(common_words) / len(total_words) if total_words else 0.0
    
    def _calculate_shader_similarity(self, shader1: str, shader2: str) -> float:
        """
        计算着色器路径的相似度
        """
        if not shader1 or not shader2:
            return 0.0
        
        if shader1 == shader2:
            return 1.0
        
        # 提取着色器名称（最后的文件名部分）
        name1 = shader1.split('\\')[-1].split('/')[-1].lower()
        name2 = shader2.split('\\')[-1].split('/')[-1].lower()
        
        if name1 == name2:
            return 0.9
        
        # 检查是否包含相同的着色器类型关键词
        shader_types = ['detailblend', 'amsn', 'cloth', 'metal', 'skin', 'hair']
        type1 = None
        type2 = None
        
        for shader_type in shader_types:
            if shader_type in name1.lower():
                type1 = shader_type
            if shader_type in name2.lower():
                type2 = shader_type
        
        if type1 and type2 and type1 == type2:
            return 0.6
        
        return 0.0
    
    def _calculate_sampler_type_similarity(self, source_details: Dict, target_material: Dict) -> float:
        """
        计算采样器类型的相似度
        """
        try:
            # 获取源材质的采样器类型
            source_samplers = source_details.get('samplers', [])
            if not source_samplers:
                return 0.0
            
            # 需要从target_material获取采样器信息
            target_details = self._get_material_details(target_material)
            target_samplers = target_details.get('samplers', [])
            
            if not target_samplers:
                return 0.0
            
            # 提取采样器类型关键词
            source_types = set()
            target_types = set()
            
            for sampler in source_samplers:
                sampler_type = sampler.get('type', '').lower()
                if sampler_type:
                    # 提取关键词：AlbedoMap, NormalMap, MetallicMap等
                    for keyword in ['albedo', 'normal', 'metallic', 'roughness', 'specular', 'diffuse', 'ao', 'height', 'emission']:
                        if keyword in sampler_type:
                            source_types.add(keyword)
                    
                    # 提取纹理类型：Texture2D, TextureCube等
                    if 'texture2d' in sampler_type:
                        source_types.add('texture2d')
                    elif 'texturecube' in sampler_type:
                        source_types.add('texturecube')
            
            for sampler in target_samplers:
                sampler_type = sampler.get('type', '').lower()
                if sampler_type:
                    # 提取关键词
                    for keyword in ['albedo', 'normal', 'metallic', 'roughness', 'specular', 'diffuse', 'ao', 'height', 'emission']:
                        if keyword in sampler_type:
                            target_types.add(keyword)
                    
                    # 提取纹理类型
                    if 'texture2d' in sampler_type:
                        target_types.add('texture2d')
                    elif 'texturecube' in sampler_type:
                        target_types.add('texturecube')
            
            # 计算相似度
            if not source_types and not target_types:
                return 0.5  # 都没有采样器类型，给个中等分数
            
            if not source_types or not target_types:
                return 0.0
            
            # Jaccard相似度
            intersection = source_types.intersection(target_types)
            union = source_types.union(target_types)
            
            return len(intersection) / len(union) if union else 0.0
            
        except Exception as e:
            # 计算失败时返回0，让其他维度起作用
            return 0.0
    
    def _extract_common_shader_keywords(self, shader_path: str) -> List[str]:
        """
        从着色器路径提取通用关键词，忽略特殊的DLC或角色名称
        """
        if not shader_path:
            return []
        
        # 转换为小写并分割路径
        path_lower = shader_path.lower().replace('\\', '/')
        parts = [part for part in path_lower.split('/') if part]
        
        # 通用材质类型关键词
        common_keywords = []
        material_types = ['cloth', 'metal', 'skin', 'hair', 'fabric', 'leather', 'wood', 'stone', 'glass', 'plastic']
        shader_types = ['hlsl', 'spx', 'shader', 'mtl', 'mat']
        path_indicators = ['shaders', 'material', 'materials', 'outputdata', 'sat']
        
        # 提取材质类型关键词
        for part in parts:
            # 检查是否包含材质类型
            for mat_type in material_types:
                if mat_type in part:
                    common_keywords.append(mat_type)
            
            # 检查是否包含着色器类型
            for shader_type in shader_types:
                if part.endswith(f'.{shader_type}') or shader_type in part:
                    common_keywords.append(shader_type)
                    
            # 检查是否包含路径指示词
            for indicator in path_indicators:
                if indicator in part:
                    common_keywords.append(indicator)
        
        # 去重并返回
        return list(set(common_keywords))
    

    
    def _calculate_similarity_optimized(self, source_details: Dict, target_details: Dict, 
                                      weights: Dict[str, float]) -> Dict:
        """
        优化的相似度计算方法 - 直接使用原始权重，不做任何修改
        """
        # 直接调用父类方法，不做任何权重调整或保护
        return super()._calculate_similarity_optimized(source_details, target_details, weights)
    
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
        计算快速匹配专用权重 - 优先名称、着色器路径、采样器类型
        """
        return {
            'material_keywords': 0.35,    # 材质名称权重最高
            'shader_path': 0.30,          # 着色器路径权重其次 
            'sampler_types': 0.20,        # 采样器类型权重第三
            'sampler_paths': 0.10,        # 采样器路径权重较低
            'parameters': 0.05,           # 参数权重最低
            'sampler_count': 0.0          # 采样器数量权重为0（快速模式忽略）
        }