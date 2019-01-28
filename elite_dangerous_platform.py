import ctypes
import logging
import platform
import time
import traceback

import inject
import sentry_sdk

from edp.contrib import discord_rich_presence, inara


def main():
    from PyQt5.QtWidgets import QApplication

    from edp import signalslib, plugins, thread, signals, journal, config, logging_tools
    from edp.gui.forms.main_window import MainWindow, main_window_created_signal
    from edp.contrib import edsm, gamestate, eddn
    from edp.settings import EDPSettings

    settings = EDPSettings.get_insance()

    logging_tools.configure(enable_sentry=settings.enable_error_reports)

    logger = logging.getLogger('edp')

    with sentry_sdk.configure_scope() as scope:
        scope.user = {'id': settings.user_id}
        scope.set_tag('platform', platform.platform())

        logger.info('Initializing thread manager')
        thread_manager = thread.ThreadManager()

        logger.info('Initializing flightlog journal handler')
        journal_reader = journal.JournalReader(settings.journal_dir)

        game_version = journal_reader.get_game_version_info()
        if game_version:
            scope.set_tag('game_version', game_version.version)
            scope.set_extra('game_build', game_version.build)

        logger.info('Loading plugins')
        plugin_loader = plugins.PluginLoader(settings.plugin_dir)

        plugin_loader.add_plugin(edsm.EDSMPlugin)
        plugin_loader.add_plugin(gamestate.GameState)
        plugin_loader.add_plugin(eddn.EDDNPlugin)
        plugin_loader.add_plugin(discord_rich_presence.DiscordRichPresencePlugin)
        plugin_loader.add_plugin(inara.InaraPlugin)
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

            app = QApplication([])
            # app.setApplicationDisplayName('Elite Dangerous Platform')
            app.setApplicationVersion(config.VERSION)
            app.setApplicationName(config.APPNAME_SHORT)

            window = MainWindow(plugin_manager)
            main_window_created_signal.emit(window=window)
            window.show()
            app.exec_()


if __name__ == '__main__':
    try:
        main()
    except:
        tb = traceback.format_exc()
        ctypes.windll.user32.MessageBoxW(0, tb, "Error initializing Elite Dangerous Platform", 1)
        raise
