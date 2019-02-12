"""Overlay UI plugin"""
from typing import Optional, Dict

from edp import plugins, signals
from edp.gui.forms import overlay_window
from edp.gui.forms.settings_window import VLayoutTab
from edp.settings import BaseSettings


class OverlaySettings(BaseSettings):
    """Overlay plugin settings"""
    layout_widgets: Dict[str, str] = {}  # layout name/id -> widget friendly name


class OverlaySettingsTabWidget(VLayoutTab):
    """Overlay UI settings widget"""
    friendly_name = 'Overlay UI'

    def get_settings_links(self):
        yield from []


class OverlayPlugin(plugins.BasePlugin):
    """Overlay UI plugin"""
    friendly_name = 'Overlay UI'

    def __init__(self):
        self.overlay_window: Optional[overlay_window.GameOverlayWindow] = None

    def get_settings_widget(self):
        return None  # OverlaySettingsTabWidget()

    @plugins.bind_signal(signals.app_created)
    def on_app_created(self):
        """Create overlay window when qt app is created"""
        self.overlay_window = overlay_window.GameOverlayWindow()
