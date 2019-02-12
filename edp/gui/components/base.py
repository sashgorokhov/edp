"""
Base things for GUI components
"""
import logging
from typing import Optional

from PyQt5 import QtWidgets, QtCore

from edp import journal

logger = logging.getLogger(__name__)


class JournalEventHandlerMixin:
    """
    Special mixin that simplifies subscribing to journal event signal.

    This connects edp signal and qt signal.

    To process journal event you want to override `on_journal_event` method.
    """
    journal_event_signal = QtCore.pyqtSignal(journal.Event)

    def __init__(self):
        super(JournalEventHandlerMixin, self).__init__()

        self.journal_event_signal.connect(self.on_journal_event_signal)
        # pylint: disable=unnecessary-lambda
        journal.journal_event_signal.bind_nonstrict(lambda event: self.journal_event_signal.emit(event))

    @QtCore.pyqtSlot(journal.Event)
    def on_journal_event_signal(self, event: journal.Event):
        """Handle journal event signal and call journal event overriden method"""
        try:
            self.on_journal_event(event)
        except:
            logger.exception('Error calling on_journal_event')

    def on_journal_event(self, event: journal.Event):
        """Process journal event"""


class BaseMainWindowSection(JournalEventHandlerMixin, QtWidgets.QWidget):
    """Base class for main window sections"""
    name: Optional[str] = None
