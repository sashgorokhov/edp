import inject
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot

from edp.contrib import gamestate
from edp.gui.components.base import BaseMainWindowSection
from edp.plugins import PluginProxy


class StateOverviewComponent(BaseMainWindowSection):
    name = 'State Overview'

    set_game_state_signal = pyqtSignal(gamestate.GameStateData)

    plugin_proxy: PluginProxy = inject.attr(PluginProxy)

    def __init__(self):
        super(StateOverviewComponent, self).__init__()
        self.setLayout(QtWidgets.QVBoxLayout())

        self.commander_label = QtWidgets.QLabel('Unkown')
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel('Commander'))
        layout.addItem(QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))
        layout.addWidget(self.commander_label)
        self.layout().addLayout(layout)

        self.ship_label = QtWidgets.QLabel('Unkown')
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel('Ship'))
        layout.addItem(QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))
        layout.addWidget(self.ship_label)
        self.layout().addLayout(layout)

        self.system_label = QtWidgets.QLabel('Unkown')
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel('System'))
        layout.addItem(QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))
        layout.addWidget(self.system_label)
        self.layout().addLayout(layout)

        self.set_game_state_signal.connect(self.on_set_game_state_signal)

        signal_wrapper = lambda state: self.set_game_state_signal.emit(state)
        gamestate.game_state_set_signal.bind_nonstrict(signal_wrapper)
        gamestate.game_state_changed_signal.bind_nonstrict(signal_wrapper)

        gamestate_plugin = self.plugin_proxy.get_plugin(gamestate.GameState)

        self.set_game_state_signal.emit(gamestate_plugin.state)

    @pyqtSlot(gamestate.GameStateData)
    def on_set_game_state_signal(self, state: gamestate.GameStateData):
        self.commander_label.setText(state.commander.name)
        self.ship_label.setText(state.ship.name or state.ship.model or state.ship.ident or 'Unknown')
        self.system_label.setText(state.location.system)
