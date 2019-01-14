import inject
from PyQt5 import QtCore, QtWidgets

from edp import journal, plugins
from edp.gui.components.base import BaseMainWindowSection


class SimpleEventsListComponent(BaseMainWindowSection):
    name = 'Simple Events List'

    journal_event_signal = QtCore.pyqtSignal(journal.Event)

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

        self.journal_event_signal.connect(self.on_journal_event_signal)
        journal.journal_event_signal.bind_nonstrict(lambda event: self.journal_event_signal.emit(event))

    @QtCore.pyqtSlot(journal.Event)
    def on_journal_event_signal(self, event: journal.Event):
        self.list_widget.insertItem(0, event.name)
        count = self.list_widget.count()
        if count > 10:
            diff = count - 10
            for i in range(1, diff + 1):
                self.list_widget.takeItem(count - i)
