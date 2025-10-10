#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
材质加载问题诊断脚本
"""

import os
import sys
import traceback

# 添加src目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.database import MaterialDatabase
from src.core.i18n import _

def diagnose_material_loading():
    """诊断材质加载问题"""
    try:
        print("开始诊断材质加载问题...")
        print("=" * 50)
        
        # 初始化数据库
        db = MaterialDatabase()
        print("✅ 数据库初始化成功")
        
        # 获取材质列表
        materials = db.search_materials()
        print(f"✅ 找到 {len(materials)} 个材质")
        
        if not materials:
            print("❌ 数据库中没有材质数据")
            return
        
        # 测试第一个材质
        first_material = materials[0]
        material_id = first_material['id']
        print(f"测试材质ID: {material_id}")
        print(f"材质文件名: {first_material.get('filename', 'Unknown')}")
        
        # 获取材质详情
        print("\n获取材质详情...")
        material_detail = db.get_material_detail(material_id)
        
        if material_detail is None:
            print("❌ get_material_detail 返回 None")
            
            # 详细检查数据库
            print("\n详细检查数据库...")
            import sqlite3
            with sqlite3.connect(db.db_path) as conn:
                cursor = conn.cursor()
                
                # 检查材质是否存在
                cursor.execute("SELECT COUNT(*) FROM materials WHERE id = ?", (material_id,))
                count = cursor.fetchone()[0]
                print(f"材质记录数: {count}")
                
                if count > 0:
                    # 检查基本信息
                    cursor.execute("SELECT * FROM materials WHERE id = ?", (material_id,))
                    material_row = cursor.fetchone()
                    print(f"材质基本信息: {material_row}")
                    
                    # 检查参数
                    cursor.execute("SELECT COUNT(*) FROM material_params WHERE material_id = ?", (material_id,))
                    param_count = cursor.fetchone()[0]
                    print(f"参数数量: {param_count}")
                    
                    # 检查采样器
                    cursor.execute("SELECT COUNT(*) FROM material_samplers WHERE material_id = ?", (material_id,))
                    sampler_count = cursor.fetchone()[0]
                    print(f"采样器数量: {sampler_count}")
        else:
            print("✅ get_material_detail 成功")
            print(f"材质详情键: {list(material_detail.keys())}")
            print(f"参数数量: {len(material_detail.get('params', []))}")
            print(f"采样器数量: {len(material_detail.get('samplers', []))}")
            
            # 测试翻译
            print("\n测试翻译...")
            print(f"load_material_failed: {_('load_material_failed')}")
            print(f"error: {_('error')}")
            
            # 检查material_panel是否存在
            print("\n检查GUI组件...")
            try:
                from src.gui.material_panel import MaterialPanel
                print("✅ MaterialPanel 类可以导入")
                
                # 尝试创建一个简单的测试
                import tkinter as tk
                test_root = tk.Tk()
                test_root.withdraw()  # 隐藏窗口
                
                test_frame = tk.Frame(test_root)
                material_panel = MaterialPanel(test_frame)
                print("✅ MaterialPanel 可以创建")
                
                # 测试load_material方法
                try:
                    material_panel.load_material(material_detail)
                    print("✅ MaterialPanel.load_material 成功")
                except Exception as e:
                    print(f"❌ MaterialPanel.load_material 失败: {str(e)}")
                    traceback.print_exc()
                
                test_root.destroy()
                
            except Exception as e:
                print(f"❌ GUI组件测试失败: {str(e)}")
                traceback.print_exc()
    
    except Exception as e:
        print(f"❌ 诊断过程中出错: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    diagnose_material_loading()