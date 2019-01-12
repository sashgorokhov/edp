import logging
import os

import inject

from edp import signals
from edp.contrib import edsm, gamestate, _debug
from edp.journal import JournalReader, JournalLiveEventThread
from edp.plugin import PluginManager, SignalExecutorThread
from edp.settings import Settings
from edp.thread import ThreadManager

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger('edp')

logger.info('Initializing settings')
settings = Settings()

logger.info('Initializing plugins')
plugin_manager = PluginManager(settings.plugin_dir)

logger.info('Initializing thread manager')
thread_manager = ThreadManager()

logger.info('Initializing flightlog journal handler')
journal_reader = JournalReader(settings.journal_dir)


def injection_config(binder: inject.Binder):
    binder.bind(Settings, settings)
    binder.bind(PluginManager, plugin_manager)
    binder.bind(ThreadManager, thread_manager)
    binder.bind(JournalReader, journal_reader)


inject.clear_and_configure(injection_config)

logger.info('Loading plugins')
plugin_manager.register_plugin_cls(edsm.EDSMPlugin)
plugin_manager.register_plugin_cls(gamestate.GameState)
plugin_manager.register_plugin_cls(_debug._DebugPlugin)

plugin_manager.load_plugins()

thread_manager.add_threads(
    JournalLiveEventThread(journal_reader, plugin_manager),
    SignalExecutorThread(plugin_manager._signal_queue),
    *plugin_manager._scheduler_threads,
)

plugin_manager.emit(signals.INIT_COMPLETE)

with thread_manager:
    logger.info('Initializing gui')

    try:
        from edp.gui.components.main_window import MainWindow
        from PyQt5.QtWidgets import QApplication

        app = QApplication([])

        window = MainWindow()
        plugin_manager.emit(signals.WINDOW_CREATED, window=window)

        window.show()
        app.exec_()
    except ImportError:
        logger.exception('Failed to initialize gui, exiting')
