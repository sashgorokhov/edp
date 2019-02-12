"""
Main application window form

Signals:
- main_window_created_signal: sent when main window is created
"""
import logging

from PyQt5 import QtWidgets, QtCore

from edp.gui.compiled.main_window import Ui_MainWindow
from edp.gui.components import state_overview, simple_events_list, materials_collected, main_window_sections
from edp.gui.forms.settings_window import SettingsWindow
from edp.plugins import PluginManager
from edp.signalslib import Signal

logger = logging.getLogger(__name__)


class MainWindow(Ui_MainWindow, QtWidgets.QMainWindow):
    """Application main window"""
    on_showed = QtCore.pyqtSignal()

    def __init__(self, plugin_manager: PluginManager):
        super(MainWindow, self).__init__()
        self.setupUi(self)

        self._app = QtWidgets.QApplication.instance()

        self.sections_view = main_window_sections.MainWindowSectionsView(self)
        self.sections_view.add_component(state_overview.StateOverviewComponent)
        self.sections_view.add_component(simple_events_list.SimpleEventsListComponent)
        self.sections_view.add_component(materials_collected.MaterialsCollectedComponent)

        self.settings_window = SettingsWindow(plugin_manager)

        action = QtWidgets.QAction(self)
        action.setText('Settings')
        action.triggered.connect(self.settings_window.show)
        self.menubar.addAction(action)

        self._app.aboutToQuit.connect(self.close)

        layout: QtWidgets.QVBoxLayout = self.layout()
        layout.setContentsMargins(0, 0, 0, 0)

    def show(self):
        """Show window and emit on_showed signal"""
        self.on_showed.emit()
        super(MainWindow, self).show()

    # pylint: disable=unused-argument
    def closeEvent(self, *args, **kwargs):
        """Terminate application if main window closed"""
        self._app.quit()


main_window_created_signal = Signal('main window created', window=MainWindow)
