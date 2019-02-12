"""Section with table that shows recently collected materials and their total count"""
import logging
from collections import OrderedDict

from PyQt5 import QtWidgets, QtCore

from edp import journal, entities, utils
from edp.gui.components.base import BaseMainWindowSection

logger = logging.getLogger(__name__)


class MaterialsStorageModel(QtCore.QAbstractTableModel):
    """Qt model implementation for materials"""
    maximum_length = 10

    def __init__(self, *args, **kwargs):
        super(MaterialsStorageModel, self).__init__(*args, **kwargs)
        self.materials = OrderedDict()  # type: OrderedDict[str, entities.Material]

    def add_material(self, material: entities.Material):
        """Add material to model"""
        self.beginResetModel()
        if material.name in self.materials:
            self.materials[material.name] += material
            self.materials.move_to_end(material.name, last=True)
        else:
            self.materials[material.name] = material
        self.endResetModel()

    def modelReset(self):
        """Remove all materials from model"""
        self.beginResetModel()
        self.materials.clear()
        self.endResetModel()

    @utils.catcherr
    def data(self, index: QtCore.QModelIndex, role=None):
        """Return model data by index"""
        if not index.isValid():
            return None
        if index.row() > len(self.materials) or index.row() < 0:
            return None
        material = self.materials[list(reversed(list(self.materials.keys())))[index.row()]]
        if role == QtCore.Qt.DisplayRole:
            if index.column() == 0:
                return material.name
            if index.column() == 1:
                return material.count

        return None

    # pylint: disable=unused-argument
    def rowCount(self, *args, **kwargs):
        """Return row count. Capped by maximum_length"""
        count = len(self.materials)
        return count if count <= self.maximum_length else self.maximum_length

    # pylint: disable=unused-argument,no-self-use
    def columnCount(self, *args, **kwargs):
        """Return column count"""
        return 2

    # pylint: disable=no-self-use
    def headerData(self, section, orientation, role=None):
        """Return headers names"""
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            if section == 0:
                return 'Material'
            if section == 1:
                return 'Count'

        return None


class MaterialsCollectedComponent(BaseMainWindowSection):
    """Materials collected component"""
    name = 'Materials Collected'

    def __init__(self):
        super(MaterialsCollectedComponent, self).__init__()
        self.setLayout(QtWidgets.QVBoxLayout())

        self.storage_model = MaterialsStorageModel(self)

        button = QtWidgets.QPushButton('clear')
        button.setMaximumHeight(20)
        button.clicked.connect(self.storage_model.modelReset)
        self.layout().addWidget(button)

        self.table_view = QtWidgets.QTableView(self)
        self.table_view.setModel(self.storage_model)
        self.table_view.setTextElideMode(QtCore.Qt.ElideRight)
        header: QtWidgets.QHeaderView = self.table_view.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.table_view.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        # self.table_view.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.table_view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.table_view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.table_view.setAutoScroll(False)
        self.table_view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table_view.setProperty("showDropIndicator", False)
        self.table_view.setDefaultDropAction(QtCore.Qt.IgnoreAction)
        self.table_view.setMinimumHeight(100)

        self.layout().addWidget(self.table_view)

    def on_journal_event(self, event: journal.Event):
        """On MaterialCollected add material to model"""
        if event.name != 'MaterialCollected':
            return

        category = event.data['Category']  # type: ignore
        name = event.data['Name']  # type: ignore
        count = event.data['Count']  # type: ignore

        self.storage_model.add_material(entities.Material(name, count, category))
        self.table_view.update()
