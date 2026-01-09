from .palette import COLORS


def load_stylesheet() -> str:
    c = COLORS
    return f"""
    /* Global */
    QWidget {{
        background: {c['bg_primary']};
        color: {c['fg_primary']};
        font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
        /* 使用 pt 而不是 px：Qt 在 px 字体下常出现 pointSize=-1（像素字体），
           部分平台/样式组合会触发 QFont::setPointSize(...) 警告。
           这里改为 pt 以获得稳定的 pointSize。 */
        font-size: 10pt;
    }}

    /* Remove default focus outlines / bright borders (often show up as white rectangles) */
    *:focus {{
        outline: none;
    }}

    QFrame {{
        outline: none;
    }}

    QLabel {{
        border: none;
        background: transparent;
    }}

    QScrollArea {{
        border: 0px;
        background: transparent;
    }}
    QScrollArea > QWidget > QWidget {{
        background: transparent;
    }}
    QScrollArea QWidget#qt_scrollarea_viewport {{
        background: transparent;
        border: 0px;
    }}

    /* Menus / popup lists (ComboBox dropdown, ToolButton menu) */
    QMenu {{
        background: {c['bg_secondary']};
        color: {c['fg_primary']};
        border: 1px solid {c['border_subtle']};
        border-radius: 10px;
        padding: 6px;
    }}
    QMenu::item {{
        padding: 8px 10px;
        border-radius: 8px;
    }}
    QMenu::item:selected {{
        background: {c['accent_soft']};
    }}

    QComboBox QAbstractItemView {{
        background: {c['bg_secondary']};
        color: {c['fg_primary']};
        border: 1px solid {c['border_subtle']};
        border-radius: 10px;
        outline: 0;
        selection-background-color: {c['accent_soft']};
        selection-color: {c['fg_primary']};
        padding: 6px;
    }}
    QComboBox QAbstractItemView::item {{
        padding: 8px 10px;
        border-radius: 8px;
    }}
    QComboBox QAbstractItemView::item:hover {{
        background: {c['accent_soft']};
    }}

    /* ScrollBars (popup lists often show bright frames without this) */
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {c['border_strong']};
        border-radius: 5px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c['accent_soft']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}

    QMainWindow {{
        background: {c['bg_primary']};
    }}

    /* CommandBar / Toolbar like background helpers */
    QToolBar {{
        background: {c['bg_secondary']};
        border: 0px;
        padding: 6px;
        spacing: 6px;
    }}
    QToolBar::separator {{
        background: {c['border_subtle']};
        width: 1px;
        margin: 4px;
    }}

    /* Buttons (Global Base) */
    QPushButton, QToolButton {{
        border-radius: 6px;
        padding: 6px 14px;
        font-weight: bold;
        font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
        color: white;
        border: 1px solid transparent;
        background: transparent;
    }}

    /* 1. General Button (Deep Grey Gradient - "Other General Buttons") */
    QPushButton#glass, QToolButton#glass, QPushButton#ghost, QToolButton#ghost {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(60, 65, 75, 0.7),
            stop:1 rgba(40, 45, 50, 0.8));
        border: 1px solid rgba(255, 255, 255, 0.15);
        color: rgba(255, 255, 255, 0.9);
    }}
    QPushButton#glass:hover, QToolButton#glass:hover, QPushButton#ghost:hover, QToolButton#ghost:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(70, 75, 85, 0.8),
            stop:1 rgba(50, 55, 60, 0.9));
        border: 1px solid rgba(255, 255, 255, 0.3);
        color: white;
    }}
    QPushButton#glass:pressed, QToolButton#glass:pressed, QPushButton#ghost:pressed, QToolButton#ghost:pressed {{
        background: rgba(30, 35, 40, 0.9);
        border: 1px solid rgba(255, 255, 255, 0.4);
    }}

    /* 2. Blue Glass (Transparent - For Import/Match) */
    QPushButton#blue-glass, QToolButton#blue-glass {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(47, 129, 247, 0.15),
            stop:1 rgba(28, 104, 217, 0.25));
        border: 1px solid #2F81F7;
        color: #E6EDFA;
    }}
    QPushButton#blue-glass:hover, QToolButton#blue-glass:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(56, 139, 253, 0.3),
            stop:1 rgba(37, 114, 227, 0.4));
        border: 1px solid #58A6FF;
        color: white;
    }}
    QPushButton#blue-glass:pressed, QToolButton#blue-glass:pressed {{
        background: rgba(47, 129, 247, 0.4);
    }}

    /* 3. Purple Glass (Transparent - For Replace) */
    QPushButton#purple-glass, QToolButton#purple-glass {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(163, 113, 247, 0.15),
            stop:1 rgba(137, 87, 229, 0.25));
        border: 1px solid #8957e5;
        color: #E6EDFA;
    }}
    QPushButton#purple-glass:hover, QToolButton#purple-glass:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(176, 130, 253, 0.3),
            stop:1 rgba(150, 100, 240, 0.4));
        border: 1px solid #bc8cff;
        color: white;
    }}
    QPushButton#purple-glass:pressed, QToolButton#purple-glass:pressed {{
        background: rgba(137, 87, 229, 0.4);
    }}

    /* 3b. Green Glass (Transparent - For Move Up) */
    QPushButton#green-glass, QToolButton#green-glass {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(63, 185, 80, 0.15),
            stop:1 rgba(35, 134, 54, 0.25));
        border: 1px solid #3fb950;
        color: #E6EDFA;
    }}
    QPushButton#green-glass:hover, QToolButton#green-glass:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(70, 200, 90, 0.3),
            stop:1 rgba(45, 150, 65, 0.4));
        border: 1px solid #56d364;
        color: white;
    }}
    QPushButton#green-glass:pressed, QToolButton#green-glass:pressed {{
        background: rgba(35, 134, 54, 0.4);
    }}

    /* 3c. Pink Glass (Transparent - For Move Down) */
    QPushButton#pink-glass, QToolButton#pink-glass {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(255, 123, 156, 0.15),
            stop:1 rgba(228, 90, 125, 0.25));
        border: 1px solid #ff7b9c;
        color: #E6EDFA;
    }}
    QPushButton#pink-glass:hover, QToolButton#pink-glass:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(255, 140, 170, 0.3),
            stop:1 rgba(240, 110, 145, 0.4));
        border: 1px solid #ffafc5;
        color: white;
    }}
    QPushButton#pink-glass:pressed, QToolButton#pink-glass:pressed {{
        background: rgba(228, 90, 125, 0.4);
    }}

    /* 4. Vivid Primary (Semi-Transparent - For Search, Save, Start) */
    /* "No solid, add transparency, gradient more obvious" */
    /* 明亮的蓝色渐变，白色文字，无边框，左上到右下渐变，带透明度 */
    QPushButton#primary, QToolButton#primary, QPushButton#solid-blue, QToolButton#solid-blue {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(80, 160, 255, 0.95),
            stop:0.4 rgba(50, 130, 240, 0.9),
            stop:1 rgba(20, 100, 220, 0.85));
        border: none;
        border-radius: 6px;
        color: white;
        font-weight: bold;
        padding: 6px 16px;
        font-family: "Microsoft YaHei", "Segoe UI";
    }}
    QPushButton#primary:hover, QToolButton#primary:hover, QPushButton#solid-blue:hover, QToolButton#solid-blue:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(100, 180, 255, 1.0),
            stop:0.4 rgba(70, 150, 255, 0.95),
            stop:1 rgba(40, 120, 240, 0.9));
        color: white;
    }}
    QPushButton#primary:pressed, QToolButton#primary:pressed, QPushButton#solid-blue:pressed, QToolButton#solid-blue:pressed {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(30, 110, 235, 0.95),
            stop:1 rgba(10, 90, 200, 0.9));
        color: white;
        padding-top: 7px; /* Press effect */
        padding-left: 17px;
    }}

    /* 5. Warning Button */
    QPushButton#warning, QToolButton#warning {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(210, 153, 34, 0.2),
            stop:1 rgba(176, 125, 21, 0.3));
        border: 1px solid #D29922;
        color: #FAEBC6;
    }}
    QPushButton#warning:hover, QToolButton#warning:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(234, 172, 44, 0.4),
            stop:1 rgba(200, 149, 31, 0.5));
        border: 1px solid #EAC54F;
        color: white;
    }}

    /* 6. Danger Button */
    QPushButton#danger, QToolButton#danger {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(248, 81, 73, 0.2),
            stop:1 rgba(218, 54, 51, 0.3));
        border: 1px solid #F85149;
        color: #FFEBE9;
    }}
    QPushButton#danger:hover, QToolButton#danger:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(255, 100, 90, 0.4),
            stop:1 rgba(230, 70, 70, 0.5));
        border: 1px solid #FF7B72;
        color: white;
    }}

    /* 7. Solid Orange Button (For Edit, Edit Texture) */
    /* 明亮的橙黄渐变，白色文字，无边框，左上到右下渐变，带透明度 */
    QPushButton#solid-orange, QToolButton#solid-orange {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(255, 215, 80, 0.95),
            stop:0.4 rgba(255, 180, 40, 0.9),
            stop:1 rgba(255, 140, 0, 0.85));
        border: none;
        border-radius: 6px;
        color: white;
        font-weight: bold;
        padding: 4px 12px;
        font-family: "Microsoft YaHei", "Segoe UI";
    }}
    QPushButton#solid-orange:hover, QToolButton#solid-orange:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(255, 230, 110, 1.0),
            stop:0.4 rgba(255, 200, 60, 0.95),
            stop:1 rgba(255, 160, 20, 0.9));
        color: white;
    }}
    QPushButton#solid-orange:pressed, QToolButton#solid-orange:pressed {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(230, 120, 0, 0.95),
            stop:1 rgba(200, 100, 0, 0.9));
        color: white;
        padding-top: 5px; /* Press effect */
        padding-left: 13px;
    }}

    /* Line edits */
    QLineEdit {{
        background: {c['input_bg']};
        color: {c['fg_primary']};
        border: 1px solid {c['input_border']};
        border-radius: 6px;
        padding: 6px 8px;
    }}
    QLineEdit:focus {{
        border: 1px solid {c['accent']};
    }}

    QLineEdit:disabled {{
        background: {c['bg_secondary']};
        border: 1px solid {c['border_subtle']};
        color: {c['fg_secondary']};
    }}

    /* ComboBox */
    QComboBox {{
        background: {c['input_bg']};
        color: {c['fg_primary']};
        border: 1px solid {c['input_border']};
        border-radius: 6px;
        padding: 6px 8px;
    }}
    QComboBox:hover {{
        border: 1px solid {c['accent_soft']};
    }}

    QComboBox:disabled {{
        background: {c['bg_secondary']};
        border: 1px solid {c['border_subtle']};
        color: {c['fg_secondary']};
    }}
    QComboBox QAbstractItemView {{
        background: {c['bg_secondary']};
        selection-background-color: {c['bg_tertiary']};
        color: {c['fg_primary']};
    }}

    /* Splitter */
    QSplitter::handle {{
        background: {c['bg_secondary']};
    }}
    QSplitter::handle:hover {{
        background: {c['accent_soft']};
    }}

    /* Tree/Table */
    QTreeView, QListView, QTableView {{
        background: {c['bg_secondary']};
        alternate-background-color: {c['bg_tertiary']};
        border: 1px solid {c['border_subtle']};
        selection-background-color: {c['bg_tertiary']};
        selection-color: {c['fg_primary']};
        gridline-color: {c['border_subtle']};
    }}
    QHeaderView::section {{
        background: {c['bg_tertiary']};
        color: {c['fg_primary']};
        border: 0px;
        padding: 6px;
    }}

    /* Status bar */
    QStatusBar {{
        background: {c['bg_secondary']};
        color: {c['fg_secondary']};
    }}

    /* Tooltip */
    QToolTip {{
        background: {c['bg_secondary']};
        color: {c['fg_primary']};
        border: 1px solid {c['border_subtle']};
        border-radius: 8px;
        padding: 6px;
    }}

    /* Tabs */
    QTabBar::tab {{
        background: {c['bg_secondary']};
        color: {c['fg_secondary']};
        padding: 6px 10px;
        border: 1px solid transparent;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        margin-right: 4px;
    }}
    QTabBar::tab:selected {{
        background: {c['bg_tertiary']};
        color: {c['fg_primary']};
        border: 1px solid {c['border_subtle']};
    }}
    QTabWidget::pane {{
        border: 1px solid {c['border_subtle']};
        border-radius: 10px;
        top: -1px;
    }}

    /* Checkbox */
    QCheckBox {{
        color: {c['fg_secondary']};
        spacing: 6px;
        background: transparent;
    }}
    QCheckBox::indicator {{
        width: 14px;
        height: 14px;
        border: 2px solid {c['accent']};
        border-radius: 3px;
        background: transparent;
    }}
    QCheckBox::indicator:hover {{
        border-color: #4a9aff;
    }}
    QCheckBox::indicator:checked {{
        background: {c['accent']};
        border-color: {c['accent']};
        image: url(src/gui_qt/assets/checkbox_check_white.svg);
    }}
    QCheckBox:disabled {{
        color: {c['fg_muted']};
    }}
    QCheckBox::indicator:disabled {{
        border-color: {c['border_subtle']};
    }}
    """


def apply_glow_effect(widget, color=(47, 129, 247), blur_radius=15, enabled=True):
    """
    为按钮应用发光效果（使用 QGraphicsDropShadowEffect）
    
    Args:
        widget: 目标按钮（QPushButton 或 QToolButton）
        color: RGB 颜色元组 (R, G, B)
        blur_radius: 模糊半径
        enabled: 是否启用
        
    用法：
        from src.gui_qt.theme.qss import apply_glow_effect
        apply_glow_effect(my_button)
    """
    from PySide6.QtWidgets import QGraphicsDropShadowEffect
    from PySide6.QtGui import QColor
    from PySide6.QtCore import QObject, QEvent
    
    class HoverGlowFilter(QObject):
        """悬停时切换阴影效果的事件过滤器"""
        
        def __init__(self, widget, color, blur_radius):
            super().__init__(widget)
            self.widget = widget
            self.color = color
            self.blur_radius = blur_radius
        
        def eventFilter(self, obj, event):
            try:
                if obj == self.widget:
                    if event.type() == QEvent.Enter:
                        # 鼠标进入：添加阴影
                        self._apply_shadow()
                    elif event.type() == QEvent.Leave:
                        # 鼠标离开：移除阴影
                        self._remove_shadow()
            except RuntimeError:
                # 对象已被删除，忽略
                pass
            return False
        
        def _apply_shadow(self):
            try:
                # 每次都创建新的效果，因为 setGraphicsEffect(None) 会删除之前的效果
                shadow_effect = QGraphicsDropShadowEffect(self.widget)
                shadow_effect.setBlurRadius(self.blur_radius)
                shadow_effect.setColor(QColor(*self.color, 180))  # 半透明
                shadow_effect.setOffset(0, 0)  # 无偏移，均匀发光
                self.widget.setGraphicsEffect(shadow_effect)
            except RuntimeError:
                # 对象已被删除，忽略
                pass
        
        def _remove_shadow(self):
            try:
                self.widget.setGraphicsEffect(None)
            except RuntimeError:
                # 对象已被删除，忽略
                pass
    
    if enabled:
        glow_filter = HoverGlowFilter(widget, color, blur_radius)
        widget.installEventFilter(glow_filter)
        # 保持对过滤器的引用，防止被垃圾回收
        widget._glow_filter = glow_filter

