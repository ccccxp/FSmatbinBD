"""
材质替换功能 - 核心数据模型

按设计文档V3第十章 10.1 定义的数据结构
用于撤销/重做与窗口状态保持
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


@dataclass
class Vec2:
    """二维向量（Scale等）"""
    x: float = 1.0
    y: float = 1.0
    
    def to_dict(self) -> Dict[str, float]:
        return {'X': self.x, 'Y': self.y}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Vec2':
        return cls(
            x=data.get('X', 1.0),
            y=data.get('Y', 1.0)
        )


@dataclass
class SamplerData:
    """
    采样器数据（对应 JSON 的 Textures[*]）
    
    Attributes:
        type_name: 采样器类型名称（如 C_DetailBlend_Rich__snp_Texture2D_7_AlbedoMap）
        index: 解析得到的序号（如 7）
        sampler_type: 解析得到的基础类型（如 AlbedoMap）
        sorted_pos: 在列表中的排序位置
        path: 贴图路径
        scale: XY缩放
        unk10, unk11, unk14, unk18, unk1c: 额外参数
    """
    type_name: str
    index: int = -1
    sampler_type: str = ""
    sorted_pos: int = 0
    path: str = ""
    scale: Vec2 = field(default_factory=Vec2)
    unk10: int = 0
    unk11: bool = False
    unk14: int = 0
    unk18: int = 0
    unk1c: int = 0
    
    @property
    def has_path(self) -> bool:
        """是否为标记采样器（Path非空）"""
        return bool(self.path and self.path.strip())
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为JSON字典（保持字段顺序）"""
        return {
            'Type': self.type_name,
            'Path': self.path,
            'Scale': self.scale.to_dict(),
            'Unk10': self.unk10,
            'Unk11': self.unk11,
            'Unk14': self.unk14,
            'Unk18': self.unk18,
            'Unk1C': self.unk1c,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], sorted_pos: int = 0) -> 'SamplerData':
        """从JSON字典创建SamplerData"""
        from .sampler_type_parser import parse_sampler_type
        
        type_name = data.get('Type', '')
        index, sampler_type, _ = parse_sampler_type(type_name)
        
        scale_data = data.get('Scale', {})
        scale = Vec2.from_dict(scale_data) if isinstance(scale_data, dict) else Vec2()
        
        return cls(
            type_name=type_name,
            index=index,
            sampler_type=sampler_type,
            sorted_pos=sorted_pos,
            path=data.get('Path', ''),
            scale=scale,
            unk10=data.get('Unk10', 0),
            unk11=data.get('Unk11', False),
            unk14=data.get('Unk14', 0),
            unk18=data.get('Unk18', 0),
            unk1c=data.get('Unk1C', 0),
        )
    
    def copy(self) -> 'SamplerData':
        """创建副本"""
        return SamplerData(
            type_name=self.type_name,
            index=self.index,
            sampler_type=self.sampler_type,
            sorted_pos=self.sorted_pos,
            path=self.path,
            scale=Vec2(self.scale.x, self.scale.y),
            unk10=self.unk10,
            unk11=self.unk11,
            unk14=self.unk14,
            unk18=self.unk18,
            unk1c=self.unk1c,
        )


@dataclass
class MaterialEntry:
    """
    材质条目（对应 JSON 的顶层数组元素）
    
    Attributes:
        name: 材质名称
        mtd: MTD路径
        textures: 采样器列表
        gx_index: GX索引
        index: 索引
        is_modified: 是否已修改（编辑器附加字段，不导出）
        last_match_summary: 上次匹配摘要（编辑器附加字段，不导出）
    """
    name: str
    mtd: str
    textures: List[SamplerData] = field(default_factory=list)
    gx_index: int = 0
    index: int = 0
    
    # 编辑器附加字段（不导出到 JSON）
    is_modified: bool = False
    last_match_summary: Optional[Dict[str, int]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为JSON字典（保持字段顺序：Name, MTD, Textures, GXIndex, Index）"""
        return {
            'Name': self.name,
            'MTD': self.mtd,
            'Textures': [t.to_dict() for t in self.textures],
            'GXIndex': self.gx_index,
            'Index': self.index,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MaterialEntry':
        """从JSON字典创建MaterialEntry"""
        textures_data = data.get('Textures', [])
        textures = [SamplerData.from_dict(t, i) for i, t in enumerate(textures_data)]
        
        return cls(
            name=data.get('Name', ''),
            mtd=data.get('MTD', ''),
            textures=textures,
            gx_index=data.get('GXIndex', 0),
            index=data.get('Index', 0),
        )
    
    def copy(self) -> 'MaterialEntry':
        """创建深拷贝"""
        return MaterialEntry(
            name=self.name,
            mtd=self.mtd,
            textures=[t.copy() for t in self.textures],
            gx_index=self.gx_index,
            index=self.index,
            is_modified=self.is_modified,
            last_match_summary=dict(self.last_match_summary) if self.last_match_summary else None,
        )


@dataclass
class ConversionOptions:
    """
    转换选项配置（按设计文档 2.5）
    """
    # === 路径处理选项 ===
    simplify_texture_path: bool = False    # 简化贴图路径
    simplify_material_path: bool = False   # 简化材质路径
    
    # === 参数迁移选项 ===
    migrate_parameters: bool = True        # 迁移源材质参数
    
    # === 匹配策略选项 ===
    prefer_perfect_match: bool = True      # 优先完美匹配
    prefer_marked_coverage: bool = True    # 优先覆盖标记采样器
    allow_order_adjustment: bool = True    # 允许顺序调整
    max_order_adjustments: int = 3         # 最大顺序调整数量
    strict_order_validation: bool = True   # 顺序校验（仅提示，不阻止导出）
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'simplify_texture_path': self.simplify_texture_path,
            'simplify_material_path': self.simplify_material_path,
            'migrate_parameters': self.migrate_parameters,
            'prefer_perfect_match': self.prefer_perfect_match,
            'prefer_marked_coverage': self.prefer_marked_coverage,
            'allow_order_adjustment': self.allow_order_adjustment,
            'max_order_adjustments': self.max_order_adjustments,
            'strict_order_validation': self.strict_order_validation,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversionOptions':
        return cls(
            simplify_texture_path=data.get('simplify_texture_path', False),
            simplify_material_path=data.get('simplify_material_path', False),
            migrate_parameters=data.get('migrate_parameters', True),
            prefer_perfect_match=data.get('prefer_perfect_match', True),
            prefer_marked_coverage=data.get('prefer_marked_coverage', True),
            allow_order_adjustment=data.get('allow_order_adjustment', True),
            max_order_adjustments=data.get('max_order_adjustments', 3),
            strict_order_validation=data.get('strict_order_validation', True),
        )


@dataclass
class EditorState:
    """
    编辑器状态（用于窗口状态保持）
    
    按设计文档 13.1 定义，关闭窗口后再次打开时恢复
    """
    file_path: Optional[str] = None
    materials: List[MaterialEntry] = field(default_factory=list)
    conversion_options: ConversionOptions = field(default_factory=ConversionOptions)
    selected_row: int = -1
    scroll_position: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'file_path': self.file_path,
            'materials': [m.to_dict() for m in self.materials],
            'conversion_options': self.conversion_options.to_dict(),
            'selected_row': self.selected_row,
            'scroll_position': self.scroll_position,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EditorState':
        materials_data = data.get('materials', [])
        materials = [MaterialEntry.from_dict(m) for m in materials_data]
        
        options_data = data.get('conversion_options', {})
        options = ConversionOptions.from_dict(options_data) if options_data else ConversionOptions()
        
        return cls(
            file_path=data.get('file_path'),
            materials=materials,
            conversion_options=options,
            selected_row=data.get('selected_row', -1),
            scroll_position=data.get('scroll_position', 0),
        )


class MatchStatus(Enum):
    """匹配状态枚举（按设计文档 2.4）"""
    PERFECT_MATCH = 'PERFECT_MATCH'      # 🟢 序号+类型完美匹配（Step1成功）
    ADJACENT_MATCH = 'ADJACENT_MATCH'    # 🟡 类型匹配但序号不同（Step2/3成功）
    UNMATCHED = 'UNMATCHED'              # 🔴 源采样器无法匹配
    UNCOVERED = 'UNCOVERED'              # 🔵 目标原有路径未被覆盖
    EMPTY = 'EMPTY'                      # ⚪ 目标空采样器未被填充


# 状态图标（不需要翻译）
STATUS_ICONS = {
    MatchStatus.PERFECT_MATCH: '🟢',
    MatchStatus.ADJACENT_MATCH: '🟡',
    MatchStatus.UNMATCHED: '🔴',
    MatchStatus.UNCOVERED: '🔵',
    MatchStatus.EMPTY: '⚪',
}


@dataclass
class MatchResult:
    """单个采样器的匹配结果"""
    source_pos: int                     # 源采样器位置
    target_pos: Optional[int]           # 目标采样器位置（None表示未匹配）
    status: MatchStatus                 # 匹配状态
    reason: str = ""                    # 原因说明（用于UI显示，需要i18n）
    order_adjusted: bool = False        # 是否发生了顺序调整
    adjustment_detail: str = ""         # 调整详情


@dataclass
class ReplaceResult:
    """材质替换结果"""
    source_material: MaterialEntry
    target_material: MaterialEntry
    results: List[MatchResult]          # 按源采样器顺序排列
    warnings: List[str] = field(default_factory=list)
    order_adjustments_count: int = 0
    global_repair_triggered: bool = False
