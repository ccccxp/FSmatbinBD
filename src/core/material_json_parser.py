"""
材质JSON解析器

按设计文档V3第七章实现：
- 导入解析（路径归一化）
- 导出规则（字段顺序、转义规则）
- 错误处理（7.3）
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from .material_replace_models import MaterialEntry, SamplerData, Vec2

logger = logging.getLogger(__name__)


class MaterialJsonParser:
    """材质JSON解析器"""
    
    @staticmethod
    def normalize_path(path: str) -> str:
        r"""
        路径归一化：统一为单个反斜杠
        
        按设计文档 7.2：导入时做归一化，统一为单个反斜杠 `\`
        """
        if not path:
            return ""
        # 处理双反斜杠 -> 单反斜杠
        normalized = path.replace('\\\\', '\\')
        # 处理正斜杠 -> 反斜杠（如果存在）
        normalized = normalized.replace('/', '\\')
        return normalized
    
    @classmethod
    def parse_file(cls, file_path: str) -> Tuple[List[MaterialEntry], Optional[str]]:
        """
        解析JSON文件
        
        Args:
            file_path: JSON文件路径
            
        Returns:
            (材质列表, 错误信息)
            成功时错误信息为 None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            return [], f"文件不存在: {file_path}"
        except json.JSONDecodeError as e:
            return [], f"JSON语法错误: {e}"
        except Exception as e:
            return [], f"读取文件失败: {e}"
        
        return cls.parse_data(data)
    
    @classmethod
    def parse_data(cls, data: Any) -> Tuple[List[MaterialEntry], Optional[str]]:
        """
        解析JSON数据
        
        Args:
            data: JSON解析后的数据
            
        Returns:
            (材质列表, 错误信息)
        """
        # 验证顶层结构
        if not isinstance(data, list):
            return [], "JSON顶层必须是数组 []"
        
        materials = []
        for idx, item in enumerate(data):
            result, error = cls._parse_material_entry(item, idx)
            if error:
                return [], error
            materials.append(result)
        
        return materials, None
    
    @classmethod
    def _parse_material_entry(cls, data: Dict[str, Any], idx: int) -> Tuple[Optional[MaterialEntry], Optional[str]]:
        """
        解析单个材质条目
        
        按设计文档 7.3：缺少关键字段时拦截并提示
        """
        if not isinstance(data, dict):
            return None, f"材质条目 #{idx} 必须是对象"
        
        # 检查必要字段
        required_fields = ['Name', 'MTD', 'Textures', 'GXIndex', 'Index']
        for field in required_fields:
            if field not in data:
                return None, f"材质条目 #{idx} 缺少必要字段: {field}"
        
        # 验证 Textures 是数组
        textures_data = data.get('Textures')
        if not isinstance(textures_data, list):
            return None, f"材质条目 #{idx} 的 Textures 必须是数组"
        
        # 解析 Textures
        textures = []
        for t_idx, t_data in enumerate(textures_data):
            sampler, error = cls._parse_sampler(t_data, idx, t_idx)
            if error:
                return None, error
            textures.append(sampler)
        
        # 创建 MaterialEntry
        entry = MaterialEntry(
            name=data.get('Name', ''),
            mtd=cls.normalize_path(data.get('MTD', '')),
            textures=textures,
            gx_index=data.get('GXIndex', 0),
            index=data.get('Index', 0),
        )
        
        return entry, None
    
    @classmethod
    def _parse_sampler(cls, data: Dict[str, Any], mat_idx: int, sampler_idx: int) -> Tuple[Optional[SamplerData], Optional[str]]:
        """
        解析单个采样器
        
        按设计文档 7.3：Textures 内部缺少 Type/Path/Scale 等字段时拦截
        """
        if not isinstance(data, dict):
            return None, f"材质 #{mat_idx} 的采样器 #{sampler_idx} 必须是对象"
        
        # 检查必要字段
        required_fields = ['Type', 'Path', 'Scale']
        for field in required_fields:
            if field not in data:
                return None, f"材质 #{mat_idx} 的采样器 #{sampler_idx} 缺少必要字段: {field}"
        
        # 验证 Scale 结构
        scale_data = data.get('Scale')
        if not isinstance(scale_data, dict):
            return None, f"材质 #{mat_idx} 的采样器 #{sampler_idx} 的 Scale 必须是对象"
        
        # 解析并归一化路径
        path = cls.normalize_path(data.get('Path', ''))
        
        # 创建 SamplerData
        sampler = SamplerData.from_dict({
            **data,
            'Path': path,  # 使用归一化后的路径
        }, sorted_pos=sampler_idx)
        
        return sampler, None
    
    @classmethod
    def export_to_file(cls, materials: List[MaterialEntry], file_path: str) -> Optional[str]:
        """
        导出材质列表到JSON文件
        
        按设计文档 7.2：
        - 字段顺序：Name, MTD, Textures, GXIndex, Index
        - Textures字段顺序：Type, Path, Scale(X,Y), Unk10, Unk11, Unk14, Unk18, Unk1C
        - 路径按JSON规则转义（文本表现为 \\，语义为 \）
        - 使用制表符缩进匹配原始格式
        - 整数值保持整数形式（1 而非 1.0）
        
        Returns:
            错误信息，成功时返回 None
        """
        try:
            data = cls.export_to_data(materials)
            
            # 使用自定义格式化保持与原始格式一致
            json_str = cls._format_json_with_tabs(data)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
            
            return None
        except PermissionError:
            return f"文件不可写（可能被占用）: {file_path}"
        except Exception as e:
            return f"导出失败: {e}"
    
    @classmethod
    def _format_json_with_tabs(cls, data: Any, indent_level: int = 0) -> str:
        """
        使用制表符缩进格式化JSON，匹配原始文件格式
        
        特点：
        - 键值对格式：`"Key":\tvalue`（冒号后跟制表符）
        - 使用制表符缩进
        - 整数值保持整数形式
        """
        indent = '\t' * indent_level
        next_indent = '\t' * (indent_level + 1)
        
        if isinstance(data, dict):
            if not data:
                return '{}'
            
            items = []
            for key, value in data.items():
                formatted_value = cls._format_json_with_tabs(value, indent_level + 1)
                items.append(f'{next_indent}"{key}": {formatted_value}')
            
            return '{\n' + ',\n'.join(items) + '\n' + indent + '}'
        
        elif isinstance(data, list):
            if not data:
                return '[]'
            
            items = []
            for item in data:
                formatted_item = cls._format_json_with_tabs(item, indent_level + 1)
                items.append(f'{next_indent}{formatted_item}')
            
            return '[\n' + ',\n'.join(items) + '\n' + indent + ']'
        
        elif isinstance(data, str):
            # 使用标准JSON字符串转义
            return json.dumps(data, ensure_ascii=False)
        
        elif isinstance(data, bool):
            return 'true' if data else 'false'
        
        elif isinstance(data, float):
            # 如果是整数值（如 1.0），转换为整数格式
            if data == int(data):
                return str(int(data))
            return str(data)
        
        elif isinstance(data, int):
            return str(data)
        
        elif data is None:
            return 'null'
        
        else:
            return json.dumps(data, ensure_ascii=False)
    
    @classmethod
    def export_to_data(cls, materials: List[MaterialEntry]) -> List[Dict[str, Any]]:
        """
        导出材质列表为JSON数据
        
        Returns:
            JSON可序列化的数据
        """
        return [cls._export_material_entry(m) for m in materials]
    
    @classmethod
    def _export_material_entry(cls, material: MaterialEntry) -> Dict[str, Any]:
        """
        导出单个材质条目
        
        按设计文档 7.2 字段顺序
        """
        # 使用有序字典确保字段顺序（Python 3.7+ dict保持插入顺序）
        return {
            'Name': material.name,
            'MTD': material.mtd,
            'Textures': [cls._export_sampler(s) for s in material.textures],
            'GXIndex': material.gx_index,
            'Index': material.index,
        }
    
    @classmethod
    def _export_sampler(cls, sampler: SamplerData) -> Dict[str, Any]:
        """
        导出单个采样器
        
        按设计文档 7.2 Textures字段顺序
        整数值保持整数形式
        """
        # 转换 scale 值：如果是整数则使用整数
        scale_x = int(sampler.scale.x) if sampler.scale.x == int(sampler.scale.x) else sampler.scale.x
        scale_y = int(sampler.scale.y) if sampler.scale.y == int(sampler.scale.y) else sampler.scale.y
        
        return {
            'Type': sampler.type_name,
            'Path': sampler.path,
            'Scale': {
                'X': scale_x,
                'Y': scale_y,
            },
            'Unk10': sampler.unk10,
            'Unk11': sampler.unk11,
            'Unk14': sampler.unk14,
            'Unk18': sampler.unk18,
            'Unk1C': sampler.unk1c,
        }
    
    @classmethod
    def validate_structure(cls, data: Any) -> Tuple[bool, Optional[str]]:
        """
        验证JSON结构是否符合规范
        
        Returns:
            (是否有效, 错误信息)
        """
        if not isinstance(data, list):
            return False, "JSON顶层必须是数组 []"
        
        for idx, item in enumerate(data):
            if not isinstance(item, dict):
                return False, f"材质条目 #{idx} 必须是对象"
            
            # 检查必要字段
            required_fields = ['Name', 'MTD', 'Textures', 'GXIndex', 'Index']
            for field in required_fields:
                if field not in item:
                    return False, f"材质条目 #{idx} 缺少必要字段: {field}"
            
            # 验证 Textures
            textures = item.get('Textures')
            if not isinstance(textures, list):
                return False, f"材质条目 #{idx} 的 Textures 必须是数组"
            
            for t_idx, texture in enumerate(textures):
                if not isinstance(texture, dict):
                    return False, f"材质 #{idx} 的采样器 #{t_idx} 必须是对象"
                
                for field in ['Type', 'Path', 'Scale']:
                    if field not in texture:
                        return False, f"材质 #{idx} 的采样器 #{t_idx} 缺少必要字段: {field}"
        
        return True, None
