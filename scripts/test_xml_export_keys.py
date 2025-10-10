#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试XML导出键值问题"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.database import MaterialDatabase
from src.core.xml_parser import MaterialXMLParser

def test_xml_export_with_keys():
    """测试XML导出是否包含所有键值"""
    print("=== 测试XML导出键值 ===")
    
    # 1. 从数据库获取材质数据
    db = MaterialDatabase()
    
    # 获取第一个材质进行测试
    materials = db.search_materials()
    if not materials:
        print("数据库中没有材质数据")
        return
    
    # 只使用第一个材质
    materials = materials[:1]
    
    material_id = materials[0]['id']
    material_name = materials[0].get('file_name', materials[0].get('name', 'UNKNOWN'))
    print(f"测试材质ID: {material_id}, 名称: {material_name}")
    
    # 获取完整材质数据
    material_data = db.get_material_detail(material_id)
    
    print(f"\n原始数据库材质键值: {material_data.get('key_value', 'MISSING')}")
    print(f"参数数量: {len(material_data.get('params', []))}")
    print(f"采样器数量: {len(material_data.get('samplers', []))}")
    
    # 显示前几个参数和采样器的Key值
    if material_data.get('params'):
        print("\n前3个参数的Key值:")
        for i, param in enumerate(material_data['params'][:3]):
            print(f"  {param.get('name', 'UNKNOWN')}: {param.get('key_value', 'MISSING')}")
    
    if material_data.get('samplers'):
        print("\n前3个采样器的Key值:")
        for i, sampler in enumerate(material_data['samplers'][:3]):
            print(f"  {sampler.get('type', 'UNKNOWN')}: {sampler.get('key_value', 'MISSING')}")
    
    # 2. 导出XML
    parser = MaterialXMLParser()
    test_output_path = os.path.join(os.getcwd(), "test_output_with_keys.xml")
    
    success = parser.export_material_to_xml(material_data, test_output_path)
    
    if success:
        print(f"\n导出成功: {test_output_path}")
        
        # 3. 读取并检查导出的XML文件
        print("\n检查导出的XML文件内容:")
        try:
            with open(test_output_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            # 检查主Key
            if f"<Key>{material_data.get('key_value', '')}</Key>" in xml_content:
                print("✓ 材质主Key导出正确")
            else:
                print("✗ 材质主Key导出错误或缺失")
            
            # 计算Key标签数量
            key_count = xml_content.count('<Key>')
            expected_count = 1 + len(material_data.get('params', [])) + len(material_data.get('samplers', []))
            print(f"XML中Key标签数量: {key_count}, 期望数量: {expected_count}")
            
            if key_count == expected_count:
                print("✓ Key数量正确")
            else:
                print("✗ Key数量不匹配")
            
            # 检查前几行内容
            lines = xml_content.split('\n')
            print(f"\nXML文件前10行:")
            for i, line in enumerate(lines[:10]):
                print(f"  {i+1}: {line}")
                
        except Exception as e:
            print(f"读取XML文件失败: {e}")
    else:
        print("导出失败")

if __name__ == "__main__":
    try:
        test_xml_export_with_keys()
    except Exception as e:
        print(f"测试过程中出错: {e}")
        import traceback
        traceback.print_exc()