import logging
import tkinter as tk

from edp.gui import MainWindow
from edp.plugin import PluginManager
from edp.journal import JournalEventProcessor, Journal
from edp import config, signals


logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger('edp')


logger.info('Initializing config')
config.init()


logger.info('Initializing plugins')
plugin_manager = PluginManager(config.PLUGIN_DIR)


logger.info('Initializing flightlog journal handler')
journal = Journal(config.JOURNAL_DIR)


with JournalEventProcessor(journal, plugin_manager):
    logger.info('Initializing gui')
    root = tk.Tk()
    window = MainWindow(root, plugin_manager)
    plugin_manager.emit(signals.WINDOW_CREATED, window=window)
    root.mainloop()
