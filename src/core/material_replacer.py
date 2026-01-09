"""
材质替换核心模块

基于设计文档V3实现：
- Phase 1: Step1/Step2/Step3 三步匹配
- Phase 2: 最小临近改动（局部 swap/shift）
- Phase 3: 全局顺序检查与二次修复

约束：源顺序至上，导出不阻止
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import re
import logging

logger = logging.getLogger(__name__)

# 使用 sampler_type_parser 中的统一解析函数（需要在 Sampler 类之前导入）
from .sampler_type_parser import parse_sampler_type


class MatchStatus(Enum):
    """匹配状态枚举"""
    PERFECT_MATCH = 'PERFECT_MATCH'      # 🟢 序号+类型完美匹配
    ADJACENT_MATCH = 'ADJACENT_MATCH'    # 🟡 类型匹配但序号不同
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
class ConversionOptions:
    """转换选项配置"""
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


@dataclass
class Sampler:
    """采样器数据结构"""
    type_name: str          # 采样器类型名（如 C_DetailBlend_Rich__snp_Texture2D_7_AlbedoMap）
    path: str = ""          # 贴图路径
    scale_x: float = 1.0
    scale_y: float = 1.0
    unk10: int = 0
    unk11: bool = False
    unk14: int = 0
    unk18: int = 0
    unk1c: int = 0
    
    # 解析后的信息
    index: int = -1         # 序号（如 7）
    base_type: str = ""     # 基础类型（如 AlbedoMap）
    is_legacy: bool = False # 是否为旧版格式（g_DiffuseTexture等）
    sorted_pos: int = 0     # 排序位置
    
    @property
    def has_path(self) -> bool:
        """是否为标记采样器（Path非空）"""
        return bool(self.path and self.path.strip())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], sorted_pos: int = 0) -> 'Sampler':
        """从JSON字典创建Sampler"""
        sampler = cls(
            type_name=data.get('Type', ''),
            path=data.get('Path', ''),
            scale_x=data.get('Scale', {}).get('X', 1.0),
            scale_y=data.get('Scale', {}).get('Y', 1.0),
            unk10=data.get('Unk10', 0),
            unk11=data.get('Unk11', False),
            unk14=data.get('Unk14', 0),
            unk18=data.get('Unk18', 0),
            unk1c=data.get('Unk1C', 0),
            sorted_pos=sorted_pos,
        )
        sampler.index, sampler.base_type, sampler.is_legacy = parse_sampler_type(sampler.type_name)
        return sampler
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为JSON字典"""
        return {
            'Type': self.type_name,
            'Path': self.path,
            'Scale': {'X': self.scale_x, 'Y': self.scale_y},
            'Unk10': self.unk10,
            'Unk11': self.unk11,
            'Unk14': self.unk14,
            'Unk18': self.unk18,
            'Unk1C': self.unk1c,
        }


@dataclass
class Material:
    """材质数据结构"""
    name: str
    mtd_path: str
    samplers: List[Sampler]
    gx_index: int = 0
    index: int = 0
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Material':
        """从JSON字典创建Material"""
        textures = data.get('Textures', [])
        samplers = [Sampler.from_dict(t, i) for i, t in enumerate(textures)]
        return cls(
            name=data.get('Name', ''),
            mtd_path=data.get('MTD', ''),
            samplers=samplers,
            gx_index=data.get('GXIndex', 0),
            index=data.get('Index', 0),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为JSON字典"""
        return {
            'Name': self.name,
            'MTD': self.mtd_path,
            'Textures': [s.to_dict() for s in self.samplers],
            'GXIndex': self.gx_index,
            'Index': self.index,
        }


@dataclass
class MatchResult:
    """单个采样器的匹配结果"""
    source_pos: int                     # 源采样器位置
    target_pos: Optional[int]           # 目标采样器位置（None表示未匹配）
    status: MatchStatus                 # 匹配状态
    reason: str = ""                    # 原因说明
    order_adjusted: bool = False        # 是否发生了顺序调整
    adjustment_detail: str = ""         # 调整详情


@dataclass
class ReplaceResult:
    """材质替换结果"""
    source_material: Material
    target_material: Material
    results: List[MatchResult]          # 按源采样器顺序排列
    warnings: List[str] = field(default_factory=list)
    order_adjustments_count: int = 0
    global_repair_triggered: bool = False



class MaterialReplacer:
    """材质替换器"""
    
    def __init__(self, options: Optional[ConversionOptions] = None):
        self.options = options or ConversionOptions()
        self._adjustment_count = 0
    
    def replace(self, source: Material, target: Material) -> ReplaceResult:
        """
        执行材质替换 - Sort-Match-Restore 框架
        
        匹配策略：
        1. 源材质：只有有路径的采样器参与匹配，按 Index 排序（决定加载顺序）
        2. 目标材质：所有采样器按 Index 排序，作为匹配候选
        3. 每次从头搜索，无 cursor 限制
        4. 冲突时进行对比分析
        5. Phase 2/3 调用链启用
        
        旧版材质检测：
        - 如果源材质包含旧版采样器（g_xxx格式），使用独立的匹配逻辑
        - 旧版匹配独立于核心匹配机制，不影响现有逻辑
        """
        self._adjustment_count = 0
        self._log_lines: List[str] = []
        warnings: List[str] = []
        
        # === 旧版材质检测 ===
        # 检测源材质中是否有旧版采样器（is_legacy=True 且有路径）
        source_legacy_samplers = [s for s in source.samplers if s.is_legacy and s.has_path]
        
        if source_legacy_samplers:
            # 检测目标材质类型
            target_has_modern = any(not s.is_legacy and s.index >= 0 for s in target.samplers)
            target_has_legacy = any(s.is_legacy for s in target.samplers)
            
            self._log_lines.append(f"[Legacy Detection] Source has {len(source_legacy_samplers)} legacy samplers")
            self._log_lines.append(f"[Legacy Detection] Target has modern: {target_has_modern}, legacy: {target_has_legacy}")
            
            # 使用独立的旧版匹配逻辑
            return self._replace_legacy(source, target, source_legacy_samplers, target_has_modern)
        
        # === Phase 0: Sort（预处理排序）===
        
        # 源材质：筛选有路径的采样器，按 Index 排序
        source_with_path = [(i, s) for i, s in enumerate(source.samplers) if s.has_path]
        sorted_source = sorted(source_with_path, key=lambda x: (x[1].index, x[0]))
        
        # 目标材质：所有采样器按 Index 排序
        indexed_target = list(enumerate(target.samplers))
        sorted_target = sorted(indexed_target, key=lambda x: (x[1].index, x[0]))
        
        self._log_lines.append(f"[Phase0] Source with path: {len(sorted_source)}, Target: {len(sorted_target)}")
        self._log_lines.append(f"[Phase0] Source indices: {[s[1].index for s in sorted_source]}")
        self._log_lines.append(f"[Phase0] Target indices: {[t[1].index for t in sorted_target]}")
        
        # 初始化状态
        occupied = [False] * len(sorted_target)
        match_of_target: Dict[int, int] = {}  # sorted_target_idx -> sorted_source_idx
        
        # 结果列表
        sorted_results: List[MatchResult] = []
        
        # === Phase 1: Match（使用 _match_single_sampler）===
        for sorted_src_idx, (orig_src_pos, src_sampler) in enumerate(sorted_source):
            # 使用 _match_single_sampler（从头搜索，无 cursor）
            result = self._match_single_sampler(
                sorted_src_idx, orig_src_pos, src_sampler,
                sorted_target, occupied, match_of_target
            )
            
            sorted_target_idx = result.target_pos
            
            # 处理匹配结果
            if sorted_target_idx is not None:
                # 转换为原始目标位置
                result.target_pos = sorted_target[sorted_target_idx][0]
                occupied[sorted_target_idx] = True
                match_of_target[sorted_target_idx] = sorted_src_idx
            
            sorted_results.append(result)
            
            self._log_lines.append(
                f"[Match] Src[{orig_src_pos}] idx={src_sampler.index} ({src_sampler.base_type}) -> "
                f"Target orig={result.target_pos} [{result.status.name}]"
            )
        
        # === Restore: 还原到原始顺序 ===
        results: List[MatchResult] = []
        sorted_result_map = {r.source_pos: r for r in sorted_results}
        
        for src_pos, src_sampler in enumerate(source.samplers):
            if src_pos in sorted_result_map:
                results.append(sorted_result_map[src_pos])
            else:
                # 源采样器无路径，标记为 EMPTY
                results.append(MatchResult(
                    source_pos=src_pos,
                    target_pos=None,
                    status=MatchStatus.EMPTY,
                    reason="源采样器无路径，跳过匹配",
                ))
        
        # === Phase 3: 全局顺序检查 ===
        if self.options.strict_order_validation:
            repair_triggered = self._global_order_check_and_repair(
                source.samplers, target.samplers, results,
                [False] * len(target.samplers), {}
            )
            if repair_triggered:
                warnings.append("触发全局顺序修复")
        
        # 标记未覆盖的目标采样器
        covered_targets = {r.target_pos for r in results if r.target_pos is not None}
        for t_idx, t_sampler in enumerate(target.samplers):
            if t_idx not in covered_targets and t_sampler.has_path:
                warnings.append(f"目标采样器 #{t_idx} ({t_sampler.base_type}) 未被覆盖")
        
        return ReplaceResult(
            source_material=source,
            target_material=target,
            results=results,
            warnings=warnings,
            order_adjustments_count=self._adjustment_count,
            global_repair_triggered=False,
        )
    
    def _replace_legacy(
        self,
        source: Material,
        target: Material,
        source_legacy_samplers: List[Sampler],
        target_has_modern: bool,
    ) -> ReplaceResult:
        """
        独立的旧版采样器匹配逻辑
        
        匹配策略（独立于核心机制）：
        1. 旧版→旧版：基于采样器名称（base_type）完全匹配
        2. 旧版→新版：使用跨世代映射表自动转换
        
        源材质按原始顺序遍历（无需排序，旧版没有 Index）
        目标材质按 Index 排序后遍历
        """
        from .sampler_type_parser import get_modern_mapping
        
        warnings: List[str] = []
        results: List[MatchResult] = []
        
        # 目标材质按 Index 排序（新版目标需要）
        indexed_target = list(enumerate(target.samplers))
        sorted_target = sorted(indexed_target, key=lambda x: (x[1].index, x[0]))
        
        # 已占用的目标位置
        occupied_targets: set = set()
        
        self._log_lines.append(f"[Legacy Replace] Processing {len(source_legacy_samplers)} legacy source samplers")
        
        # 调试：输出目标采样器信息
        self._log_lines.append(f"[Legacy Debug] Target samplers:")
        for idx, t_sampler in enumerate(target.samplers):
            self._log_lines.append(f"  [{idx}] index={t_sampler.index}, base_type='{t_sampler.base_type}', is_legacy={t_sampler.is_legacy}, has_path={t_sampler.has_path}")
        
        # 遍历所有源采样器（按原始顺序）
        for src_pos, src_sampler in enumerate(source.samplers):
            if not src_sampler.has_path:
                # 无路径的源采样器，标记为 EMPTY
                results.append(MatchResult(
                    source_pos=src_pos,
                    target_pos=None,
                    status=MatchStatus.EMPTY,
                    reason="源采样器无路径，跳过匹配",
                ))
                continue
            
            if not src_sampler.is_legacy:
                # 非旧版源采样器（理论上不应该到这里，但做保护）
                results.append(MatchResult(
                    source_pos=src_pos,
                    target_pos=None,
                    status=MatchStatus.UNMATCHED,
                    reason="非旧版采样器，跳过旧版匹配逻辑",
                ))
                continue
            
            src_base_type = src_sampler.base_type
            matched_target_pos: Optional[int] = None
            match_status = MatchStatus.UNMATCHED
            match_reason = ""
            
            # === 策略1：旧版→旧版 名称完全匹配 ===
            for orig_t_pos, t_sampler in sorted_target:
                if orig_t_pos in occupied_targets:
                    continue
                if t_sampler.is_legacy and t_sampler.base_type == src_base_type:
                    matched_target_pos = orig_t_pos
                    match_status = MatchStatus.PERFECT_MATCH
                    match_reason = f"旧版名称匹配：{src_base_type}"
                    self._log_lines.append(f"[Legacy] Src[{src_pos}] {src_base_type} → Target[{orig_t_pos}] (名称匹配)")
                    break
            
            # === 策略2：旧版→新版 跨世代映射 ===
            if matched_target_pos is None and target_has_modern:
                modern_types = get_modern_mapping(src_base_type)
                if modern_types:
                    self._log_lines.append(f"[Legacy] Trying cross-gen mapping: {src_base_type} → {modern_types}")
                    
                    # 遍历目标（按 Index 排序），找第一个匹配的现代类型
                    for modern_type in modern_types:
                        if matched_target_pos is not None:
                            break  # 已找到匹配，停止
                        
                        for orig_t_pos, t_sampler in sorted_target:
                            if orig_t_pos in occupied_targets:
                                continue
                            if not t_sampler.is_legacy and t_sampler.base_type == modern_type:
                                matched_target_pos = orig_t_pos
                                match_status = MatchStatus.ADJACENT_MATCH  # 跨世代用黄色标记
                                match_reason = f"跨世代映射：{src_base_type} → {modern_type}"
                                self._log_lines.append(f"[Legacy] Src[{src_pos}] {src_base_type} → Target[{orig_t_pos}] #{t_sampler.index} {modern_type} (跨世代)")
                                break
            
            # 记录匹配结果
            if matched_target_pos is not None:
                occupied_targets.add(matched_target_pos)
                results.append(MatchResult(
                    source_pos=src_pos,
                    target_pos=matched_target_pos,
                    status=match_status,
                    reason=match_reason,
                ))
            else:
                results.append(MatchResult(
                    source_pos=src_pos,
                    target_pos=None,
                    status=MatchStatus.UNMATCHED,
                    reason=f"旧版采样器 {src_base_type} 未找到匹配目标",
                ))
                warnings.append(f"源采样器 {src_base_type} 未匹配")
        
        # 标记未覆盖的目标采样器
        for t_idx, t_sampler in enumerate(target.samplers):
            if t_idx not in occupied_targets and t_sampler.has_path:
                warnings.append(f"目标采样器 #{t_idx} ({t_sampler.base_type}) 未被覆盖")
        
        return ReplaceResult(
            source_material=source,
            target_material=target,
            results=results,
            warnings=warnings,
            order_adjustments_count=0,
            global_repair_triggered=False,
        )
    
    def _match_single_sampler(
        self,
        sorted_src_idx: int,
        orig_src_pos: int,
        src_sampler: Sampler,
        sorted_target: List[Tuple[int, Sampler]],
        occupied: List[bool],
        match_of_target: Dict[int, int],
    ) -> MatchResult:
        """
        三步匹配策略（从头搜索，无 cursor）
        
        Step 1: 完美匹配（Index + Type 相同）
        Step 2: 标记覆盖（同类型 + 有路径）
        Step 3: 类型匹配（同类型任意可用）
        
        遇到冲突时进入 Phase 2 动态调整
        """
        base_type = src_sampler.base_type
        src_index = src_sampler.index
        
        # Step 1: 完美匹配（从头搜索）
        if self.options.prefer_perfect_match:
            for t_sorted_idx, (orig_t_pos, t_sampler) in enumerate(sorted_target):
                if t_sampler.base_type == base_type and t_sampler.index == src_index:
                    if not occupied[t_sorted_idx]:
                        return MatchResult(
                            source_pos=orig_src_pos,
                            target_pos=t_sorted_idx,
                            status=MatchStatus.PERFECT_MATCH,
                            reason=f"完美匹配：类型 {base_type}，序号 {src_index}",
                        )
                    else:
                        # 冲突：目标已被占用，尝试解决
                        conflict_result = self._resolve_conflict(
                            sorted_src_idx, orig_src_pos, src_sampler,
                            t_sorted_idx, sorted_target, occupied, match_of_target
                        )
                        if conflict_result:
                            return conflict_result
        
        # Step 2: 标记覆盖（同类型 + 有路径）
        if self.options.prefer_marked_coverage:
            for t_sorted_idx, (orig_t_pos, t_sampler) in enumerate(sorted_target):
                if t_sampler.base_type == base_type and t_sampler.has_path:
                    if not occupied[t_sorted_idx]:
                        return MatchResult(
                            source_pos=orig_src_pos,
                            target_pos=t_sorted_idx,
                            status=MatchStatus.ADJACENT_MATCH,
                            reason=f"标记覆盖：类型 {base_type}，覆盖原路径",
                        )
        
        # Step 3: 类型匹配（同类型任意可用）
        for t_sorted_idx, (orig_t_pos, t_sampler) in enumerate(sorted_target):
            if t_sampler.base_type == base_type:
                if not occupied[t_sorted_idx]:
                    marker = "填充空位" if not t_sampler.has_path else "类型匹配"
                    return MatchResult(
                        source_pos=orig_src_pos,
                        target_pos=t_sorted_idx,
                        status=MatchStatus.ADJACENT_MATCH,
                        reason=f"{marker}：类型 {base_type}（目标序号 {t_sampler.index}）",
                    )
        
        # === Phase 2: Step1/2/3 全失败，尝试动态调整 ===
        if self.options.allow_order_adjustment and self._adjustment_count < self.options.max_order_adjustments:
            # 策略A：相邻交换 - 找被占用的同类型目标，让占用者移到相邻位置
            phase2_result = self._phase2_swap_neighbor(
                sorted_src_idx, orig_src_pos, src_sampler,
                sorted_target, occupied, match_of_target
            )
            if phase2_result:
                return phase2_result
            
            # 策略B：向后平移 - 在窗口内找空位并顺延
            phase2_result = self._phase2_shift_forward(
                sorted_src_idx, orig_src_pos, src_sampler,
                sorted_target, occupied, match_of_target
            )
            if phase2_result:
                return phase2_result
        
        # 无可用目标
        return MatchResult(
            source_pos=orig_src_pos,
            target_pos=None,
            status=MatchStatus.UNMATCHED,
            reason=f"未找到类型 {base_type} 的可用目标",
        )
    
    def _resolve_conflict(
        self,
        current_src_idx: int,
        orig_src_pos: int,
        src_sampler: Sampler,
        target_idx: int,
        sorted_target: List[Tuple[int, Sampler]],
        occupied: List[bool],
        match_of_target: Dict[int, int],
    ) -> Optional[MatchResult]:
        """
        Phase 2: 冲突处理
        
        当完美匹配的目标已被占用时，尝试让已占用者让位
        """
        if not self.options.allow_order_adjustment:
            return None
        
        if self._adjustment_count >= self.options.max_order_adjustments:
            return None
        
        existing_src_idx = match_of_target.get(target_idx)
        if existing_src_idx is None:
            return None
        
        base_type = src_sampler.base_type
        
        # 策略A：让已占用者找替代目标
        for alt_idx, (orig_pos, t_sampler) in enumerate(sorted_target):
            if alt_idx == target_idx:
                continue
            if t_sampler.base_type == base_type and not occupied[alt_idx]:
                # 已占用者可以移到 alt_idx
                # 让位
                occupied[alt_idx] = True
                match_of_target[alt_idx] = existing_src_idx
                occupied[target_idx] = False
                del match_of_target[target_idx]
                
                self._adjustment_count += 1
                self._log_lines.append(
                    f"[Conflict] 源{existing_src_idx} 让位到 {alt_idx}，源{current_src_idx} 占用 {target_idx}"
                )
                
                return MatchResult(
                    source_pos=orig_src_pos,
                    target_pos=target_idx,
                    status=MatchStatus.PERFECT_MATCH,
                    reason=f"完美匹配（冲突解决）：类型 {base_type}，序号 {src_sampler.index}",
                    order_adjusted=True,
                )
        
        return None
    
    def _phase2_swap_neighbor(
        self,
        sorted_src_idx: int,
        orig_src_pos: int,
        src_sampler: Sampler,
        sorted_target: List[Tuple[int, Sampler]],
        occupied: List[bool],
        match_of_target: Dict[int, int],
    ) -> Optional[MatchResult]:
        """
        Phase 2 策略A：相邻交换
        
        找被占用的同类型目标，看占用者能否移到相邻位置
        """
        base_type = src_sampler.base_type
        
        for j, (orig_pos, t_sampler) in enumerate(sorted_target):
            if t_sampler.base_type != base_type:
                continue
            if not occupied[j]:
                continue  # 未被占用，不需要交换
            
            # j 被占用，看 j+1 能否容纳被占用者
            if j + 1 < len(sorted_target):
                next_orig_pos, next_sampler = sorted_target[j + 1]
                if next_sampler.base_type == base_type and not occupied[j + 1]:
                    # 执行交换
                    prev_src = match_of_target[j]
                    match_of_target[j + 1] = prev_src
                    match_of_target[j] = sorted_src_idx
                    occupied[j + 1] = True
                    # occupied[j] 保持 True
                    
                    self._adjustment_count += 1
                    self._log_lines.append(
                        f"[Phase2-SwapNeighbor] 源{prev_src} 移至 {j+1}，源{sorted_src_idx} 占用 {j}"
                    )
                    
                    return MatchResult(
                        source_pos=orig_src_pos,
                        target_pos=j,
                        status=MatchStatus.ADJACENT_MATCH,
                        reason=f"相邻交换：类型 {base_type}，将原占用者移至 {j+1}",
                        order_adjusted=True,
                        adjustment_detail=f"swap: src{prev_src}->t{j+1}, src{sorted_src_idx}->t{j}",
                    )
        
        return None
    
    def _phase2_shift_forward(
        self,
        sorted_src_idx: int,
        orig_src_pos: int,
        src_sampler: Sampler,
        sorted_target: List[Tuple[int, Sampler]],
        occupied: List[bool],
        match_of_target: Dict[int, int],
    ) -> Optional[MatchResult]:
        """
        Phase 2 策略B：向后平移
        
        在有限窗口内找空位，尝试顺延已匹配项
        """
        base_type = src_sampler.base_type
        window = 3  # 可配置窗口大小
        
        # 找第一个同类型的被占用位置
        for start_idx, (orig_pos, t_sampler) in enumerate(sorted_target):
            if t_sampler.base_type != base_type:
                continue
            if not occupied[start_idx]:
                continue  # 如果找到空位，Step3 应该已经匹配了
            
            # 在 [start_idx, start_idx+window] 内寻找空位
            for k in range(start_idx + 1, min(start_idx + window + 1, len(sorted_target))):
                k_orig_pos, k_sampler = sorted_target[k]
                if k_sampler.base_type == base_type and not occupied[k]:
                    # 找到空位 k，可以把 start_idx 的占用者移到 k
                    prev_src = match_of_target[start_idx]
                    
                    # 执行平移
                    match_of_target[k] = prev_src
                    occupied[k] = True
                    
                    match_of_target[start_idx] = sorted_src_idx
                    # occupied[start_idx] 保持 True
                    
                    self._adjustment_count += 1
                    self._log_lines.append(
                        f"[Phase2-ShiftForward] 源{prev_src} 移至 {k}，源{sorted_src_idx} 占用 {start_idx}"
                    )
                    
                    return MatchResult(
                        source_pos=orig_src_pos,
                        target_pos=start_idx,
                        status=MatchStatus.ADJACENT_MATCH,
                        reason=f"向后平移：类型 {base_type}，窗口内顺延",
                        order_adjusted=True,
                        adjustment_detail=f"shift: src{prev_src}->t{k}, src{sorted_src_idx}->t{start_idx}",
                    )
        
        return None
    
    def _match_by_type(
        self,
        src_pos: int,
        src_sampler: Sampler,
        targets: List[Sampler],
        target_occupied: List[bool],
        target_by_type: Dict[str, List[Tuple[int, Sampler]]],
    ) -> MatchResult:
        """
        按类型匹配采样器
        
        优先级：
        1. 完美匹配：同 Type 且同 Index（优先选有路径的）
        2. 类型匹配：同 Type 但 Index 不同（优先选有路径的）
        """
        base_type = src_sampler.base_type
        src_index = src_sampler.index
        
        # 获取该类型的所有目标采样器
        candidates = target_by_type.get(base_type, [])
        
        if not candidates:
            return MatchResult(
                source_pos=src_pos,
                target_pos=None,
                status=MatchStatus.UNMATCHED,
                reason=f"目标材质中不存在类型 {base_type}",
            )
        
        # Step 1: 尝试完美匹配（Index + Type 相同）
        for t_pos, t_sampler in candidates:
            if target_occupied[t_pos]:
                continue
            if t_sampler.index == src_index:
                return MatchResult(
                    source_pos=src_pos,
                    target_pos=t_pos,
                    status=MatchStatus.PERFECT_MATCH,
                    reason=f"完美匹配：类型 {base_type}，序号 {src_index}",
                )
        
        # Step 2: 类型匹配（优先选有原路径的目标采样器，方便覆盖）
        for t_pos, t_sampler in candidates:
            if target_occupied[t_pos]:
                continue
            if t_sampler.has_path:
                return MatchResult(
                    source_pos=src_pos,
                    target_pos=t_pos,
                    status=MatchStatus.ADJACENT_MATCH,
                    reason=f"类型匹配：{base_type}，覆盖原路径（目标序号 {t_sampler.index}）",
                )
        
        # Step 3: 类型匹配（任意可用）
        for t_pos, t_sampler in candidates:
            if target_occupied[t_pos]:
                continue
            return MatchResult(
                source_pos=src_pos,
                target_pos=t_pos,
                status=MatchStatus.ADJACENT_MATCH,
                reason=f"类型匹配：{base_type}（目标序号 {t_sampler.index}）",
            )
        
        # 该类型的所有目标采样器都被占用
        return MatchResult(
            source_pos=src_pos,
            target_pos=None,
            status=MatchStatus.UNMATCHED,
            reason=f"类型 {base_type} 的所有目标采样器已被占用",
        )
    
    def get_log(self) -> List[str]:
        """获取最近一次替换的日志"""
        return getattr(self, '_log_lines', [])
        
        return None
    
    def _global_order_check_and_repair(
        self,
        sources: List[Sampler],
        targets: List[Sampler],
        results: List[MatchResult],
        occupied: List[bool],
        match_of_target: Dict[int, int],
    ) -> bool:
        """
        Phase 3: 全局顺序检查与二次修复
        
        检查所有已匹配结果是否满足源顺序约束
        发现冲突时尝试局部交换修复
        """
        # 收集已匹配的结果（索引 -> 结果）
        result_by_src = {r.source_pos: r for r in results if r.target_pos is not None}
        if len(result_by_src) < 2:
            return False
        
        # 按源排序位置排序
        matched_sorted = sorted(result_by_src.items(), key=lambda x: sources[x[0]].sorted_pos)
        
        repair_count = 0
        max_repairs = 3
        repaired = True
        
        # 迭代修复，直到无冲突或达到上限
        while repaired and repair_count < max_repairs:
            repaired = False
            
            for i in range(len(matched_sorted) - 1):
                src_i, result_i = matched_sorted[i]
                src_j, result_j = matched_sorted[i + 1]
                tgt_i = result_i.target_pos
                tgt_j = result_j.target_pos
                
                if tgt_i is None or tgt_j is None:
                    continue
                
                if tgt_i >= tgt_j:
                    # 发现冲突：src_i 的目标位置 >= src_j 的目标位置
                    # 尝试交换修复
                    
                    # 检查是否可以交换两者的目标位置
                    src_i_type = sources[src_i].base_type
                    src_j_type = sources[src_j].base_type
                    tgt_i_type = targets[tgt_i].base_type if tgt_i < len(targets) else ""
                    tgt_j_type = targets[tgt_j].base_type if tgt_j < len(targets) else ""
                    
                    # 只有类型兼容时才能交换
                    if src_i_type == tgt_j_type and src_j_type == tgt_i_type:
                        # 执行交换
                        result_i.target_pos = tgt_j
                        result_j.target_pos = tgt_i
                        result_i.order_adjusted = True
                        result_j.order_adjusted = True
                        result_i.adjustment_detail += " 全局顺序修复(交换)"
                        result_j.adjustment_detail += " 全局顺序修复(交换)"
                        
                        repair_count += 1
                        repaired = True
                        self._log_lines.append(
                            f"[Phase3-Repair] 交换 src{src_i}->t{tgt_j}, src{src_j}->t{tgt_i}"
                        )
                        
                        # 重新排序后继续检查
                        matched_sorted = sorted(result_by_src.items(), 
                                                key=lambda x: sources[x[0]].sorted_pos)
                        break
                    else:
                        # 无法交换，记录警告
                        logger.warning(
                            f"顺序冲突无法修复：源 {src_i}(pos={sources[src_i].sorted_pos}) -> 目标 {tgt_i}, "
                            f"但源 {src_j}(pos={sources[src_j].sorted_pos}) -> 目标 {tgt_j}"
                        )
                        result_i.order_adjusted = True
                        result_j.order_adjusted = True
                        result_i.adjustment_detail += " 顺序冲突(无法修复)"
                        result_j.adjustment_detail += " 顺序冲突(无法修复)"
        
        return repair_count > 0


def apply_replacement(source: Material, target: Material, result: ReplaceResult) -> Material:
    """
    应用替换结果，生成新的材质数据
    
    Args:
        source: 源材质
        target: 目标材质模板
        result: 替换结果
    
    Returns:
        新的材质对象（基于目标结构，填入源路径）
    """
    # 深拷贝目标材质
    new_samplers = []
    for t_idx, t_sampler in enumerate(target.samplers):
        new_sampler = Sampler(
            type_name=t_sampler.type_name,
            path=t_sampler.path,  # 默认保留目标路径
            scale_x=t_sampler.scale_x,
            scale_y=t_sampler.scale_y,
            unk10=t_sampler.unk10,
            unk11=t_sampler.unk11,
            unk14=t_sampler.unk14,
            unk18=t_sampler.unk18,
            unk1c=t_sampler.unk1c,
            index=t_sampler.index,
            base_type=t_sampler.base_type,
            is_legacy=t_sampler.is_legacy,
            sorted_pos=t_idx,
        )
        new_samplers.append(new_sampler)
    
    # 应用匹配结果
    for match_result in result.results:
        if match_result.target_pos is not None:
            src_sampler = source.samplers[match_result.source_pos]
            tgt_sampler = new_samplers[match_result.target_pos]
            
            # 复制路径和参数
            tgt_sampler.path = src_sampler.path
            tgt_sampler.scale_x = src_sampler.scale_x
            tgt_sampler.scale_y = src_sampler.scale_y
    
    return Material(
        name=source.name,
        mtd_path=target.mtd_path,
        samplers=new_samplers,
        gx_index=source.gx_index,
        index=source.index,
    )
