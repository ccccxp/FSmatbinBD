#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证GUI Key值显示修复"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.database import MaterialDatabase

def test_gui_key_display():
    """验证GUI应该显示的Key值数据"""
    print("=== 验证GUI Key值显示数据 ===")
    
    db = MaterialDatabase()
    
    # 获取第一个材质
    materials = db.search_materials()[:1]
    if not materials:
        print("没有材质数据")
        return
    
    material_id = materials[0]['id']
    material_data = db.get_material_detail(material_id)
    
    print(f"材质: {material_data.get('filename', 'UNKNOWN')}")
    print(f"材质文件: {material_data.get('file_name', 'UNKNOWN')}")
    
    # 检查基本信息Key值字段
    print(f"\n=== 基本信息Key值 ===")
    print(f"key_value字段: {material_data.get('key_value', 'MISSING')}")
    print(f"key字段 (旧): {material_data.get('key', 'MISSING')}")
    
    # 检查参数Key值字段
    print(f"\n=== 参数Key值 (前3个) ===")
    if material_data.get('params'):
        for i, param in enumerate(material_data['params'][:3]):
            param_name = param.get('name', f'参数{i+1}')
            key_value = param.get('key_value', 'MISSING')
            old_key = param.get('key', 'MISSING')
            print(f"{param_name}:")
            print(f"  key_value字段: {key_value}")
            print(f"  key字段 (旧): {old_key}")
    
    # 检查数据库字段是否正确
    print(f"\n=== 数据库字段验证 ===")
    import sqlite3
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        
        # 检查材质表key_value字段
        cursor.execute("SELECT key_value FROM materials WHERE id = ?", (material_id,))
        result = cursor.fetchone()
        if result:
            print(f"数据库材质key_value: {result[0]}")
        
        # 检查参数表key_value字段
        cursor.execute("SELECT name, key_value FROM material_params WHERE material_id = ? LIMIT 3", (material_id,))
        param_results = cursor.fetchall()
        print(f"数据库参数key_value:")
        for name, key_value in param_results:
            print(f"  {name}: {key_value}")

if __name__ == "__main__":
    try:
        test_gui_key_display()
    except Exception as e:
        print(f"验证过程中出错: {e}")
        import traceback
        traceback.print_exc()