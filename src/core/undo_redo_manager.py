"""
撤销/重做管理器

按设计文档V3第十章 10.2 实现：
- 撤销粒度边界
- 与窗口状态保持的关系
"""

from dataclasses import dataclass, field
from typing import List, Any, Callable, Optional, Dict
from copy import deepcopy
import logging

logger = logging.getLogger(__name__)


@dataclass
class UndoAction:
    """单次撤销动作"""
    action_type: str          # 动作类型（如 'save_to_texture_edit', 'batch_replace', 'restore_source'）
    description: str          # 动作描述（用于显示）
    material_index: int       # 材质索引
    before_state: Any         # 动作前状态（MaterialEntry的深拷贝）
    after_state: Any          # 动作后状态（MaterialEntry的深拷贝）
    timestamp: float = 0.0    # 时间戳


class UndoRedoManager:
    """
    撤销/重做管理器
    
    按设计文档 10.2 撤销粒度：
    - 触发撤销记录的操作：
      1. "保存到纹理编辑"（从纹理编辑面板提交）
      2. "批量替换材质"对话框点击"保存/应用"（一次确认算一步）
      3. "还原源材质"（一次算一步）
      4. 导入JSON（清空撤销栈）
    
    - 纹理编辑面板内逐字段编辑不写入主撤销栈
    """
    
    # 最大撤销步数
    MAX_UNDO_STEPS = 50
    
    def __init__(self):
        self._undo_stack: List[UndoAction] = []
        self._redo_stack: List[UndoAction] = []
        self._listeners: List[Callable[[], None]] = []
    
    def push(self, action: UndoAction):
        """
        推入一个撤销动作
        
        调用后清空redo栈
        """
        self._undo_stack.append(action)
        self._redo_stack.clear()
        
        # 限制栈大小
        if len(self._undo_stack) > self.MAX_UNDO_STEPS:
            self._undo_stack.pop(0)
        
        self._notify_listeners()
        logger.debug(f"Push undo action: {action.action_type} - {action.description}")
    
    def undo(self) -> Optional[UndoAction]:
        """
        撤销一步
        
        Returns:
            撤销的动作，如果没有可撤销的返回 None
        """
        if not self._undo_stack:
            return None
        
        action = self._undo_stack.pop()
        self._redo_stack.append(action)
        self._notify_listeners()
        
        logger.debug(f"Undo: {action.action_type} - {action.description}")
        return action
    
    def redo(self) -> Optional[UndoAction]:
        """
        重做一步
        
        Returns:
            重做的动作，如果没有可重做的返回 None
        """
        if not self._redo_stack:
            return None
        
        action = self._redo_stack.pop()
        self._undo_stack.append(action)
        self._notify_listeners()
        
        logger.debug(f"Redo: {action.action_type} - {action.description}")
        return action
    
    def can_undo(self) -> bool:
        """是否可撤销"""
        return len(self._undo_stack) > 0
    
    def can_redo(self) -> bool:
        """是否可重做"""
        return len(self._redo_stack) > 0
    
    def undo_count(self) -> int:
        """可撤销步数"""
        return len(self._undo_stack)
    
    def redo_count(self) -> int:
        """可重做步数"""
        return len(self._redo_stack)
    
    def clear(self):
        """
        清空撤销/重做栈
        
        按设计文档 10.2：导入JSON时清空撤销栈
        """
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._notify_listeners()
        logger.debug("Undo/Redo stacks cleared")
    
    def add_listener(self, callback: Callable[[], None]):
        """添加状态变化监听器"""
        self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable[[], None]):
        """移除状态变化监听器"""
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def _notify_listeners(self):
        """通知所有监听器"""
        for listener in self._listeners:
            try:
                listener()
            except Exception as e:
                logger.error(f"Error notifying undo/redo listener: {e}")
    
    def get_undo_description(self) -> Optional[str]:
        """获取下一个撤销动作的描述"""
        if self._undo_stack:
            return self._undo_stack[-1].description
        return None
    
    def get_redo_description(self) -> Optional[str]:
        """获取下一个重做动作的描述"""
        if self._redo_stack:
            return self._redo_stack[-1].description
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典（用于状态保持）"""
        return {
            'undo_stack': [
                {
                    'action_type': a.action_type,
                    'description': a.description,
                    'material_index': a.material_index,
                    'before_state': a.before_state.to_dict() if hasattr(a.before_state, 'to_dict') else a.before_state,
                    'after_state': a.after_state.to_dict() if hasattr(a.after_state, 'to_dict') else a.after_state,
                    'timestamp': a.timestamp,
                }
                for a in self._undo_stack
            ],
            'redo_stack': [
                {
                    'action_type': a.action_type,
                    'description': a.description,
                    'material_index': a.material_index,
                    'before_state': a.before_state.to_dict() if hasattr(a.before_state, 'to_dict') else a.before_state,
                    'after_state': a.after_state.to_dict() if hasattr(a.after_state, 'to_dict') else a.after_state,
                    'timestamp': a.timestamp,
                }
                for a in self._redo_stack
            ],
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], material_entry_class) -> 'UndoRedoManager':
        """从字典反序列化"""
        manager = cls()
        
        for item in data.get('undo_stack', []):
            action = UndoAction(
                action_type=item['action_type'],
                description=item['description'],
                material_index=item['material_index'],
                before_state=material_entry_class.from_dict(item['before_state']),
                after_state=material_entry_class.from_dict(item['after_state']),
                timestamp=item.get('timestamp', 0.0),
            )
            manager._undo_stack.append(action)
        
        for item in data.get('redo_stack', []):
            action = UndoAction(
                action_type=item['action_type'],
                description=item['description'],
                material_index=item['material_index'],
                before_state=material_entry_class.from_dict(item['before_state']),
                after_state=material_entry_class.from_dict(item['after_state']),
                timestamp=item.get('timestamp', 0.0),
            )
            manager._redo_stack.append(action)
        
        return manager


def create_undo_action(
    action_type: str,
    description: str,
    material_index: int,
    before_state,
    after_state,
) -> UndoAction:
    """
    创建撤销动作的便捷函数
    
    Args:
        action_type: 动作类型
        description: 动作描述
        material_index: 材质索引
        before_state: 动作前的材质状态（会做深拷贝）
        after_state: 动作后的材质状态（会做深拷贝）
    """
    import time
    return UndoAction(
        action_type=action_type,
        description=description,
        material_index=material_index,
        before_state=before_state.copy() if hasattr(before_state, 'copy') else deepcopy(before_state),
        after_state=after_state.copy() if hasattr(after_state, 'copy') else deepcopy(after_state),
        timestamp=time.time(),
    )
