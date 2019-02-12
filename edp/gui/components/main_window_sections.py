"""Component for managing widget sections on main window surface"""
import collections
import logging
from functools import partial
from typing import Dict, List, Type

from PyQt5 import QtWidgets

from edp.gui.components.base import BaseMainWindowSection
from edp.settings import SimpleSettings

logger = logging.getLogger(__name__)


class SECTIONS:
    """Sections names"""
    MAIN = 'main'
    PLUGINS = 'plugins'

    order = (MAIN, PLUGINS)


class MainWindowSectionsView:
    """Manager of sections"""
    def __init__(self, window):
        self._settings = SimpleSettings.get_insance('main_window_sections')

        self.window = window
        self.layout: QtWidgets.QVBoxLayout = self.window.centralwidget.layout()
        self._section_components: Dict[str, List[BaseMainWindowSection]] = collections.defaultdict(list)
        self._section_separators: Dict[str, QtWidgets.QAction] = {}

        self.layout.addStretch(1)

        for section in SECTIONS.order:
            self._section_separators[section] = self.window.menuView.addSeparator()

    def add_component(self, component_cls: Type[BaseMainWindowSection], section=SECTIONS.MAIN):
        """Add section component to section"""
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
        """Create horizontal line on layout"""
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.layout.addWidget(line)

    def add_component_on_layout(self, component: BaseMainWindowSection):
        """Add section component on layout"""
        # remove stretch
        self.layout.removeItem(self.layout.itemAt(self.layout.count() - 1))
        if self.layout.count() > 0:
            self.add_horizontal_line()
        self.layout.addWidget(component)
        component.setVisible(True)
        self.layout.addStretch(1)

    def remove_horizontal_line(self, i):
        """Remove horizontal line from layout"""
        item = self.layout.itemAt(i)
        widget = item.widget()
        if widget:
            self.layout.removeWidget(widget)
            widget.deleteLater()

    def remove_component_on_layout(self, component: BaseMainWindowSection):
        """Remove specific component from layout"""
        i = self.layout.indexOf(component)
        if i == 0:
            self.remove_horizontal_line(i + 1)
        if i > 0:
            self.remove_horizontal_line(i - 1)
        self.layout.removeWidget(component)
        component.setVisible(False)

    def on_section_action_toggled(self, toggled: bool, action: QtWidgets.QAction, component: BaseMainWindowSection):
        """Show or hide specific section component"""
        try:
            if toggled:
                self.add_component_on_layout(component)
            else:
                self.remove_component_on_layout(component)
            self._settings[component.name] = toggled
        except:
            logger.exception(f'on_section_action_toggled({toggled}, {action}, {component})')
