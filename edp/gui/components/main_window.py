from PyQt5 import QtCore
from PyQt5.QtWidgets import QMainWindow

from edp.contrib import gamestate
from edp.gui.compiled.main_window import Ui_MainWindow
import inject
from edp import signals

from edp.journal import Event
from edp.plugin import PluginManager


class MainWindow(Ui_MainWindow, QMainWindow):
    plugin_manager: PluginManager = inject.instance(PluginManager)
    gamestate_plugin: gamestate.GameState = plugin_manager.get_plugin(gamestate.GameState)

    journal_event_signal = QtCore.pyqtSignal(Event)
    game_state_set_signal = QtCore.pyqtSignal(gamestate.GameStateData)

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)

        self.journal_event_signal.connect(self.on_journal_event)
        self.game_state_set_signal.connect(self.on_game_state_set)

        self.plugin_manager.register_callback_func(
            lambda event: self.journal_event_signal.emit(event),
            signals.JOURNAL_EVENT
        )
        self.plugin_manager.register_callback_func(
            lambda state: self.game_state_set_signal.emit(state),
            gamestate.SIGNALS.GAME_STATE_SET
        )

        self.game_state_set_signal.emit(self.gamestate_plugin.state)

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
