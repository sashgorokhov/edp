from PyQt5 import QtCore
from PyQt5.QtWidgets import QMainWindow

from edp.contrib import gamestate
from edp.gui.compiled.main_window import Ui_MainWindow
from edp.journal import Event
from edp.plugins import PluginManager
from edp.signalslib import Signal
from edp import journal


class MainWindow(Ui_MainWindow, QMainWindow):
    journal_event_signal = QtCore.pyqtSignal(Event)
    game_state_set_signal = QtCore.pyqtSignal(gamestate.GameStateData)

    def __init__(self, plugin_manager: PluginManager):
        super(MainWindow, self).__init__()
        self.setupUi(self)

        self._plugin_manager = plugin_manager
        self._gamestate_plugin = plugin_manager.get_plugin(gamestate.GameState)

        self.journal_event_signal.connect(self.on_journal_event)
        self.game_state_set_signal.connect(self.on_game_state_set)

        journal.journal_event_signal.bin_nonstrict(lambda event:  self.journal_event_signal.emit(event))
        gamestate.game_state_set_signal.bin_nonstrict(lambda state: self.game_state_set_signal.emit(state))

        self.game_state_set_signal.emit(self._gamestate_plugin.state)

    # noinspection PyArgumentList
    @QtCore.pyqtSlot(Event)
    def on_journal_event(self, event: Event):
        self.list_widget_events.insertItem(0, event.name)
        count = self.list_widget_events.count()
        if count > 10:
            diff = count - 10
            for i in range(1, diff + 1):
                self.list_widget_events.takeItem(count - i)

    # noinspection PyArgumentList
    @QtCore.pyqtSlot(gamestate.GameStateData)
    def on_game_state_set(self, state: gamestate.GameStateData):
        self.label_commander.setText(state.commander.name)
        self.label_ship.setText(state.ship.name or state.ship.model or state.ship.ident or 'Unknown')
        self.label_system.setText(state.location.system)


main_window_created_signal = Signal('main window created', window=MainWindow)
