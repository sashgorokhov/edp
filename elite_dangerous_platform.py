import logging
import time
import traceback

import inject

from edp import signalslib, plugins, thread, signals, journal, config
from edp.contrib import edsm, gamestate, eddn
from edp.settings import EDPSettings

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger('edp')

logger.info('Initializing settings')
settings = EDPSettings.get_insance()

logger.info('Initializing thread manager')
thread_manager = thread.ThreadManager()

logger.info('Initializing flightlog journal handler')
journal_reader = journal.JournalReader(settings.journal_dir)

logger.info('Loading plugins')
plugin_loader = plugins.PluginLoader(settings.plugin_dir)

plugin_loader.add_plugin(edsm.EDSMPlugin)
plugin_loader.add_plugin(gamestate.GameState)
plugin_loader.add_plugin(eddn.EDDNPlugin)
plugin_loader.load_plugins()

plugin_manager = plugins.PluginManager(plugin_loader.get_plugins())
plugin_proxy = plugins.PluginProxy(plugin_manager)


def injection_config(binder: inject.Binder):
    binder.bind(plugins.PluginProxy, plugin_proxy)
    binder.bind(thread.ThreadManager, thread_manager)
    binder.bind(journal.JournalReader, journal_reader)


inject.clear_and_configure(injection_config)
logger.debug('Injection complete')

logger.info('Configuring plugins')
plugin_manager.set_plugin_annotation_references()
plugin_manager.register_plugin_signals()

thread_manager.add_threads(
    journal.JournalLiveEventThread(journal_reader),
    signalslib.signal_manager.get_signal_executor_thread(),
    *plugin_manager.get_scheduled_methods_threads()
)

with thread_manager:
    time.sleep(0.1)  # do we need this? for threads warmup
    signals.init_complete.emit()

    logger.info('Initializing gui')

    try:
        from edp.gui.forms.main_window import MainWindow, main_window_created_signal
        from PyQt5.QtWidgets import QApplication

        app = QApplication([])
        # app.setApplicationDisplayName('Elite Dangerous Platform')
        app.setApplicationVersion(config.VERSION)
        app.setApplicationName('EDP')

        window = MainWindow(plugin_manager)
        main_window_created_signal.emit(window=window)
        window.show()
    except:
        logger.exception('Error initializing gui')
        tb = traceback.format_exc()
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, tb, "Error initializing GUI of Elite Dangerous Platform", 1)
        raise
    else:
        app.exec_()
