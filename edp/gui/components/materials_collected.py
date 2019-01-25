import logging
from collections import OrderedDict

from PyQt5 import QtWidgets, QtCore

from edp import journal, entities, utils
from edp.gui.components.base import BaseMainWindowSection

logger = logging.getLogger(__name__)


class MaterialsStorageModel(QtCore.QAbstractTableModel):
    maximum_length = 10

    def __init__(self, *args, **kwargs):
        super(MaterialsStorageModel, self).__init__(*args, **kwargs)
        self.materials: OrderedDict[str, entities.Material] = OrderedDict()

    def add_material(self, material: entities.Material):
        self.beginResetModel()
        if material.name in self.materials:
            self.materials[material.name] += material
            self.materials.move_to_end(material.name, last=True)
        else:
            self.materials[material.name] = material
        self.endResetModel()

    def modelReset(self):
        self.beginResetModel()
        self.materials.clear()
        self.endResetModel()

    @utils.catcherr
    def data(self, index: QtCore.QModelIndex, role=None):
        if not index.isValid():
            return
        if index.row() > len(self.materials) or index.row() < 0:
            return
        material = self.materials[list(reversed(list(self.materials.keys())))[index.row()]]
        if role == QtCore.Qt.DisplayRole:
            if index.column() == 0:
                return material.name
            elif index.column() == 1:
                return material.count

    def rowCount(self, parent=None, *args, **kwargs):
        count = len(self.materials)
        return count if count <= self.maximum_length else self.maximum_length

    def columnCount(self, parent=None, *args, **kwargs):
        return 2

    def headerData(self, section, orientation, role=None):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            if section == 0:
                return 'Material'
            elif section == 1:
                return 'Count'


class MaterialsCollectedComponent(BaseMainWindowSection):
    name = 'Materials Collected'

    def __init__(self):
        super(MaterialsCollectedComponent, self).__init__()
        self.setLayout(QtWidgets.QVBoxLayout())

        self.storage_model = MaterialsStorageModel(self)

        button = QtWidgets.QPushButton('clear')
        button.setMaximumHeight(20)
        button.clicked.connect(lambda: self.storage_model.modelReset())
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
        if event.name != 'MaterialCollected':
            return

        category: str = event.data['Category']  # type: ignore
        name: str = event.data['Name']  # type: ignore
        count: int = event.data['Count']  # type: ignore

        self.storage_model.add_material(entities.Material(name, count, category))
        self.table_view.update()
