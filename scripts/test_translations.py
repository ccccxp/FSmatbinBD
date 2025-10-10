#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试翻译修复"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.i18n import language_manager, _

def test_translations():
    """测试关键翻译项"""
    print("=== 测试翻译修复 ===")
    
    # 测试不同语言的关键翻译
    languages = ['zh_CN', 'en_US', 'ja_JP', 'ko_KR']
    
    for lang in languages:
        print(f"\n{lang} 语言:")
        language_manager.set_language(lang)
        
        # 软件名称和版本
        print(f"  软件标题: {_('app_title')} {_('version')}")
        
        # 高级搜索按钮
        print(f"  高级搜索: {_('advanced_search_button')}")
        
        # 统计信息
        stats_template = _('library_material_stats')
        print(f"  统计模板: {stats_template}")
        try:
            stats_text = stats_template.format(libraries=2, materials=41376)
            print(f"  统计示例: {stats_text}")
        except Exception as e:
            print(f"  统计格式错误: {e}")
        
        # 状态信息
        print(f"  状态就绪: {_('status_ready')}")
        
        # 菜单项
        print(f"  文件菜单: {_('menu_file')}")
        print(f"  编辑菜单: {_('menu_edit')}")
        print(f"  语言菜单: {_('menu_language')}")
        print(f"  帮助菜单: {_('menu_help')}")
        
        # 按钮
        print(f"  搜索按钮: {_('search_button')}")
        print(f"  清空按钮: {_('clear_button')}")
        print(f"  添加库按钮: {_('add_library_button')}")

if __name__ == "__main__":
    try:
        test_translations()
    except Exception as e:
        print(f"测试过程中出错: {e}")
        import traceback
        traceback.print_exc()