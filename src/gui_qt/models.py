"""
Qt models for library list, material list, and samplers.
These are lightweight wrappers over existing database data.
"""
from typing import List, Dict, Any, Optional
import json
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt, QAbstractListModel, QModelIndex
from src.core.i18n import _

class LibraryListModel(QStandardItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.libraries: List[Dict[str, Any]] = []

    def load(self, libraries: List[Dict[str, Any]]):
        self.clear()
        self.libraries = libraries
        for lib in libraries:
            item = QStandardItem(f"{lib.get('name', '')} (ID:{lib.get('id')})")
            item.setData(lib, Qt.UserRole)
            item.setEditable(False)
            self.appendRow(item)

    def get_library_id(self, index) -> Optional[int]:
        if not index.isValid():
            return None
        data = index.data(Qt.UserRole)
        if isinstance(data, dict):
            return data.get('id')
        return None

class MaterialListModel(QAbstractListModel):
    """高性能材质列表模型 - 使用 QAbstractListModel 实现按需渲染"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.materials: List[Dict[str, Any]] = []

    def load(self, materials: List[Dict[str, Any]]):
        """加载材质列表（高性能：直接替换数据，无需创建Item对象）"""
        self.beginResetModel()
        self.materials = materials or []
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.materials)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self.materials):
            return None
        
        material = self.materials[index.row()]
        
        if role == Qt.DisplayRole:
            return material.get('filename') or material.get('file_name') or _('unknown_material')
        elif role == Qt.UserRole:
            return material
        
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def get_material_id(self, index: QModelIndex) -> Optional[int]:
        if not index.isValid() or index.row() >= len(self.materials):
            return None
        material = self.materials[index.row()]
        if isinstance(material, dict):
            return material.get('id')
        return None


class SamplerTableModel(QStandardItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHorizontalHeaderLabels([_('header_type'), _('header_path'), _('header_key'), _('header_x'), _('header_y')])

    def load(self, samplers: List[Dict[str, Any]]):
        self.setRowCount(0)
        # Refresh headers for dynamic language support
        self.setHorizontalHeaderLabels([_('header_type'), _('header_path'), _('header_key'), _('header_x'), _('header_y')])
        for sampler in samplers:
            row = []
            row.append(QStandardItem(str(sampler.get('type', ''))))
            row.append(QStandardItem(str(sampler.get('path', ''))))
            row.append(QStandardItem(str(sampler.get('key_value', ''))))
            unk = sampler.get('unk14', {}) or {}
            row.append(QStandardItem(str(unk.get('X', ''))))
            row.append(QStandardItem(str(unk.get('Y', ''))))
            for it in row:
                it.setEditable(False)
                # 内容居中显示
                it.setTextAlignment(Qt.AlignCenter)
            self.appendRow(row)


class ParamTableModel(QStandardItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHorizontalHeaderLabels([_('header_name'), _('header_type'), _('header_value'), _('header_key')])
        self._params: List[Dict[str, Any]] = []

    def load(self, params: List[Dict[str, Any]]):
        """加载参数，并允许编辑值与Key列。"""
        self.setRowCount(0)
        # Refresh headers for dynamic language support
        self.setHorizontalHeaderLabels([_('header_name'), _('header_type'), _('header_value'), _('header_key')])
        self._params = params or []
        for p in self._params:
            name_item = QStandardItem(str(p.get('name', '')))
            name_item.setEditable(False)

            type_item = QStandardItem(str(p.get('type', '')))
            type_item.setEditable(False)

            val = p.get('value', '')
            if isinstance(val, (list, dict)):
                val_disp = json.dumps(val, ensure_ascii=False)
            else:
                val_disp = str(val)
            value_item = QStandardItem(val_disp)
            value_item.setEditable(True)

            key_item = QStandardItem(str(p.get('key_value', '')))
            key_item.setEditable(True)

            self.appendRow([name_item, type_item, value_item, key_item])

    def _parse_value(self, text: str, ptype: str = "", strict: bool = False):
        """根据类型解析文本。strict=True 时遇到非法格式将抛出 ValueError。"""
        stripped = text.strip()
        if stripped == "":
            return ""

        lower_t = (ptype or "").lower()
        # 数值型
        try:
            if "int" in lower_t:
                return int(stripped)
            if any(k in lower_t for k in ["float", "double", "real"]):
                return float(stripped)
            if "bool" in lower_t:
                if stripped.lower() in ["true", "1", "yes", "on"]:
                    return True
                if stripped.lower() in ["false", "0", "no", "off"]:
                    return False
                raise ValueError(f"无法解析布尔值: {text}")
        except Exception as e:
            if strict:
                raise
            return text

        # 尝试 JSON（列表/字典/数字/布尔）
        try:
            return json.loads(stripped)
        except Exception:
            if strict and (stripped.startswith("[") or stripped.startswith("{")):
                raise
            return stripped

    def to_params(self) -> List[Dict[str, Any]]:
        """从模型提取当前参数列表，供保存使用。"""
        params: List[Dict[str, Any]] = []
        for row in range(self.rowCount()):
            name = self.item(row, 0).text().strip()
            ptype = self.item(row, 1).text().strip()
            value_text = self.item(row, 2).text()
            key_text = self.item(row, 3).text().strip()
            params.append({
                'name': name,
                'type': ptype,
                'value': self._parse_value(value_text, ptype=ptype, strict=True),
                'key': key_text,
                'key_value': key_text,  # 兼容旧字段命名
            })
        return params