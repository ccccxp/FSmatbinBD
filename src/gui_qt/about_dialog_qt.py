# -*- coding: utf-8 -*-
"""
关于对话框
包含版本信息、GitHub链接和打赏二维码
包含完整性校验，防止内容被篡改
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QPixmap, QDesktopServices, QFont

from src.core.i18n import _
from src.core.version import get_version, get_build_date
from src.core.about_secure import (
    get_qr_images, 
    get_app_name, 
    get_developer, 
    get_github_repo,
    get_copyright_years,
    verify_integrity,
    get_integrity_error_message
)


class AboutDialog(QDialog):
    """关于对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_('about_title'))
        self.setFixedSize(520, 580)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 20, 25, 20)
        
        # 从安全模块获取受保护的信息
        app_name = get_app_name()
        developer = get_developer()
        github_repo = get_github_repo()
        copyright_years = get_copyright_years()
        
        # 应用名称和版本
        title_label = QLabel(f"<h1 style='color: #4FC3F7;'>{app_name}</h1>")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        version = get_version()
        build_date = get_build_date()
        
        version_label = QLabel(f"<p style='font-size: 14px;'>{_('about_version')}: <b>v{version}</b></p>")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)
        
        # 描述
        desc_label = QLabel(f"<p style='font-size: 12px; color: #888;'>{_('about_description_text')}</p>")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # 分隔线
        line1 = QFrame()
        line1.setFrameShape(QFrame.HLine)
        line1.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line1)
        
        # 开发信息
        info_layout = QHBoxLayout()
        info_layout.setSpacing(40)
        
        dev_label = QLabel(f"<b>{_('about_developer')}:</b> {developer}")
        dev_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(dev_label)
        
        date_label = QLabel(f"<b>{_('about_date')}:</b> {build_date}")
        date_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(date_label)
        
        layout.addLayout(info_layout)
        
        # GitHub 链接
        github_btn = QPushButton(f"⭐ GitHub: {github_repo.split('/')[-1]}")
        github_btn.setStyleSheet("""
            QPushButton {
                background-color: #333;
                color: #fff;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #444;
                border-color: #4FC3F7;
            }
        """)
        github_btn.setCursor(Qt.PointingHandCursor)
        github_btn.clicked.connect(lambda: self._open_github(github_repo))
        layout.addWidget(github_btn, alignment=Qt.AlignCenter)
        
        # 分隔线
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line2)
        
        # 打赏标题
        coffee_label = QLabel(f"<h3>☕ {_('about_buy_coffee')}</h3>")
        coffee_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(coffee_label)
        
        coffee_desc = QLabel(f"<p style='font-size: 11px; color: #888;'>{_('about_coffee_desc')}</p>")
        coffee_desc.setAlignment(Qt.AlignCenter)
        coffee_desc.setWordWrap(True)
        layout.addWidget(coffee_desc)
        
        # 二维码区域
        qr_layout = QHBoxLayout()
        qr_layout.setSpacing(30)
        qr_layout.setContentsMargins(20, 10, 20, 10)
        
        # 加载二维码图片
        wechat_data, alipay_data = get_qr_images()
        
        # 微信支付
        wechat_widget = self._create_qr_widget(wechat_data, _('about_wechat_pay'))
        qr_layout.addWidget(wechat_widget)
        
        # 支付宝
        alipay_widget = self._create_qr_widget(alipay_data, _('about_alipay'))
        qr_layout.addWidget(alipay_widget)
        
        layout.addLayout(qr_layout)
        
        # 版权信息
        copyright_label = QLabel(f"<p style='font-size: 10px; color: #666;'>© {copyright_years} {developer}. {_('about_rights')}</p>")
        copyright_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(copyright_label)
        
        # 关闭按钮
        close_btn = QPushButton(_('close_button'))
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)
    
    def _create_qr_widget(self, image_data: bytes, label_text: str) -> QWidget:
        """创建二维码显示组件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(5)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 二维码图片
        qr_label = QLabel()
        qr_label.setFixedSize(150, 150)
        qr_label.setAlignment(Qt.AlignCenter)
        qr_label.setStyleSheet("""
            QLabel {
                background-color: #fff;
                border: 2px solid #555;
                border-radius: 8px;
            }
        """)
        
        if image_data:
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    140, 140,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                qr_label.setPixmap(scaled_pixmap)
            else:
                qr_label.setText(_('about_qr_unavailable'))
        else:
            qr_label.setText(_('about_qr_unavailable'))
        
        layout.addWidget(qr_label, alignment=Qt.AlignCenter)
        
        # 标签
        text_label = QLabel(label_text)
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        layout.addWidget(text_label)
        
        return widget
    
    def _open_github(self, url: str):
        """打开GitHub页面"""
        QDesktopServices.openUrl(QUrl(url))
