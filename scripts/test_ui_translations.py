#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试界面翻译完整性"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.i18n import language_manager, _

def test_ui_translations():
    """测试所有界面翻译项"""
    print("=== 测试界面翻译完整性 ===")
    
    # 需要测试的翻译键
    ui_keys = [
        'app_title', 'version', 'advanced_search_button', 'library_material_stats',
        'type_label', 'key_label', 'name_label', 'value_label', 'value_label_short',
        'array_values_label', 'delete_button', 'material_name', 'shader_path',
        'material_file_path', 'compression_type', 'key_value', 'basic_info',
        'editable_params', 'material_info_panel'
    ]
    
    languages = ['zh_CN', 'en_US', 'ja_JP', 'ko_KR']
    
    for lang in languages:
        print(f"\n{lang} 语言翻译:")
        language_manager.set_language(lang)
        
        missing_keys = []
        for key in ui_keys:
            try:
                translation = _(key)
                if translation == key:  # 如果翻译和键相同，可能是缺失翻译
                    missing_keys.append(key)
                print(f"  {key}: {translation}")
            except Exception as e:
                print(f"  {key}: ERROR - {e}")
                missing_keys.append(key)
        
        if missing_keys:
            print(f"  缺失的翻译: {missing_keys}")
        else:
            print(f"  ✓ 所有翻译完整")
        
        # 测试带参数的翻译
        try:
            stats_text = _('library_material_stats').format(libraries=2, materials=41376)
            print(f"  统计示例: {stats_text}")
        except Exception as e:
            print(f"  统计格式错误: {e}")
        
        try:
            array_text = _('array_values_label').format(count=3)
            print(f"  数组示例: {array_text}")
        except Exception as e:
            print(f"  数组格式错误: {e}")

if __name__ == "__main__":
    try:
        test_ui_translations()
    except Exception as e:
        print(f"测试过程中出错: {e}")
        import traceback
        traceback.print_exc()