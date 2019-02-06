import logging
from typing import Iterator

import inject
from PyQt5 import QtWidgets

from edp.contrib import edsm, gamestate, eddb
from edp.gui.compiled.find_nearest_station import Ui_Form
from edp.gui.components.overlay_widgets.base import BaseOverlayWidget
from edp.gui.components.overlay_widgets.manager import register
from edp.utils import catcherr

logger = logging.getLogger(__name__)


@register
class FindNearestWidget(Ui_Form, BaseOverlayWidget):
    friendly_name = 'Find nearest station'

    edsm_plugin: edsm.EDSMPlugin = inject.attr(edsm.EDSMPlugin)

    def __init__(self):
        super(FindNearestWidget, self).__init__()
        self.setupUi(self)
        self.search_button.setEnabled(False)
        self.facilities_combobox.currentTextChanged.connect(lambda text: self.search_button.setEnabled(text != '---'))
        self.search_button.clicked.connect(lambda *args, **kwargs: self.search_button_clicked())
        self.hide_result_labels()

        self.eddb_api = eddb.EDDBApi()

    def result_labels(self) -> Iterator[QtWidgets.QLabel]:
        for i in range(self.result_layout.count()):
            item: QtWidgets.QLayoutItem = self.result_layout.itemAt(i)
            label: QtWidgets.QLabel = item.widget()
            yield label

    def hide_result_labels(self):
        for label in self.result_labels():
            label.hide()

    def show_result_labels(self):
        for label in self.result_labels():
            label.show()

    @catcherr
    def search_button_clicked(self):
        self.hide_result_labels()

        facility = self.facilities_combobox.currentText()
        state = gamestate.get_gamestate()
        data = self.edsm_plugin.api.get_system(state.location.system)
        system_id = data.get('id', None)

        if not system_id:
            logger.warning(f'System id not found for system {state.location.system}: {data}')
            return

        data_list = self.eddb_api.search_station(facility, ref_system_id=system_id)

        for label, data in zip(self.result_labels(), data_list):
            label.setText(f'{data[1]} | {data[0]}')

        self.show_result_labels()
