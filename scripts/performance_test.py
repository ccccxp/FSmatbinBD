#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
参数加载性能测试 - 模拟大量参数的材质加载
"""

import tkinter as tk
import sys
import os
import time

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.gui.material_panel import MaterialPanel
from src.core.i18n import language_manager, _

def create_test_material_data(param_count=50):
    """创建测试用的材质数据"""
    params = []
    for i in range(param_count):
        param_types = ['Float', 'Float2', 'Float3', 'Float4', 'Bool', 'Int']
        param_type = param_types[i % len(param_types)]
        
        if param_type == 'Bool':
            value = 'true' if i % 2 == 0 else 'false'
        elif param_type in ['Float2', 'Float3', 'Float4']:
            size = int(param_type[-1]) if param_type[-1].isdigit() else 2
            value = [f"{(i + j) * 0.1:.1f}" for j in range(size)]
        else:
            value = f"{i * 0.5:.1f}"
        
        params.append({
            'name': f'参数_{i+1}',
            'type': param_type,
            'value': value,
            'key': f'param_{i}'
        })
    
    return {
        'id': 1,
        'filename': f'测试材质_{param_count}参数.matbin.xml',
        'shader_path': 'test/shader.fx',
        'params': params,
        'samplers': []
    }

def performance_test():
    """性能测试"""
    root = tk.Tk()
    root.title("参数加载性能测试")
    root.geometry("1200x800")
    
    # 创建材质面板
    material_panel = MaterialPanel(root)
    
    # 测试不同数量的参数
    test_cases = [10, 25, 50, 100, 200]
    
    for param_count in test_cases:
        print(f"\n测试 {param_count} 个参数的加载性能...")
        
        # 创建测试数据
        test_material = create_test_material_data(param_count)
        
        # 测量加载时间
        start_time = time.time()
        
        material_panel.load_material(test_material)
        
        # 等待界面更新完成
        root.update()
        
        end_time = time.time()
        load_time = (end_time - start_time) * 1000  # 转换为毫秒
        
        print(f"加载 {param_count} 个参数耗时: {load_time:.2f} ms")
        
        # 清理
        material_panel.clear()
        root.update()
        
        # 等待一秒后进行下一轮测试
        time.sleep(1)
    
    print("\n性能测试完成！")
    print("优化效果：")
    print("- 分批加载：避免界面冻结")
    print("- 进度提示：超过20个参数时显示进度")
    print("- 缓存优化：减少重复的字体和样式创建")
    print("- 延迟布局：避免频繁重排")
    
    # 显示最终测试结果
    final_material = create_test_material_data(100)
    material_panel.load_material(final_material)
    
    root.mainloop()

if __name__ == "__main__":
    performance_test()