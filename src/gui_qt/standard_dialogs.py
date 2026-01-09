"""
统一的消息对话框样式工具

提供预设样式的消息对话框，确保全局一致的按钮风格：
- 确认/保存: 蓝色实心渐变 (solid-blue)
- 取消: 灰色透明 (glass)
- 否/不保存/删除: 红色透明 (danger)
"""

from PySide6.QtWidgets import QMessageBox, QPushButton, QWidget
from PySide6.QtCore import Qt
from typing import Optional, Tuple, Literal

from src.core.i18n import _
from src.gui_qt.theme.palette import COLORS

C = COLORS

# ==================== 按钮样式定义 ====================

# 蓝色实心渐变样式 (用于确认、保存等正向操作)
STYLE_SOLID_BLUE = f"""
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(80, 160, 255, 0.95),
            stop:0.4 rgba(50, 130, 240, 0.9),
            stop:1 rgba(20, 100, 220, 0.85));
        border: none;
        border-radius: 6px;
        color: white;
        font-weight: bold;
        padding: 0px 12px;
        min-width: 0px;
        height: 32px;
    }}
    QPushButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(100, 180, 255, 1.0),
            stop:0.4 rgba(70, 150, 255, 0.95),
            stop:1 rgba(40, 120, 240, 0.9));
    }}
    QPushButton:pressed {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(30, 110, 235, 0.95),
            stop:1 rgba(10, 90, 200, 0.9));
    }}
"""

# 灰色透明样式 (用于取消等中性操作)
STYLE_GLASS = f"""
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(99, 110, 123, 0.15),
            stop:1 rgba(77, 87, 97, 0.25));
        border: 1px solid {C['border_subtle']};
        border-radius: 6px;
        color: {C['fg_primary']};
        padding: 0px 12px;
        min-width: 0px;
        height: 32px;
    }}
    QPushButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(139, 148, 158, 0.3),
            stop:1 rgba(110, 120, 130, 0.4));
        border: 1px solid {C['border_strong']};
        color: white;
    }}
    QPushButton:pressed {{
        background: rgba(99, 110, 123, 0.4);
    }}
"""

# 红色透明样式 (用于不保存、删除等破坏性操作)
STYLE_DANGER = f"""
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(248, 81, 73, 0.2),
            stop:1 rgba(218, 54, 51, 0.3));
        border: 1px solid #F85149;
        border-radius: 6px;
        color: #FFEBE9;
        padding: 0px 12px;
        min-width: 0px;
        height: 32px;
    }}
    QPushButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(255, 100, 90, 0.4),
            stop:1 rgba(230, 70, 70, 0.5));
        border: 1px solid #FF7B72;
        color: white;
    }}
    QPushButton:pressed {{
        background: rgba(248, 81, 73, 0.5);
    }}
"""


# 橙色透明样式 (用于浏览、编辑等可以引起注意的操作)
STYLE_ORANGE_TRANSPARENT = f"""
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(210, 153, 34, 0.15),
            stop:1 rgba(187, 128, 9, 0.25));
        border: 1px solid #D29922;
        border-radius: 6px;
        color: #FFEBC9;
        padding: 0px 12px;
        min-width: 0px;
        height: 32px;
    }}
    QPushButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(210, 153, 34, 0.3),
            stop:1 rgba(187, 128, 9, 0.4));
        border: 1px solid #E3B341;
        color: white;
    }}
    QPushButton:pressed {{
        background: rgba(210, 153, 34, 0.4);
    }}
"""


# 蓝色透明样式 (用于添加条件等操作)
STYLE_BLUE_TRANSPARENT = f"""
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(80, 160, 255, 0.15),
            stop:1 rgba(60, 130, 230, 0.25));
        border: 1px solid rgba(80, 160, 255, 0.5);
        border-radius: 6px;
        color: rgba(180, 210, 255, 0.9);
        padding: 0px 12px;
        min-width: 0px;
        height: 32px;
    }}
    QPushButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(80, 160, 255, 0.3),
            stop:1 rgba(60, 130, 230, 0.4));
        border: 1px solid rgba(100, 180, 255, 0.8);
        color: white;
    }}
    QPushButton:pressed {{
        background: rgba(80, 160, 255, 0.4);
    }}
"""

# 浅绿色切换样式 (用于精确匹配)
STYLE_LIGHT_GREEN_TOGGLE = f"""
    QPushButton {{
        background: rgba(40, 167, 69, 0.15);
        border: 1px solid rgba(40, 167, 69, 0.5);
        border-radius: 6px;
        color: rgba(160, 255, 180, 0.9);
        padding: 0px 12px;
        min-width: 0px;
        height: 50px;
    }}
    QPushButton:hover {{
        background: rgba(40, 167, 69, 0.25);
        border: 1px solid rgba(40, 167, 69, 0.8);
        color: white;
    }}
    QPushButton:checked {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(40, 167, 69, 0.9),
            stop:1 rgba(30, 130, 50, 0.8));
        border: 1px solid rgba(40, 167, 69, 1.0);
        color: white;
        font-weight: bold;
    }}
"""

# 浅粉色切换样式 (用于模糊匹配)
STYLE_LIGHT_PINK_TOGGLE = f"""
    QPushButton {{
        background: rgba(232, 62, 140, 0.15);
        border: 1px solid rgba(232, 62, 140, 0.5);
        border-radius: 6px;
        color: rgba(255, 180, 210, 0.9);
        padding: 0px 12px;
        min-width: 0px;
        height: 50px;
    }}
    QPushButton:hover {{
        background: rgba(232, 62, 140, 0.25);
        border: 1px solid rgba(232, 62, 140, 0.8);
        color: white;
    }}
    QPushButton:checked {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(232, 62, 140, 0.9),
            stop:1 rgba(200, 50, 120, 0.8));
        border: 1px solid rgba(232, 62, 140, 1.0);
        color: white;
        font-weight: bold;
    }}
"""


# ==================== 样式应用函数 ====================

def apply_button_style(button: QPushButton, style: Literal['solid-blue', 'glass', 'danger', 'orange-transparent', 'blue-transparent', 'green-toggle', 'pink-toggle']):
    """为按钮应用预设样式"""
    styles = {
        'solid-blue': STYLE_SOLID_BLUE,
        'glass': STYLE_GLASS,
        'danger': STYLE_DANGER,
        'orange-transparent': STYLE_ORANGE_TRANSPARENT,
        'blue-transparent': STYLE_BLUE_TRANSPARENT,
        'green-toggle': STYLE_LIGHT_GREEN_TOGGLE,
        'pink-toggle': STYLE_LIGHT_PINK_TOGGLE,
    }
    button.setStyleSheet(styles.get(style, STYLE_GLASS))


# ==================== 消息对话框函数 ====================

def show_unsaved_changes_dialog(parent: QWidget) -> QMessageBox.StandardButton:
    """
    显示未保存更改对话框
    
    Returns:
        QMessageBox.StandardButton.Save: 用户选择保存
        QMessageBox.StandardButton.Discard: 用户选择不保存
        QMessageBox.StandardButton.Cancel: 用户选择取消
    """
    msg = QMessageBox(parent)
    msg.setWindowTitle(_('unsaved_changes') if _('unsaved_changes') != 'unsaved_changes' else "未保存的更改")
    msg.setText(_('unsaved_changes_close_confirm') if _('unsaved_changes_close_confirm') != 'unsaved_changes_close_confirm' else "有未保存的更改，是否保存后退出?")
    msg.setIcon(QMessageBox.Icon.Question)
    
    # 保存按钮 (蓝色实心)
    save_text = _('save') if _('save') != 'save' else "保存"
    save_btn = msg.addButton(save_text, QMessageBox.ButtonRole.AcceptRole)
    apply_button_style(save_btn, 'solid-blue')
    
    # 不保存按钮 (红色透明)
    discard_text = _('discard_changes') if _('discard_changes') != 'discard_changes' else "不保存"
    discard_btn = msg.addButton(discard_text, QMessageBox.ButtonRole.DestructiveRole)
    apply_button_style(discard_btn, 'danger')
    
    # 取消按钮 (灰色)
    cancel_text = _('cancel') if _('cancel') != 'cancel' else "取消"
    cancel_btn = msg.addButton(cancel_text, QMessageBox.ButtonRole.RejectRole)
    apply_button_style(cancel_btn, 'glass')
    
    msg.exec()
    
    clicked = msg.clickedButton()
    if clicked == save_btn:
        return QMessageBox.StandardButton.Save
    elif clicked == discard_btn:
        return QMessageBox.StandardButton.Discard
    else:
        return QMessageBox.StandardButton.Cancel


def show_confirm_dialog(
    parent: QWidget,
    title: str,
    message: str,
    confirm_text: str = None,
    cancel_text: str = None,
    confirm_style: Literal['solid-blue', 'danger'] = 'solid-blue'
) -> bool:
    """
    显示确认对话框
    
    Args:
        parent: 父窗口
        title: 对话框标题
        message: 消息内容
        confirm_text: 确认按钮文字 (默认为翻译的"确认")
        cancel_text: 取消按钮文字 (默认为翻译的"取消")
        confirm_style: 确认按钮样式 ('solid-blue' 或 'danger')
    
    Returns:
        True: 用户确认
        False: 用户取消
    """
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setIcon(QMessageBox.Icon.Question)
    
    # 确认按钮
    confirm_text = confirm_text or (_('confirm') if _('confirm') != 'confirm' else "确认")
    confirm_btn = msg.addButton(confirm_text, QMessageBox.ButtonRole.AcceptRole)
    apply_button_style(confirm_btn, confirm_style)
    
    # 取消按钮
    cancel_text = cancel_text or (_('cancel') if _('cancel') != 'cancel' else "取消")
    cancel_btn = msg.addButton(cancel_text, QMessageBox.ButtonRole.RejectRole)
    apply_button_style(cancel_btn, 'glass')
    
    msg.exec()
    
    return msg.clickedButton() == confirm_btn


def show_yes_no_dialog(
    parent: QWidget,
    title: str,
    message: str,
    yes_text: str = None,
    no_text: str = None,
) -> bool:
    """
    显示是/否对话框 (否按钮为红色样式)
    
    Args:
        parent: 父窗口
        title: 对话框标题
        message: 消息内容
        yes_text: "是"按钮文字
        no_text: "否"按钮文字
    
    Returns:
        True: 用户选择"是"
        False: 用户选择"否"
    """
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setIcon(QMessageBox.Icon.Question)
    
    # 是 按钮 (蓝色)
    yes_text = yes_text or (_('yes') if _('yes') != 'yes' else "是")
    yes_btn = msg.addButton(yes_text, QMessageBox.ButtonRole.YesRole)
    apply_button_style(yes_btn, 'solid-blue')
    
    # 否 按钮 (红色)
    no_text = no_text or (_('no') if _('no') != 'no' else "否")
    no_btn = msg.addButton(no_text, QMessageBox.ButtonRole.NoRole)
    apply_button_style(no_btn, 'danger')
    
    msg.exec()
    
    return msg.clickedButton() == yes_btn


def show_info_dialog(parent: QWidget, title: str, message: str, button_text: str = None):
    """显示信息对话框"""
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setIcon(QMessageBox.Icon.Information)
    
    button_text = button_text or (_('ok') if _('ok') != 'ok' else "确定")
    ok_btn = msg.addButton(button_text, QMessageBox.ButtonRole.AcceptRole)
    apply_button_style(ok_btn, 'solid-blue')
    
    msg.exec()


def show_warning_dialog(parent: QWidget, title: str, message: str, button_text: str = None):
    """显示警告对话框"""
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setIcon(QMessageBox.Icon.Warning)
    
    button_text = button_text or (_('ok') if _('ok') != 'ok' else "确定")
    ok_btn = msg.addButton(button_text, QMessageBox.ButtonRole.AcceptRole)
    apply_button_style(ok_btn, 'glass')
    
    msg.exec()


def show_error_dialog(parent: QWidget, title: str, message: str, button_text: str = None):
    """显示错误对话框"""
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setIcon(QMessageBox.Icon.Critical)
    
    button_text = button_text or (_('ok') if _('ok') != 'ok' else "确定")
    ok_btn = msg.addButton(button_text, QMessageBox.ButtonRole.AcceptRole)
    apply_button_style(ok_btn, 'danger')
    
    msg.exec()


def show_yes_no_cancel_dialog(
    parent: QWidget,
    title: str,
    message: str,
    yes_text: str = None,
    no_text: str = None,
    cancel_text: str = None,
) -> Optional[bool]:
    """
    显示是/否/取消对话框
    
    Args:
        parent: 父窗口
        title: 对话框标题
        message: 消息内容
        yes_text: "是"按钮文字
        no_text: "否"按钮文字
        cancel_text: "取消"按钮文字
    
    Returns:
        True: 用户选择"是"
        False: 用户选择"否"
        None: 用户选择"取消"
    """
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setIcon(QMessageBox.Icon.Question)
    
    # 是 按钮 (蓝色)
    yes_text = yes_text or (_('yes') if _('yes') != 'yes' else "是")
    yes_btn = msg.addButton(yes_text, QMessageBox.ButtonRole.YesRole)
    apply_button_style(yes_btn, 'solid-blue')
    
    # 否 按钮 (红色)
    no_text = no_text or (_('no') if _('no') != 'no' else "否")
    no_btn = msg.addButton(no_text, QMessageBox.ButtonRole.NoRole)
    apply_button_style(no_btn, 'danger')
    
    # 取消 按钮 (灰色)
    cancel_text = cancel_text or (_('cancel') if _('cancel') != 'cancel' else "取消")
    cancel_btn = msg.addButton(cancel_text, QMessageBox.ButtonRole.RejectRole)
    apply_button_style(cancel_btn, 'glass')
    
    msg.exec()
    
    clicked = msg.clickedButton()
    if clicked == yes_btn:
        return True
    elif clicked == no_btn:
        return False
    else:
        return None
