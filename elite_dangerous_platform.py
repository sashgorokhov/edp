import logging
import tkinter as tk
import inject

from edp.gui import MainWindow
from edp.plugin import PluginManager, SignalExecutorThread
from edp.thread import ThreadManager
from edp.journal import JournalEventProcessor, Journal
from edp import signals
from edp.settings import Settings
from edp.contrib import edsm


logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger('edp')


logger.info('Initializing settings')
settings = Settings()


logger.info('Initializing plugins')
plugin_manager = PluginManager(settings.plugin_dir)


logger.info('Initializing thread manager')
thread_manager = ThreadManager()


def injection_config(binder: inject.Binder):
    binder.bind(Settings, settings)
    binder.bind(PluginManager, plugin_manager)
    binder.bind(ThreadManager, thread_manager)


inject.clear_and_configure(injection_config)

logger.info('Initializing flightlog journal handler')
journal = Journal(settings.journal_dir)

logger.info('Loading plugins')
plugin_manager.load_plugins()

plugin_manager.register_plugin_cls(edsm.EDSMPlugin)

thread_manager.add_threads(
    journal,
    JournalEventProcessor(journal, plugin_manager),
    SignalExecutorThread(plugin_manager._signal_queue),
    *plugin_manager._scheduler_threads,
)

with thread_manager:
    logger.info('Initializing gui')
    root = tk.Tk()
    window = MainWindow(root, plugin_manager)
    plugin_manager.emit(signals.WINDOW_CREATED, window=window)
    plugin_manager.emit(signals.INIT_COMPLETE)
    root.mainloop()
