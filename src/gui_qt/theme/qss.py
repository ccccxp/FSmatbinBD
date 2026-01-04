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

    /* Buttons */
    QPushButton, QToolButton {{
        border-radius: 6px;
        padding: 6px 12px;
        border: 1px solid transparent;
        background: {c['bg_secondary']};
        color: {c['fg_primary']};
    }}
    QPushButton:hover, QToolButton:hover {{
        background: {c['bg_tertiary']};
        border: 1px solid {c['border_strong']};
    }}
    QPushButton:pressed, QToolButton:pressed {{
        background: {c['accent_soft']};
        border: 1px solid {c['accent_soft']};
    }}

    /* Primary buttons: use objectName="primary" or property qproperty-isPrimary true */
    QPushButton#primary, QToolButton#primary {{
        background: {c['accent']};
        color: {c['fg_on_accent']};
        border: 1px solid {c['accent']};
    }}
    QPushButton#primary:hover, QToolButton#primary:hover {{
        background: #388bfd;
        border-color: #388bfd;
    }}
    QPushButton#primary:pressed, QToolButton#primary:pressed {{
        background: #215bb3;
        border-color: #215bb3;
    }}

    /* Ghost buttons: set objectName="ghost" */
    QPushButton#ghost, QToolButton#ghost {{
        background: transparent;
        color: {c['fg_secondary']};
        border: 1px solid transparent;
        padding: 6px 8px;
    }}
    QPushButton#ghost:hover, QToolButton#ghost:hover {{
        background: {c['bg_tertiary']};
        border: 1px solid {c['border_subtle']};
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
    """
