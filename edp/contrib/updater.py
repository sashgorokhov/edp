"""Plugin that does software updates"""
import logging
from typing import Optional

from PyQt5 import QtWidgets

from edp import plugins, signals, config
from edp.gui.forms.updater_window import UpdaterWindow
from edp.settings import EDPSettings
from edp.utils import github, is_version_newer

logger = logging.getLogger(__name__)


class UpdaterPlugin(plugins.BasePlugin):
    """Check for new github release and show edp.gui.forms.updater_window.UpdaterWindow if new version is available"""
    name = 'App updater'

    def __init__(self):
        super(UpdaterPlugin, self).__init__()

        self._api = github.GithubApi()
        self._settings = EDPSettings.get_insance()
        self._window = None

    @plugins.bind_signal(signals.app_created)
    def on_app_created(self):
        """Check for updates when qt app created and show updater window if newer version found"""
        if self._settings.check_for_updates:
            logger.info('Checking for updates')
            release = self.check_for_updates()
            if not release:
                logger.info('No updates found')
                return
            logger.info(f'Found update: {release["id"]}')
            self.show_updater_window(release)

    def check_for_updates(self) -> Optional[dict]:
        """Check for newer version on github releases and return release info dict if found any"""
        releases = self._api.get_releases('sashgorokhov', 'edp')
        for release in releases:
            version = release['tag_name']
            if not version:
                continue
            if release.get('prerelease', False) and not self._settings.receive_patches or release.get('draft', False):
                continue
            try:
                if is_version_newer(version, config.VERSION):
                    return release
            except:
                logger.exception(f'Failed to parse gitgub tag as version: "{version}", release id={release.get("id")}')

        return None

    def show_updater_window(self, release: dict):
        """Show edp.gui.forms.updater_window.UpdaterWindow with given release info"""
        try:
            self._window = UpdaterWindow(release)
        except:
            logger.exception('Failed to create updater window')
            return

        self._window.show()
        self._window.raise_()
        self._window.activateWindow()

    def get_settings_widget(self) -> Optional[QtWidgets.QWidget]:
        return None
