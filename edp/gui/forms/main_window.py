import collections
import logging
from functools import partial
from typing import Dict, Type, List

from PyQt5.QtWidgets import QMainWindow, QAction, QLayout, QFrame, QBoxLayout

from edp.gui.compiled.main_window import Ui_MainWindow
from edp.gui.components import state_overview, simple_events_list
from edp.gui.components.base import BaseMainWindowSection
from edp.plugins import PluginManager
from edp.signalslib import Signal

logger = logging.getLogger(__name__)


class SECTIONS:
    MAIN = 'main'
    PLUGINS = 'plugins'

    order = (MAIN, PLUGINS)


class MainWindowSectionsView(Ui_MainWindow):
    def init_ui(self):
        self.menuView.clear()

        self._section_components: Dict[str, List[BaseMainWindowSection]] = collections.defaultdict(list)
        self._section_separators: Dict[str, QAction] = {}

        for section in SECTIONS.order:
            self._section_separators[section] = self.menuView.addSeparator()

    def add_component(self, component_cls: Type[BaseMainWindowSection], section=SECTIONS.MAIN):
        if component_cls.name is None:
            logger.warning(f'Section component {component_cls} does not define `name` attribute')

        component = component_cls()
        component.name = component.name or component_cls.__name__

        action = QAction(self)
        action.setCheckable(True)
        action.setChecked(True)
        action.setText(component.name)
        action.toggled.connect(partial(self.on_section_action_toggled, action=action, component=component))

        self.menuView.insertAction(self._section_separators[section], action)

        self._section_components[section].append(component)

        if action.isChecked():
            self.add_component_on_layout(component)

    def add_component_on_layout(self, component: BaseMainWindowSection):
        layout: QLayout = self.centralwidget.layout()
        if layout.count() > 0:
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setFrameShadow(QFrame.Sunken)
            layout.addWidget(line)
        layout.addWidget(component)
        component.setVisible(True)
        # TODO: add spacer after

    def remove_component_on_layout(self, component: BaseMainWindowSection):
        layout: QBoxLayout = self.centralwidget.layout()
        i = layout.indexOf(component)
        if i > 0:
            item = layout.itemAt(i - 1)
            widget = item.widget()
            layout.removeWidget(widget)
            widget.deleteLater()
        layout.removeWidget(component)
        component.setVisible(False)

    def on_section_action_toggled(self, toggled: bool, action: QAction, component: BaseMainWindowSection):
        try:
            if toggled:
                self.add_component_on_layout(component)
            else:
                self.remove_component_on_layout(component)
        except:
            logger.exception(f'on_section_action_toggled({toggled}, {action}, {component})')


class MainWindow(MainWindowSectionsView, Ui_MainWindow, QMainWindow):
    def __init__(self, plugin_manager: PluginManager):
        super(MainWindow, self).__init__()
        self.setupUi(self)

        self._plugin_manager = plugin_manager

        self.init_ui()

        self.add_component(state_overview.StateOverviewComponent)
        self.add_component(simple_events_list.SimpleEventsListComponent)


main_window_created_signal = Signal('main window created', window=MainWindow)
