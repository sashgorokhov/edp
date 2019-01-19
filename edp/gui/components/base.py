import logging
from typing import Optional

from PyQt5 import QtWidgets, QtCore

from edp import journal

logger = logging.getLogger(__name__)


class BaseMainWindowSection(QtWidgets.QWidget):
    name: Optional[str] = None

    journal_event_signal = QtCore.pyqtSignal(journal.Event)

    def __init__(self):
        super(BaseMainWindowSection, self).__init__()
        self.journal_event_signal.connect(self.on_journal_event_signal)
        journal.journal_event_signal.bind_nonstrict(lambda event: self.journal_event_signal.emit(event))

    @QtCore.pyqtSlot(journal.Event)
    def on_journal_event_signal(self, event: journal.Event):
        try:
            self.on_journal_event(event)
        except:
            logger.exception('Error calling on_journal_event')

    def on_journal_event(self, event: journal.Event):
        pass
