"""
采样器类型解析器

按设计文档V3第五章实现：
- 从采样器名称解析序号和类型
- 识别通用采样器（不参与自动转换）
- 支持旧版采样器的中文备注和跨世代映射
"""

import re
from typing import Tuple, Optional, List

# 通用采样器列表（旧版格式）
GENERIC_SAMPLERS = [
    'g_DiffuseTexture',
    'g_BumpmapTexture',
    'g_SpecularTexture',
    'g_BloodMaskTexture',
    'g_ShininessTexture',
    'g_LightmapTexture',
    'g_DetailBumpmapTexture',
    'g_DisplacementTexture',
    'g_BlendMaskTexture',
]

# 旧版采样器中文备注映射
LEGACY_SAMPLER_ANNOTATIONS = {
    'DiffuseTexture': '漫反射',
    'BumpmapTexture': '凹凸',
    'SpecularTexture': '高光',
    'BloodMaskTexture': '血迹',
    'ShininessTexture': '反光',
    'LightmapTexture': '光照',
    'DetailBumpmapTexture': '细节',
    'DisplacementTexture': '置换',
    'BlendMaskTexture': '混合',
}

# 跨世代映射表（旧版 → 新版）
# BloodMaskTexture 可映射到多个目标，但只需填充第一个可用的
LEGACY_TO_MODERN_MAPPING = {
    'DiffuseTexture': ['AlbedoMap'],
    'BumpmapTexture': ['NormalMap'],
    'SpecularTexture': ['MetallicMap'],
    'BloodMaskTexture': ['MaskMap', 'Mask1Map', 'Mask3Map'],
    'ShininessTexture': ['MetallicMap'],
    'LightmapTexture': ['EmissiveMap'],
    'DetailBumpmapTexture': ['NormalMap'],
    'DisplacementTexture': ['DisplacementMap'],
}


def parse_sampler_type(type_name: str) -> Tuple[int, str, bool]:
    """
    解析采样器名称，提取序号和类型
    
    Args:
        type_name: 采样器类型名称（如 C_DetailBlend_Rich__snp_Texture2D_7_AlbedoMap）
    
    Returns:
        (序号, 类型, 是否旧版格式)
        
    示例：
        "C_DetailBlend_Rich__snp_Texture2D_7_AlbedoMap" → (7, "AlbedoMap", False)
        "M_AMSN_V_Mb2_Ov_N__snp_Texture2D_0_GSBlendMap_NormalMap_1" → (0, "NormalMap", False)
        "C_c4450__AreaMatchBlend_snp_Texture2D_7_NormalMap_4" → (7, "NormalMap", False)
        "C_Crystal__snp_Texture2D_2__DistortionDepth" → (2, "DistortionDepth", False)
        "g_DiffuseTexture" → (-1, "DiffuseTexture", True)
    """
    if not type_name:
        return (-1, "", False)
    
    # 检查旧版采样器（g_xxx格式）
    for generic in GENERIC_SAMPLERS:
        if type_name.startswith(generic):
            # 提取 g_ 后面的类型名作为 base_type
            base_type = generic[2:]  # 去掉 "g_" 前缀
            return (-1, base_type, True)
    
    # 模式1: 标准格式 Texture2D_数字_类型
    # 例: C_DetailBlend_Rich__snp_Texture2D_7_AlbedoMap
    pattern1 = r'Texture2D_(\d+)_([A-Za-z]+(?:Map)?)$'
    match = re.search(pattern1, type_name)
    if match:
        return (int(match.group(1)), match.group(2), False)
    
    # 模式2: 带后缀数字 Texture2D_数字_类型_数字
    # 例: C_c4450__AreaMatchBlend_snp_Texture2D_7_NormalMap_4
    pattern2 = r'Texture2D_(\d+)_([A-Za-z]+Map)_\d+$'
    match = re.search(pattern2, type_name)
    if match:
        return (int(match.group(1)), match.group(2), False)
    
    # 模式3: 复杂中间内容 Texture2D_数字_xxx_类型_数字
    # 例: M_AMSN_V_Mb2_Ov_N__snp_Texture2D_0_GSBlendMap_NormalMap_1
    pattern3 = r'Texture2D_(\d+)_.*?_([A-Za-z]+Map)(?:_\d+)?$'
    match = re.search(pattern3, type_name)
    if match:
        return (int(match.group(1)), match.group(2), False)
    
    # 模式4: 特殊类型（非Map结尾）
    # 例: C_Crystal__snp_Texture2D_2__DistortionDepth
    pattern4 = r'Texture2D_(\d+)_+([A-Za-z]+)$'
    match = re.search(pattern4, type_name)
    if match:
        return (int(match.group(1)), match.group(2), False)
    
    # 无法识别
    return (-1, "Unknown", False)


def is_generic_sampler(type_name: str) -> bool:
    """检查是否为旧版通用采样器"""
    if not type_name:
        return False
    for generic in GENERIC_SAMPLERS:
        if type_name.startswith(generic):
            return True
    return False


def get_legacy_display_name(type_name: str) -> str:
    """
    获取旧版采样器带中文备注的显示名称
    
    Args:
        type_name: 采样器类型名称（如 g_DiffuseTexture）
    
    Returns:
        带备注的显示名称，如 "g_DiffuseTexture(漫反射)"
        如果不是旧版采样器，返回原名称
    """
    _, base_type, is_legacy = parse_sampler_type(type_name)
    if is_legacy and base_type:
        annotation = LEGACY_SAMPLER_ANNOTATIONS.get(base_type, '')
        if annotation:
            return f"g_{base_type}({annotation})"
        return f"g_{base_type}"
    return type_name


def get_sampler_display_name(type_name: str) -> str:
    """
    获取采样器显示名称
    
    Returns:
        格式化的显示名称：
        - 新版: 完整的 type_name（如 C[c2030]_AM__snp_Texture2D_7_AlbedoMap）
        - 旧版: 完整的 type_name + 中文备注（如 g_DiffuseTexture(漫反射)）
    """
    _, base_type, is_legacy = parse_sampler_type(type_name)
    if is_legacy:
        return get_legacy_display_name(type_name)
    # 新版采样器：返回完整的 type_name
    return type_name


def get_modern_mapping(legacy_base_type: str) -> List[str]:
    """
    获取旧版采样器对应的新版类型列表
    
    Args:
        legacy_base_type: 旧版采样器基础类型（如 DiffuseTexture）
    
    Returns:
        对应的新版类型列表（如 ['AlbedoMap']）
    """
    return LEGACY_TO_MODERN_MAPPING.get(legacy_base_type, [])


# 测试用例（按设计文档 5.2）
def _test_parse_sampler_type():
    """运行测试用例验证解析器"""
    test_cases = [
        ("C_DetailBlend_Rich__snp_Texture2D_7_AlbedoMap", (7, "AlbedoMap", False)),
        ("C_DetailBlend_Rich__snp_Texture2D_0_NormalMap", (0, "NormalMap", False)),
        ("C_DetailBlend_Rich__snp_Texture2D_11_MetallicMap", (11, "MetallicMap", False)),
        ("C_Face_S2__SSS_snp_Texture2D_2_Mask3Map", (2, "Mask3Map", False)),
        ("C_Fur__FurBlur_snp_Texture2D_9_VectorMap", (9, "VectorMap", False)),
        ("M_AMSN_V_Mb2_Ov_N__snp_Texture2D_0_GSBlendMap_NormalMap_1", (0, "NormalMap", False)),
        ("C_c4450__AreaMatchBlend_snp_Texture2D_7_NormalMap_4", (7, "NormalMap", False)),
        ("C_Crystal__snp_Texture2D_2__DistortionDepth", (2, "DistortionDepth", False)),
        # 旧版采样器测试（现在返回 base_type）
        ("g_DiffuseTexture", (-1, "DiffuseTexture", True)),
        ("g_BumpmapTexture", (-1, "BumpmapTexture", True)),
        ("g_SpecularTexture", (-1, "SpecularTexture", True)),
        ("g_DisplacementTexture", (-1, "DisplacementTexture", True)),
    ]
    
    passed = 0
    failed = 0
    for type_name, expected in test_cases:
        result = parse_sampler_type(type_name)
        if result == expected:
            print(f"✓ {type_name} → {result}")
            passed += 1
        else:
            print(f"✗ {type_name}")
            print(f"  Expected: {expected}")
            print(f"  Got: {result}")
            failed += 1
    
    # 测试显示名称
    print("\n=== 显示名称测试 ===")
    display_tests = [
        ("g_DiffuseTexture", "DiffuseTexture(漫反射)"),
        ("g_BumpmapTexture", "BumpmapTexture(凹凸)"),
        ("g_BloodMaskTexture", "BloodMaskTexture(血迹)"),
    ]
    for type_name, expected_display in display_tests:
        result = get_legacy_display_name(type_name)
        if result == expected_display:
            print(f"✓ {type_name} → {result}")
            passed += 1
        else:
            print(f"✗ {type_name}")
            print(f"  Expected: {expected_display}")
            print(f"  Got: {result}")
            failed += 1
    
    print(f"\n总计: {passed} 通过, {failed} 失败")
    return failed == 0


if __name__ == '__main__':
    _test_parse_sampler_type()

