"""
平滑滚动控件 - iOS风格惯性滚动
"""
from PySide6.QtWidgets import QScrollArea, QListView, QTableView, QAbstractScrollArea
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, Qt, QEvent
from PySide6.QtGui import QWheelEvent


class SmoothScrollMixin:
    """平滑滚动混入类 - 提供iOS风格的惯性滚动效果"""
    
    def _init_smooth_scroll(self):
        """初始化平滑滚动"""
        # 垂直滚动动画
        self._v_scroll_animation = QPropertyAnimation(self.verticalScrollBar(), b"value")
        self._v_scroll_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._v_scroll_animation.setDuration(400)
        
        # 水平滚动动画
        self._h_scroll_animation = QPropertyAnimation(self.horizontalScrollBar(), b"value")
        self._h_scroll_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._h_scroll_animation.setDuration(400)
        
        # 滚动速度倍数（增加滚动距离）
        self._scroll_multiplier = 1.5
        
        # 累积滚动值（支持快速滚动累积）
        self._accumulated_delta = 0
    
    def _smooth_wheel_event(self, event: QWheelEvent):
        """处理滚轮事件，实现平滑滚动"""
        # 获取滚动增量
        delta = event.angleDelta()
        
        # 垂直滚动
        if delta.y() != 0:
            self._do_smooth_scroll(
                self._v_scroll_animation,
                self.verticalScrollBar(),
                -delta.y() * self._scroll_multiplier
            )
        
        # 水平滚动
        if delta.x() != 0:
            self._do_smooth_scroll(
                self._h_scroll_animation, 
                self.horizontalScrollBar(),
                -delta.x() * self._scroll_multiplier
            )
        
        event.accept()
    
    def _do_smooth_scroll(self, animation: QPropertyAnimation, scrollbar, delta: float):
        """执行平滑滚动动画"""
        # 如果动画正在运行，累积滚动值
        if animation.state() == QPropertyAnimation.Running:
            current_target = animation.endValue()
            new_target = current_target + delta
        else:
            new_target = scrollbar.value() + delta
        
        # 限制目标值在有效范围内
        new_target = max(scrollbar.minimum(), min(scrollbar.maximum(), new_target))
        
        # 停止当前动画并启动新动画
        animation.stop()
        animation.setStartValue(scrollbar.value())
        animation.setEndValue(int(new_target))
        animation.start()


class SmoothScrollArea(QScrollArea, SmoothScrollMixin):
    """平滑滚动区域 - 用于包裹内容区域"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_smooth_scroll()
    
    def wheelEvent(self, event: QWheelEvent):
        self._smooth_wheel_event(event)


class SmoothListView(QListView, SmoothScrollMixin):
    """
    平滑滚动列表视图 - 用于材质列表等
    特性：
    - 单次滚动精准缓慢
    - 连续滚动加速
    - 短列表弹性边界
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_smooth_scroll()
        
        # 基础滚动倍数（非常慢 - 约3-5个材质/次）
        self._base_multiplier = 0.08
        self._scroll_multiplier = self._base_multiplier
        
        # 速度累积（曲线加速）
        self._scroll_count = 0  # 滚动次数计数
        self._max_acceleration = 2.0  # 最大加速倍数（2倍）
        
        # 使用更平滑的缓动曲线
        self._v_scroll_animation.setEasingCurve(QEasingCurve.OutQuart)
        self._v_scroll_animation.setDuration(500)
        
        # 弹性边界动画（增强效果）
        self._bounce_animation = QPropertyAnimation(self.verticalScrollBar(), b"value")
        self._bounce_animation.setEasingCurve(QEasingCurve.OutBounce)  # 改用OutBounce更明显
        self._bounce_animation.setDuration(500)
        
        # 速度重置定时器
        from PySide6.QtCore import QTimer
        self._velocity_timer = QTimer()
        self._velocity_timer.setSingleShot(True)
        self._velocity_timer.setInterval(200)  # 200ms无滚动后重置
        self._velocity_timer.timeout.connect(self._reset_velocity)
    
    def _reset_velocity(self):
        """重置速度累积"""
        self._scroll_count = 0
        self._scroll_multiplier = self._base_multiplier
        # 确保动画完全停止
        if hasattr(self, '_v_scroll_animation'):
            self._v_scroll_animation.stop()
        if hasattr(self, '_bounce_animation'):
            self._bounce_animation.stop()
    
    def reset_scroll_state(self):
        """完全重置滚动状态（供外部调用，如列表刷新后）"""
        self._reset_velocity()
        self.verticalScrollBar().setValue(0)
    
    def _get_curved_acceleration(self) -> float:
        """
        曲线加速：使用平方根曲线
        滚动次数越多加速越快，但增长逐渐变慢
        """
        import math
        # 平方根曲线：1.0 -> 1.4 -> 1.7 -> 1.9 -> 2.0
        acceleration = 1.0 + min(math.sqrt(self._scroll_count) * 0.4, self._max_acceleration - 1.0)
        return acceleration
    
    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta()
        
        if delta.y() != 0:
            # 重启速度重置定时器
            self._velocity_timer.start()
            
            # 增加滚动计数，计算曲线加速
            self._scroll_count += 1
            acceleration = self._get_curved_acceleration()
            effective_multiplier = self._base_multiplier * acceleration
            
            scroll_delta = -delta.y() * effective_multiplier
            scrollbar = self.verticalScrollBar()
            
            # 检测是否到达边界
            current = scrollbar.value()
            min_val = scrollbar.minimum()
            max_val = scrollbar.maximum()
            
            # 禁用弹性边界（暂时禁用以修复跳动问题）
            # is_short_list = (max_val - min_val) < self.viewport().height() * 2
            # 
            # if is_short_list:
            #     # 短列表：弹性边界
            #     if (current <= min_val and scroll_delta < 0) or (current >= max_val and scroll_delta > 0):
            #         # 到达边界，触发弹性回弹
            #         self._do_elastic_bounce(scrollbar, current)
            #         event.accept()
            #         return
            
            # 正常滚动
            if self._v_scroll_animation.state() == QPropertyAnimation.Running:
                # 动画运行中：从当前动画目标值累积
                current_anim_value = self._v_scroll_animation.currentValue()
                new_target = self._v_scroll_animation.endValue() + scroll_delta
                start_value = current_anim_value  # 使用当前动画位置防止跳动
            else:
                new_target = current + scroll_delta
                start_value = current
            
            new_target = max(min_val, min(max_val, new_target))
            
            self._v_scroll_animation.stop()
            self._v_scroll_animation.setStartValue(start_value)
            self._v_scroll_animation.setEndValue(int(new_target))
            self._v_scroll_animation.start()
        
        event.accept()
    
    def _do_elastic_bounce(self, scrollbar, current):
        """执行弹性回弹效果"""
        self._bounce_animation.stop()
        
        # 更明显的偏移后回弹
        offset = 60 if current <= scrollbar.minimum() else -60
        
        self._bounce_animation.setStartValue(current + offset)
        self._bounce_animation.setEndValue(current)
        self._bounce_animation.start()


class SmoothTableView(QTableView, SmoothScrollMixin):
    """平滑滚动表格视图 - 用于采样器表格等"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_smooth_scroll()
    
    def wheelEvent(self, event: QWheelEvent):
        self._smooth_wheel_event(event)


from PySide6.QtWidgets import QTableWidget

class SmoothTableWidget(QTableWidget, SmoothScrollMixin):
    """平滑滚动表格控件 - 用于匹配结果表格等"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_smooth_scroll()
    
    def wheelEvent(self, event: QWheelEvent):
        self._smooth_wheel_event(event)


def apply_smooth_scroll_to_widget(widget: QAbstractScrollArea):
    """
    为现有的滚动控件添加平滑滚动效果
    注意：这种方式需要替换wheelEvent，建议优先使用上面的类
    """
    # 初始化动画
    v_animation = QPropertyAnimation(widget.verticalScrollBar(), b"value")
    v_animation.setEasingCurve(QEasingCurve.OutCubic)
    v_animation.setDuration(400)
    
    h_animation = QPropertyAnimation(widget.horizontalScrollBar(), b"value")
    h_animation.setEasingCurve(QEasingCurve.OutCubic)
    h_animation.setDuration(400)
    
    # 存储到widget
    widget._smooth_v_animation = v_animation
    widget._smooth_h_animation = h_animation
    widget._scroll_multiplier = 1.5
    
    # 保存原始wheelEvent
    original_wheel_event = widget.wheelEvent
    
    def smooth_wheel_event(event: QWheelEvent):
        delta = event.angleDelta()
        
        if delta.y() != 0:
            anim = widget._smooth_v_animation
            scrollbar = widget.verticalScrollBar()
            scroll_delta = -delta.y() * widget._scroll_multiplier
            
            if anim.state() == QPropertyAnimation.Running:
                new_target = anim.endValue() + scroll_delta
            else:
                new_target = scrollbar.value() + scroll_delta
            
            new_target = max(scrollbar.minimum(), min(scrollbar.maximum(), new_target))
            
            anim.stop()
            anim.setStartValue(scrollbar.value())
            anim.setEndValue(int(new_target))
            anim.start()
        
        if delta.x() != 0:
            anim = widget._smooth_h_animation
            scrollbar = widget.horizontalScrollBar()
            scroll_delta = -delta.x() * widget._scroll_multiplier
            
            if anim.state() == QPropertyAnimation.Running:
                new_target = anim.endValue() + scroll_delta
            else:
                new_target = scrollbar.value() + scroll_delta
            
            new_target = max(scrollbar.minimum(), min(scrollbar.maximum(), new_target))
            
            anim.stop()
            anim.setStartValue(scrollbar.value())
            anim.setEndValue(int(new_target))
            anim.start()
        
        event.accept()
    
    widget.wheelEvent = smooth_wheel_event
    return widget
