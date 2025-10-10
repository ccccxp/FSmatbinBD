#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试采样器路径搜索功能"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.database import MaterialDatabase

def test_sampler_search():
    """测试采样器搜索功能"""
    print("=== 测试采样器搜索功能 ===")
    
    db = MaterialDatabase()
    
    # 1. 测试采样器类型搜索
    print("\n1. 测试采样器类型搜索")
    search_criteria = {
        'sampler_search': [{'type': 'Texture2D'}],
        'fuzzy_search': True,
        'match_mode': 'any'
    }
    
    results = db.advanced_search_materials(search_criteria)
    print(f"搜索 'Texture2D' 类型的采样器，找到 {len(results)} 个材质")
    
    if results:
        material = db.get_material_detail(results[0]['id'])
        print(f"第一个材质 '{material['filename']}' 的采样器:")
        for sampler in material.get('samplers', [])[:3]:
            print(f"  类型: {sampler.get('type', 'UNKNOWN')}")
            print(f"  路径: {sampler.get('path', 'UNKNOWN')}")
    
    # 2. 测试采样器路径搜索
    print(f"\n2. 测试采样器路径搜索")
    search_criteria = {
        'sampler_search': [{'path': '.tif'}],
        'fuzzy_search': True,
        'match_mode': 'any'
    }
    
    results = db.advanced_search_materials(search_criteria)
    print(f"搜索包含 '.tif' 的采样器路径，找到 {len(results)} 个材质")
    
    if results:
        material = db.get_material_detail(results[0]['id'])
        print(f"第一个材质 '{material['filename']}' 的采样器:")
        for sampler in material.get('samplers', [])[:3]:
            path = sampler.get('path', 'UNKNOWN')
            print(f"  路径: {path}")
    
    # 3. 测试特定文件名搜索
    print(f"\n3. 测试特定文件名搜索")
    search_criteria = {
        'sampler_search': [{'path': 'AET001'}],
        'fuzzy_search': True,
        'match_mode': 'any'
    }
    
    results = db.advanced_search_materials(search_criteria)
    print(f"搜索包含 'AET001' 的采样器路径，找到 {len(results)} 个材质")
    
    if results:
        material = db.get_material_detail(results[0]['id'])
        print(f"第一个材质 '{material['filename']}' 的采样器:")
        for sampler in material.get('samplers', [])[:3]:
            path = sampler.get('path', 'UNKNOWN')
            if 'AET001' in path:
                print(f"  匹配路径: {path}")
    
    # 4. 组合搜索测试
    print(f"\n4. 组合搜索测试（采样器类型 + 路径）")
    search_criteria = {
        'sampler_search': [
            {'type': 'AlbedoMap'},
            {'path': '.tif'}
        ],
        'fuzzy_search': True,
        'match_mode': 'any'  # 匹配任一条件
    }
    
    results = db.advanced_search_materials(search_criteria)
    print(f"搜索包含 'AlbedoMap' 类型或 '.tif' 路径的采样器，找到 {len(results)} 个材质")

if __name__ == "__main__":
    try:
        test_sampler_search()
    except Exception as e:
        print(f"测试过程中出错: {e}")
        import traceback
        traceback.print_exc()