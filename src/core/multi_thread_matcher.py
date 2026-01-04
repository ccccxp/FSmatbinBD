#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多线程材质匹配器 - 超高性能版本
"""

import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Callable
from src.core.fast_material_matcher import FastMaterialMatcher


class MultiThreadMaterialMatcher(FastMaterialMatcher):
    """多线程材质匹配器"""
    
    def __init__(self, database_manager):
        super().__init__(database_manager)
        
        # 多线程配置 - 高性能优化
        self.max_workers = 32  # 增加到32线程进行超高速处理
        self.chunk_size = 150  # 减少块大小，增加并行度
        self.progress_callback = None
        self.stop_event = threading.Event()  # 添加停止事件
        
        # 精确匹配不使用阈值boost，严格按照用户设定的阈值
        self.similarity_threshold_boost = 0.0
        
    def find_similar_materials_parallel(self, source_material: Dict, target_library_id: int, 
                                      priority_order: List[str], similarity_threshold: float,
                                      progress_callback: Optional[Callable] = None) -> List[Dict]:
        """
        并行查找相似材质
        """
        try:
            self.progress_callback = progress_callback
            
            # 获取目标库中的所有材质
            target_materials = self.database_manager.get_materials_by_library(target_library_id)
            
            # 多线程模式不再限制材质数量，处理全部材质
            
            # 启动多线程搜索（静默）
            
            # 获取源材质的详细信息
            source_details = self._get_material_details(source_material)
            
            # 精确匹配应该根据用户配置的优先级顺序计算权重
            weights = self._calculate_weights(priority_order)
            library_name = self._get_library_name(target_library_id)
            
            # 将材质分块处理
            chunks = self._split_into_chunks(target_materials, self.chunk_size)
            
            start_time = time.time()
            all_results = []
            processed_count = 0
            total_materials = len(target_materials)
            
            # 重置停止事件
            self.stop_event.clear()
            
            # 使用线程池并行处理
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交所有任务
                future_to_chunk = {
                    executor.submit(
                        self._process_chunk,
                        chunk_id,
                        chunk,
                        source_material,
                        source_details,
                        weights,
                        library_name,
                        target_library_id,  # 添加目标库ID
                        similarity_threshold,
                        self.stop_event  # 传递停止事件
                    ): (chunk_id, len(chunk))
                    for chunk_id, chunk in enumerate(chunks)
                }
                
                # 收集结果 - 优化并发处理
                completed_chunks = 0
                total_chunks = len(chunks)
                
                for future in as_completed(future_to_chunk):
                    # 检查停止信号
                    if self.stop_event.is_set():
                        print("🛑 收到停止信号，取消剩余任务")
                        # 取消未完成的任务
                        for pending_future in future_to_chunk:
                            if not pending_future.done():
                                pending_future.cancel()
                        break
                    
                    chunk_id, chunk_size = future_to_chunk[future]
                    try:
                        chunk_results = future.result(timeout=30)  # 设置超时
                        all_results.extend(chunk_results)
                        processed_count += chunk_size
                        completed_chunks += 1
                        
                        # 更新进度 - 支持GUI进度条
                        if self.progress_callback:
                            progress = (processed_count / total_materials) * 100
                            self.progress_callback(progress)
                        
                        # 大幅减少输出频率 - 只在完成时输出
                        if completed_chunks == total_chunks:
                            print(f"✅ 所有线程完成，总计找到 {len(all_results)} 个结果")
                            
                    except Exception as e:
                        # 静默处理错误，不输出到控制台
                        continue
            
            # 超高速排序 - 移除输出，直接排序
            if all_results:
                # 对于大量结果，使用并行排序优化
                if len(all_results) > 1000:
                    # 分块排序后合并（适合大数据集）
                    chunk_size = len(all_results) // 4
                    chunks = [all_results[i:i + chunk_size] for i in range(0, len(all_results), chunk_size)]
                    
                    with ThreadPoolExecutor(max_workers=4) as sort_executor:
                        sorted_chunks = list(sort_executor.map(
                            lambda chunk: sorted(chunk, key=lambda x: x['similarity'], reverse=True), 
                            chunks
                        ))
                    
                    # 合并已排序的块
                    import heapq
                    all_results = list(heapq.merge(*sorted_chunks, key=lambda x: x['similarity'], reverse=True))
                else:
                    # 小数据集直接排序
                    all_results.sort(key=lambda x: x['similarity'], reverse=True)
            
            results = all_results  # 返回所有符合阈值的结果
            
            elapsed = time.time() - start_time
            print(f"并行匹配完成: 处理了{processed_count}个材质，找到{len(results)}个匹配结果，耗时{elapsed:.1f}秒")
            print(f"平均速度: {processed_count/elapsed:.0f} 材质/秒")
            
            return results
            
        except Exception as e:
            raise Exception(f"并行材质匹配失败: {str(e)}")
    
    def _split_into_chunks(self, materials: List[Dict], chunk_size: int) -> List[List[Dict]]:
        """将材质列表分割成块"""
        chunks = []
        for i in range(0, len(materials), chunk_size):
            chunks.append(materials[i:i + chunk_size])
        return chunks
    
    def _process_chunk(self, chunk_id: int, chunk: List[Dict], source_material: Dict,
                      source_details: Dict, weights: Dict, library_name: str,
                      target_library_id: int, similarity_threshold: float, 
                      stop_event: threading.Event = None) -> List[Dict]:
        """处理一个材质块"""
        results = []
        
        try:
            for i, target_material in enumerate(chunk):
                # 检查停止信号（每10个材质检查一次，减少开销）
                if stop_event and i % 10 == 0 and stop_event.is_set():
                    print(f"🛑 线程 {chunk_id} 收到停止信号")
                    break
                
                try:
                    # 跳过同一个材质
                    if (source_material.get('id') == target_material.get('id') and 
                        source_material.get('library_id') == target_material.get('library_id')):
                        continue
                    
                    # 精确匹配不使用预筛选，进行全参数匹配
                    # 移除预筛选，确保不遗漏任何可能的匹配
                    
                    # 计算详细相似度
                    similarity_info = self._calculate_similarity_optimized(
                        source_details, 
                        target_material, 
                        weights
                    )
                    
                    total_similarity = similarity_info['total']
                    
                    # 静默处理
                    
                    # 检查是否满足阈值
                    if total_similarity >= similarity_threshold:
                        # 获取目标材质详情用于计算数量
                        target_details = self._get_material_details(target_material)
                        
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
                            'target_library_id': target_library_id,  # 添加目标库ID用于跳转
                            'source_material': source_material,  # 添加源材质信息
                            'target_material': target_material   # 添加目标材质信息（为了统一）
                        })
                        
                        # 如果这个块已经找到足够的结果，停止处理
                        if len(results) >= self.max_results_per_search // self.max_workers:
                            break
                        
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"处理块 {chunk_id} 时出错: {e}")
        
        return results
    
    def stop_matching(self):
        """停止当前匹配进程"""
        if hasattr(self, 'stop_event'):
            self.stop_event.set()
            print("🛑 多线程匹配已请求停止")


class AsyncMaterialMatcher:
    """异步材质匹配器 - 用于GUI"""
    
    def __init__(self, database_manager):
        self.matcher = MultiThreadMaterialMatcher(database_manager)
        self.stop_event = threading.Event()
        self.current_thread = None
        
    def start_matching(self, source_material: Dict, target_library_id: int,
                      priority_order: List[str], similarity_threshold: float,
                      progress_callback: Optional[Callable] = None,
                      completion_callback: Optional[Callable] = None):
        """启动异步匹配"""
        # 停止之前的匹配
        self.stop_matching()
        
        # 重置停止事件
        self.stop_event.clear()
        
        # 启动新的匹配线程
        self.current_thread = threading.Thread(
            target=self._run_matching,
            args=(source_material, target_library_id, priority_order, 
                  similarity_threshold, progress_callback, completion_callback),
            daemon=True
        )
        self.current_thread.start()
        
    def stop_matching(self):
        """停止当前匹配"""
        if self.current_thread and self.current_thread.is_alive():
            self.stop_event.set()
            self.current_thread.join(timeout=1.0)
            
    def _run_matching(self, source_material: Dict, target_library_id: int,
                     priority_order: List[str], similarity_threshold: float,
                     progress_callback: Optional[Callable] = None,
                     completion_callback: Optional[Callable] = None):
        """运行匹配任务"""
        try:
            # 包装进度回调以检查停止事件
            def wrapped_progress_callback(progress, processed, total):
                if self.stop_event.is_set():
                    raise InterruptedError("匹配被用户取消")
                if progress_callback:
                    progress_callback(progress, processed, total)
            
            results = self.matcher.find_similar_materials_parallel(
                source_material, target_library_id, priority_order, 
                similarity_threshold, wrapped_progress_callback
            )
            
            if not self.stop_event.is_set() and completion_callback:
                completion_callback(results, None)
                
        except InterruptedError as e:
            print(f"匹配被中断: {e}")
            if completion_callback:
                completion_callback([], str(e))
        except Exception as e:
            print(f"匹配失败: {e}")
            if completion_callback:
                completion_callback([], str(e))

    def find_similar_materials_multi_thread(self, source_material: Dict, target_library_id: int, 
                                           priority_order: List[str], similarity_threshold: float,
                                           skip_prefilter: bool = False) -> List[Dict]:
        """
        多线程搜索的同步接口，支持跳过预筛选
        """
        if skip_prefilter:
            print("多线程精确搜索 - 跳过所有预筛选")
            # 临时修改预筛选设置
            original_method = self._strict_prefilter
            self._strict_prefilter = lambda *args: True  # 跳过预筛选
            
        try:
            result = self.find_similar_materials_parallel(
                source_material, target_library_id, priority_order, similarity_threshold
            )
            return result
        finally:
            if skip_prefilter:
                # 恢复原来的预筛选方法
                self._strict_prefilter = original_method


# 创建别名以保持向后兼容
MultiThreadMatcher = MultiThreadMaterialMatcher