from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QPushButton, 
                             QApplication, QFrame)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QIcon, QColor, QPalette

class DarkTitleBar(QFrame):
    """
    Custom dark title bar for frameless windows.
    """
    def __init__(self, parent=None, title="Application"):
        super().__init__(parent)
        self.setFixedHeight(32)
        self.parent_window = parent
        self._setup_ui(title)
        
        self.start_pos = None
        self.is_dragging = False

    def _setup_ui(self, title):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(0)
        
        # Icon (Optional)
        # self.icon_label = QLabel()
        # layout.addWidget(self.icon_label)
        
        # Title
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #cccccc; font-weight: bold;")
        layout.addWidget(self.title_label)
        layout.addStretch()
        
        # Buttons
        self.btn_min = self._create_btn("-", self._minimize)
        layout.addWidget(self.btn_min)
        
        self.btn_max = self._create_btn("□", self._maximize)
        layout.addWidget(self.btn_max)
        
        self.btn_close = self._create_btn("✕", self._close)
        self.btn_close.setStyleSheet("QPushButton { color: #cccccc; border: none; background: transparent; } QPushButton:hover { background: #e81123; color: white; }")
        layout.addWidget(self.btn_close)
        
        self.setStyleSheet("background-color: #2d2d2d; border-bottom: 1px solid #3d3d3d;")

    def _create_btn(self, text, slot):
        btn = QPushButton(text)
        btn.setFixedSize(45, 32)
        btn.clicked.connect(slot)
        btn.setStyleSheet("""
            QPushButton { color: #cccccc; border: none; background: transparent; }
            QPushButton:hover { background: #3d3d3d; }
        """)
        return btn

    def _minimize(self):
        if self.parent_window:
            self.parent_window.showMinimized()

    def _maximize(self):
        if self.parent_window:
            if self.parent_window.isMaximized():
                self.parent_window.showNormal()
            else:
                self.parent_window.showMaximized()

    def _close(self):
        if self.parent_window:
            self.parent_window.close()

    # Dragging logic
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self.start_pos = event.globalPosition().toPoint() - self.parent_window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.is_dragging and event.buttons() & Qt.LeftButton:
            self.parent_window.move(event.globalPosition().toPoint() - self.start_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.is_dragging = False
