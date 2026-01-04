from typing import Callable, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel
)
from PySide6.QtCore import Signal, Qt

from src.core.i18n import _
from .smooth_scroll import SmoothListView


class MaterialTreePanel(QWidget):
    materialSelected = Signal(object)  # emits material_id or data object

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # top filter bar - hidden as duplicate with top search bar
        bar = QHBoxLayout()
        bar.setSpacing(6)
        self.filter_label = QLabel(_('filter'))
        bar.addWidget(self.filter_label)
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText(_('filter_by_name_shader'))
        bar.addWidget(self.filter_edit)
        # Hide filter bar (duplicate with top search)
        # layout.addLayout(bar)

        # list view with smooth scrolling
        self.list_view = SmoothListView()
        self.list_view.setEditTriggers(SmoothListView.NoEditTriggers)
        self.list_view.setSelectionMode(SmoothListView.SingleSelection)
        self.list_view.setAlternatingRowColors(True)
        self.list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 隐藏水平滚动条
        self.list_view.setStyleSheet("""
            QListView {
                background: rgba(10, 14, 24, 160);
                alternate-background-color: rgba(255, 255, 255, 5);
                border: 1px solid rgba(110, 165, 255, 90);
                border-radius: 14px;
                font-size: 9pt;
                padding: 4px;
            }
            QListView::item {
                padding: 6px 10px;
                border-radius: 6px;
                margin: 1px 2px;
            }
            QListView::item:hover {
                background-color: rgba(47, 129, 247, 18);
            }
            QListView::item:selected {
                background-color: rgba(47, 129, 247, 230);
                color: #ffffff;
            }
        """)
        self.list_view.clicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_view, 1)

    def _on_item_clicked(self, index):
        data = index.data(Qt.UserRole)
        if data is None:
            data = index.data(Qt.DisplayRole)
        self.materialSelected.emit(data)

    # placeholder loaders — to be wired with real models
    def set_model(self, model):
        self.list_view.setModel(model)

    def set_filter_text(self, text: str):
        self.filter_edit.setText(text)

    def on_filter_changed(self, callback: Callable[[str], None]):
        self.filter_edit.textChanged.connect(callback)
