from edp import journal
from edp.contrib import edsm
from edp.gui.compiled.edsm_unknown_systems import Ui_Form
from edp.gui.components.base import JournalEventHandlerMixin
from edp.gui.components.overlay_widgets.base import BaseOverlayWidget
from edp.gui.components.overlay_widgets.manager import register


@register
class UnknownSystemsWidget(Ui_Form, JournalEventHandlerMixin, BaseOverlayWidget):
    friendly_name = 'EDSM unknown systems'

    def __init__(self):
        super(UnknownSystemsWidget, self).__init__()
        self.setupUi(self)

        self.edsm_api = edsm.EDSMApi()

    def on_journal_event(self, event: journal.Event):
        if not self.enabled_checkbox.isChecked():
            return

        if event.name == 'FSDTarget':
            self.system_label.setText(event.data['Name'])

            if self.edsm_api.get_system(event.data['Name']):
                self.status_label.setText('Found')
                self.status_label.setProperty('status', True)
            else:
                self.status_label.setText('Not found')
                self.status_label.setProperty('status', False)
            return
