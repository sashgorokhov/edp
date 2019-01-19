import collections
import logging
from functools import partial
from typing import Dict, Type, List

from PyQt5 import QtWidgets

from edp.gui.compiled.main_window import Ui_MainWindow
from edp.gui.components import state_overview, simple_events_list, materials_collected
from edp.gui.components.base import BaseMainWindowSection
from edp.gui.forms.settings_window import SettingsWindow
from edp.plugins import PluginManager
from edp.settings import SimpleSettings
from edp.signalslib import Signal

logger = logging.getLogger(__name__)


class SECTIONS:
    MAIN = 'main'
    PLUGINS = 'plugins'

    order = (MAIN, PLUGINS)


class MainWindowSectionsView:
    def __init__(self, window: 'MainWindow'):
        self._settings = SimpleSettings.get_insance('main_window_sections')

        self.window = window
        self.layout: QtWidgets.QVBoxLayout = self.window.centralwidget.layout()
        self._section_components: Dict[str, List[BaseMainWindowSection]] = collections.defaultdict(list)
        self._section_separators: Dict[str, QtWidgets.QAction] = {}

        self.layout.addStretch(1)

        for section in SECTIONS.order:
            self._section_separators[section] = self.window.menuView.addSeparator()

    def add_component(self, component_cls: Type[BaseMainWindowSection], section=SECTIONS.MAIN):
        if component_cls.name is None:
            logger.warning(f'Section component {component_cls} does not define `name` attribute')

        try:
            component = component_cls()
        except:
            logger.exception(f'Failed to configure component: {component_cls}')
            return

        component.name = component.name or component_cls.__name__
        self._settings.setdefault(component.name, True)

        action = QtWidgets.QAction(self.window)
        action.setCheckable(True)
        action.setChecked(self._settings[component.name])
        action.setText(component.name)
        action.toggled.connect(partial(self.on_section_action_toggled, action=action, component=component))

        self.window.menuView.insertAction(self._section_separators[section], action)

        self._section_components[section].append(component)

        if action.isChecked():
            self.add_component_on_layout(component)

    def add_horizontal_line(self):
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.layout.addWidget(line)

    def add_component_on_layout(self, component: BaseMainWindowSection):
        # remove stretch
        self.layout.removeItem(self.layout.itemAt(self.layout.count() - 1))
        if self.layout.count() > 0:
            self.add_horizontal_line()
        self.layout.addWidget(component)
        component.setVisible(True)
        self.layout.addStretch(1)

    def remove_horizontal_line(self, i):
        item = self.layout.itemAt(i)
        widget = item.widget()
        if widget:
            self.layout.removeWidget(widget)
            widget.deleteLater()

    def remove_component_on_layout(self, component: BaseMainWindowSection):
        i = self.layout.indexOf(component)
        if i == 0:
            self.remove_horizontal_line(i + 1)
        if i > 0:
            self.remove_horizontal_line(i - 1)
        self.layout.removeWidget(component)
        component.setVisible(False)

    def on_section_action_toggled(self, toggled: bool, action: QtWidgets.QAction, component: BaseMainWindowSection):
        try:
            if toggled:
                self.add_component_on_layout(component)
            else:
                self.remove_component_on_layout(component)
            self._settings[component.name] = toggled
        except:
            logger.exception(f'on_section_action_toggled({toggled}, {action}, {component})')


class MainWindow(Ui_MainWindow, QtWidgets.QMainWindow):
    def __init__(self, plugin_manager: PluginManager):
        super(MainWindow, self).__init__()
        self.setupUi(self)

        self._app = QtWidgets.QApplication.instance()

        self.sections_view = MainWindowSectionsView(self)
        self.sections_view.add_component(state_overview.StateOverviewComponent)
        self.sections_view.add_component(simple_events_list.SimpleEventsListComponent)
        self.sections_view.add_component(materials_collected.MaterialsCollectedComponent)

        self.settings_window = SettingsWindow(plugin_manager)

        action = QtWidgets.QAction(self)
        action.setText('Settings')
        action.triggered.connect(self.settings_window.show)
        self.menubar.addAction(action)

        self._app.aboutToQuit.connect(self.close)
        self._app.aboutToQuit.connect(self.settings_window.close)

        layout: QtWidgets.QVBoxLayout = self.layout()
        layout.setContentsMargins(0, 0, 0, 0)

    def closeEvent(self, *args, **kwargs):
        self._app.quit()


main_window_created_signal = Signal('main window created', window=MainWindow)
