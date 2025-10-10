#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据顺序验证脚本 - 验证材质数据的导入导出顺序一致性
"""

import os
import sys
import tempfile

# 添加src目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.database import MaterialDatabase
from src.core.xml_parser import MaterialXMLParser

def test_data_order():
    """测试数据顺序一致性"""
    try:
        # 初始化数据库和解析器
        db = MaterialDatabase()
        parser = MaterialXMLParser()
        
        # 获取所有材质
        materials = db.search_materials()
        print(f"找到 {len(materials)} 个材质")
        
        if not materials:
            print("数据库中没有材质数据，请先导入一些XML文件")
            return
        
        # 测试第一个材质的数据顺序
        first_material = materials[0]
        material_id = first_material['id']
        print(f"\n测试材质: {first_material['filename']}")
        
        # 获取详细信息
        material_detail = db.get_material_detail(material_id)
        if not material_detail:
            print("无法获取材质详情")
            return
        
        print(f"参数数量: {len(material_detail.get('params', []))}")
        print(f"采样器数量: {len(material_detail.get('samplers', []))}")
        
        # 显示前几个参数的顺序
        params = material_detail.get('params', [])
        if params:
            print("\n前5个参数:")
            for i, param in enumerate(params[:5]):
                print(f"  {i+1}. {param['name']} ({param['type']})")
        
        # 显示前几个采样器的顺序
        samplers = material_detail.get('samplers', [])
        if samplers:
            print("\n前5个采样器:")
            for i, sampler in enumerate(samplers[:5]):
                print(f"  {i+1}. {sampler['type']} -> {sampler['path']}")
        
        # 测试导出XML并验证顺序
        print("\n开始测试XML导出顺序...")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # 导出材质到临时文件
            success = parser.export_material_to_xml(material_detail, temp_path)
            if success:
                print(f"导出成功: {temp_path}")
                
                # 重新解析导出的文件
                parsed_data = parser.parse_file(temp_path)
                if parsed_data:
                    # 比较参数顺序
                    original_params = [p['name'] for p in material_detail.get('params', [])]
                    parsed_params = [p['name'] for p in parsed_data.get('params', [])]
                    
                    print(f"\n原始参数数量: {len(original_params)}")
                    print(f"导出后参数数量: {len(parsed_params)}")
                    
                    if original_params == parsed_params:
                        print("✅ 参数顺序保持一致")
                    else:
                        print("❌ 参数顺序发生变化!")
                        print("前10个参数对比:")
                        for i in range(min(10, len(original_params), len(parsed_params))):
                            if i < len(original_params) and i < len(parsed_params):
                                orig = original_params[i]
                                pars = parsed_params[i]
                                status = "✅" if orig == pars else "❌"
                                print(f"  {i+1}: {status} {orig} -> {pars}")
                    
                    # 比较采样器顺序
                    original_samplers = [s['type'] for s in material_detail.get('samplers', [])]
                    parsed_samplers = [s['type'] for s in parsed_data.get('samplers', [])]
                    
                    print(f"\n原始采样器数量: {len(original_samplers)}")
                    print(f"导出后采样器数量: {len(parsed_samplers)}")
                    
                    if original_samplers == parsed_samplers:
                        print("✅ 采样器顺序保持一致")
                    else:
                        print("❌ 采样器顺序发生变化!")
                        print("前10个采样器对比:")
                        for i in range(min(10, len(original_samplers), len(parsed_samplers))):
                            if i < len(original_samplers) and i < len(parsed_samplers):
                                orig = original_samplers[i]
                                pars = parsed_samplers[i]
                                status = "✅" if orig == pars else "❌"
                                print(f"  {i+1}: {status} {orig} -> {pars}")
                else:
                    print("无法解析导出的XML文件")
            else:
                print("导出失败")
                
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    except Exception as e:
        print(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("数据顺序一致性验证")
    print("=" * 50)
    test_data_order()
    print("=" * 50)
    print("验证完成")