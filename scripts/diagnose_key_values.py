#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断键值丢失问题"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.database import MaterialDatabase
from src.core.xml_parser import MaterialXMLParser

def diagnose_key_values():
    """诊断键值存储和导出问题"""
    print("=== 键值诊断工具 ===")
    
    # 1. 检查数据库中的键值存储
    print("\n1. 检查数据库中的键值存储")
    db = MaterialDatabase()
    
    # 查找CXP材质
    materials = db.search_materials(keyword='CXP')
    print(f"找到包含'CXP'的材质: {len(materials)}个")
    
    if materials:
        material_id = materials[0]['id']
        print(f"检查材质ID: {material_id}")
        
        # 获取材质详情
        material = db.get_material_detail(material_id)
        print(f"材质名称: {material.get('name', 'UNKNOWN')}")
        print(f"材质键值: {material.get('key_value', 'MISSING')}")
        
        # 检查参数键值
        if material.get('params'):
            print(f"参数数量: {len(material['params'])}")
            for i, param in enumerate(material['params'][:3]):  # 只显示前3个
                print(f"  参数{i+1} 键值: {param.get('key_value', 'MISSING')}")
        
        # 检查采样器键值
        if material.get('samplers'):
            print(f"采样器数量: {len(material['samplers'])}")
            for i, sampler in enumerate(material['samplers'][:3]):  # 只显示前3个
                print(f"  采样器{i+1} 键值: {sampler.get('key_value', 'MISSING')}")
    
    # 2. 检查数据库表结构
    print("\n2. 检查数据库表结构")
    import sqlite3
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        
        # 检查材质表
        cursor.execute("PRAGMA table_info(materials)")
        material_columns = cursor.fetchall()
        print("材质表字段:")
        for col in material_columns:
            if 'key' in col[1].lower():
                print(f"  {col[1]} ({col[2]})")
        
        # 检查参数表
        cursor.execute("PRAGMA table_info(material_params)")
        param_columns = cursor.fetchall()
        print("参数表字段:")
        for col in param_columns:
            if 'key' in col[1].lower():
                print(f"  {col[1]} ({col[2]})")
        
        # 检查采样器表
        cursor.execute("PRAGMA table_info(material_samplers)")
        sampler_columns = cursor.fetchall()
        print("采样器表字段:")
        for col in sampler_columns:
            if 'key' in col[1].lower():
                print(f"  {col[1]} ({col[2]})")
        
        # 3. 检查实际数据
        print("\n3. 检查实际数据中的键值")
        if materials:
            # 查找实际的材质数据
            cursor.execute("SELECT file_name, key_value FROM materials WHERE file_name LIKE '%CXP%' LIMIT 3")
            materials_data = cursor.fetchall()
            print("材质键值:")
            for name, key_value in materials_data:
                print(f"  {name}: {key_value}")
            
            if materials_data:
                # 获取第一个材质的ID
                cursor.execute("SELECT id FROM materials WHERE file_name LIKE '%CXP%' LIMIT 1")
                result = cursor.fetchone()
                if result:
                    material_id = result[0]
                    
                    cursor.execute("SELECT name, key_value FROM material_params WHERE material_id = ? LIMIT 3", (material_id,))
                    params_data = cursor.fetchall()
                    print("参数键值:")
                    for param_name, key_value in params_data:
                        print(f"  {param_name}: {key_value}")
                    
                    cursor.execute("SELECT type, key_value FROM material_samplers WHERE material_id = ? LIMIT 3", (material_id,))
                    samplers_data = cursor.fetchall()
                    print("采样器键值:")
                    for sampler_type, key_value in samplers_data:
                        print(f"  {sampler_type}: {key_value}")
        else:
            # 如果搜索没有找到CXP，查看所有材质
            cursor.execute("SELECT file_name, key_value FROM materials LIMIT 3")
            materials_data = cursor.fetchall()
            print("所有材质键值(前3个):")
            for name, key_value in materials_data:
                print(f"  {name}: {key_value}")
            
            if materials_data:
                # 获取第一个材质的ID
                cursor.execute("SELECT id FROM materials LIMIT 1")
                result = cursor.fetchone()
                if result:
                    material_id = result[0]
                    
                    cursor.execute("SELECT name, key_value FROM material_params WHERE material_id = ? LIMIT 3", (material_id,))
                    params_data = cursor.fetchall()
                    print("参数键值:")
                    for param_name, key_value in params_data:
                        print(f"  {param_name}: {key_value}")
                    
                    cursor.execute("SELECT type, key_value FROM material_samplers WHERE material_id = ? LIMIT 3", (material_id,))
                    samplers_data = cursor.fetchall()
                    print("采样器键值:")
                    for sampler_type, key_value in samplers_data:
                        print(f"  {sampler_type}: {key_value}")

if __name__ == "__main__":
    try:
        diagnose_key_values()
    except Exception as e:
        print(f"诊断过程中出错: {e}")
        import traceback
        traceback.print_exc()