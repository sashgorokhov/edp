import inject
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QVBoxLayout, QListWidget

from edp import journal
from edp.gui.components.base import BaseMainWindowSection
from edp.plugins import PluginProxy


class SimpleEventsListComponent(BaseMainWindowSection):
    name = 'Simple Events List'

    journal_event_signal = pyqtSignal(journal.Event)

    plugin_proxy: PluginProxy = inject.attr(PluginProxy)

    def __init__(self):
        super(SimpleEventsListComponent, self).__init__()
        self.setLayout(QVBoxLayout())
        self._list_widget = QListWidget()
        self._list_widget.setMinimumSize(QtCore.QSize(0, 100))
        self._list_widget.setMaximumSize(QtCore.QSize(16777215, 150))
        self._list_widget.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self._list_widget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self._list_widget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self._list_widget.setAutoScroll(False)
        self._list_widget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._list_widget.setProperty("showDropIndicator", False)
        self._list_widget.setDefaultDropAction(QtCore.Qt.IgnoreAction)
        self._list_widget.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.layout().addWidget(self._list_widget)

        self.journal_event_signal.connect(self.on_journal_event_signal)
        journal.journal_event_signal.bind_nonstrict(lambda event: self.journal_event_signal.emit(event))

    @pyqtSlot(journal.Event)
    def on_journal_event_signal(self, event: journal.Event):
        self._list_widget.insertItem(0, event.name)
        count = self._list_widget.count()
        if count > 10:
            diff = count - 10
            for i in range(1, diff + 1):
                self._list_widget.takeItem(count - i)
