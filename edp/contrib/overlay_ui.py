from typing import Optional

from PyQt5 import QtWidgets

from edp import plugins, signals
from edp.gui.forms import overlay_window
from edp.gui.forms.settings_window import VLayoutTab
from edp.settings import BaseSettings


class OverlaySettings(BaseSettings):
    pass


class OverlaySettingsTabWidget(VLayoutTab):
    def get_settings_links(self):
        yield from []


class OverlayPlugin(plugins.BasePlugin):
    friendly_name = 'Overlay UI'

    def __init__(self):
        self.overlay_window: Optional[overlay_window.GameOverlayWindow] = None

    def get_settings_widget(self) -> Optional[QtWidgets.QWidget]:
        return OverlaySettingsTabWidget()

    @plugins.bind_signal(signals.app_created)
    def on_app_created(self):
        self.overlay_window = overlay_window.GameOverlayWindow()
