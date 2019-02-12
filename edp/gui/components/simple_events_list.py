"""Section with list of journal events read by application"""
import logging

import inject
from PyQt5 import QtCore, QtWidgets

from edp import journal, plugins
from edp.gui.components.base import BaseMainWindowSection

logger = logging.getLogger(__name__)


class SimpleEventsListComponent(BaseMainWindowSection):
    """Events list component"""
    name = 'Simple Events List'

    plugin_proxy: plugins.PluginProxy = inject.attr(plugins.PluginProxy)

    def __init__(self):
        super(SimpleEventsListComponent, self).__init__()
        self.setLayout(QtWidgets.QVBoxLayout())
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setMinimumSize(QtCore.QSize(0, 100))
        self.list_widget.setMaximumSize(QtCore.QSize(16777215, 150))
        self.list_widget.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.list_widget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.list_widget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.list_widget.setAutoScroll(False)
        self.list_widget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.list_widget.setProperty("showDropIndicator", False)
        self.list_widget.setDefaultDropAction(QtCore.Qt.IgnoreAction)
        self.list_widget.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.layout().addWidget(self.list_widget)

    def on_journal_event(self, event: journal.Event):
        """Add journal event name to list widget"""
        self.list_widget.insertItem(0, event.name)
        count = self.list_widget.count()
        if count > 10:
            diff = count - 10
            for i in range(1, diff + 1):
                self.list_widget.takeItem(count - i)
