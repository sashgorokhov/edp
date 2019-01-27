from pathlib import Path
from typing import Optional, Any, Callable, Union, Type, Iterator

from PyQt5 import QtWidgets, QtCore, QtGui

from edp.plugins import PluginManager
from edp.settings import EDPSettings


class BaseTab(QtWidgets.QWidget):
    friendly_name: Optional[str] = None

    def get_friendly_name(self):
        return self.friendly_name or self.__class__.__name__

    def link_checkbox(self, settings, field, label=None) -> QtWidgets.QHBoxLayout:
        label = label or field
        layout = QtWidgets.QHBoxLayout()
        checkbox = QtWidgets.QCheckBox()
        checkbox.setText(label)
        checkbox.stateChanged.connect(lambda state: settings.__setattr__(field, QtCore.Qt.Checked == state))
        checkbox.setChecked(getattr(settings, field))
        layout.addWidget(checkbox)
        layout.addStretch(1)
        return layout

    def link_line_edit(self, settings, field, label=None,
                       settype: Union[Callable[[str], Any], Type] = str) -> QtWidgets.QHBoxLayout:
        label = label or field
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel(label))
        line_edit = QtWidgets.QLineEdit(str(getattr(settings, field) or ''))
        line_edit.textChanged.connect(lambda text: settings.__setattr__(field, settype(text)))
        line_edit.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        layout.addWidget(line_edit)
        layout.addSpacerItem(
            QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum))
        return layout

    def link_directory_dialog(self, settings, field, label_text=None) -> QtWidgets.QHBoxLayout:
        label_text = label_text or field
        layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel(label_text)
        # label.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed))
        layout.addWidget(label)
        line_edit = QtWidgets.QLineEdit(str(getattr(settings, field) or ''))
        line_edit.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        line_edit.setReadOnly(True)
        layout.addWidget(line_edit)
        button = QtWidgets.QPushButton('Change')

        def on_button_clicked():
            value = QtWidgets.QFileDialog.getExistingDirectory(self, "Select %s" % label)
            if not value:
                return
            line_edit.setText(value)
            setattr(settings, field, Path(value))

        button.clicked.connect(on_button_clicked)
        layout.addWidget(button)
        layout.addSpacerItem(
            QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum))
        return layout

    def get_settings_links(self) -> Iterator[QtWidgets.QLayout]:
        yield from []


class VLayoutTab(BaseTab):
    def __init__(self):
        super(VLayoutTab, self).__init__()
        layout = QtWidgets.QVBoxLayout()

        for l in self.get_settings_links():
            layout.addLayout(l)

        layout.addStretch(1)

        self.setLayout(layout)


class TabGeneral(VLayoutTab):
    friendly_name = 'General'

    def get_settings_links(self):
        settings = EDPSettings.get_insance()

        yield self.link_directory_dialog(settings, 'plugin_dir', 'Plugin directory')
        yield self.link_directory_dialog(settings, 'journal_dir', 'Journal directory')

        layout = QtWidgets.QVBoxLayout()
        checkbox = QtWidgets.QCheckBox('Enable automatic error reports')
        checkbox.setChecked(settings.enable_error_reports)
        checkbox.stateChanged.connect(
            lambda state: settings.__setattr__('enable_error_reports', QtCore.Qt.Checked == state))
        layout.addWidget(checkbox)
        label = QtWidgets.QLabel('App restart required')
        font: QtGui.QFont = label.font()
        font.setPointSize(7)
        label.setFont(font)
        layout.addWidget(label)
        yield layout


class SettingsWindow(QtWidgets.QTabWidget):
    def __init__(self, plugin_manager: PluginManager):
        super(SettingsWindow, self).__init__()
        self.setWindowTitle('EDP - Settings')

        self.add_tab_widget(TabGeneral())

        self.setMinimumSize(QtCore.QSize(400, 300))
        self.setMaximumSize(QtCore.QSize(800, 16777215))

        for tab_widget in plugin_manager.get_settings_widgets():
            self.add_tab_widget(tab_widget)

    def add_tab_widget(self, tab_widget: QtWidgets.QWidget):
        tab_widget.setParent(self)
        self.addTab(tab_widget, tab_widget.get_friendly_name())
