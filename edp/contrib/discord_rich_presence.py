"""Discord Rich Presence integration plugin"""
import datetime
import logging
from typing import Optional, Dict

import dataclasses

from edp import plugins, config, signals
from edp.contrib import gamestate
from edp.gui.forms.settings_window import VLayoutTab
from edp.settings import BaseSettings
from edp.utils import discord_rpc

logger = logging.getLogger(__name__)


class DRPSettings(BaseSettings):
    """Define DRP settings"""
    enabled: bool = True
    show_location: bool = True


class DRPSettingsTabWidget(VLayoutTab):
    """DRP settings widget"""
    friendly_name = 'Discord Rich Presence'

    def get_settings_links(self):
        settings = DRPSettings.get_insance()

        yield self.link_checkbox(settings, 'enabled', 'Enabled')
        yield self.link_checkbox(settings, 'show_location', 'Show location info')


@dataclasses.dataclass()
class DRPState:
    """DRP state container class"""
    state: str
    details: str
    timestamp_start: Optional[float] = None
    assets_small_text: Optional[str] = None
    assets_small_image: Optional[str] = None
    assets_large_text: Optional[str] = None
    assets_large_image: Optional[str] = None


class DiscordRichPresencePlugin(plugins.BasePlugin):
    """Discord rich presence plugin"""

    def __init__(self):
        self.settings = DRPSettings.get_insance()
        self._current_state: Optional[DRPState] = None
        self._rpc_client = discord_rpc.DiscordRpcClient(config.DISCORD_CLIENT_ID)

    def is_enalbed(self):
        return self.settings.enabled

    def set_state(self, state: DRPState):
        """Set current state so it will be flushed to discord in background"""
        state.timestamp_start = datetime.datetime.now().timestamp()
        self._current_state = state

    @plugins.bind_signal(gamestate.game_state_changed_signal, gamestate.game_state_set_signal)
    def on_game_state_changed(self, state: gamestate.GameStateData):
        """Handle game state changes"""
        drp_state: Optional[DRPState] = None

        if self.settings.show_location:
            location = f'In system {state.location.system}'
        else:
            location = f'Somewhere in space'

        if state.location.docked:
            drp_state = DRPState(f'Docked at {state.location.station.name}', location)
        elif state.location.supercruise:
            drp_state = DRPState(f'Supercruise', location)
        else:
            drp_state = DRPState(f'In normal space', location)

        if drp_state:
            drp_state.assets_small_text = f'{state.ship.model} {state.ship.name} {state.ship.ident}'
            drp_state.assets_small_image = (state.ship.model or '').lower()
            drp_state.assets_large_image = 'logo'
            self.set_state(drp_state)

    @plugins.scheduled(15)
    def update_discord_state(self):
        """Update discord rich presence state periodically in a minimum allowed interval"""
        state, self._current_state = self._current_state, None

        if not state:
            return

        self.set_activity(state)

    def set_activity(self, state: DRPState):
        """Send state to discord"""
        activity: Dict = {
            'state': state.state,
            'details': state.details,
            'timestamps': {
                'start': int(state.timestamp_start or datetime.datetime.now().timestamp())
            }
        }
        if state.assets_large_text:
            activity.setdefault('assets', {})
            activity['assets']['large_text'] = state.assets_large_text
        if state.assets_large_image:
            activity.setdefault('assets', {})
            activity['assets']['large_image'] = state.assets_large_image
        if state.assets_small_text:
            activity.setdefault('assets', {})
            activity['assets']['small_text'] = state.assets_small_text
        if state.assets_small_image:
            activity.setdefault('assets', {})
            activity['assets']['small_image'] = state.assets_small_image

        try:
            self._rpc_client.set_activity(activity)
        except ConnectionError:
            logger.debug('Cant connect to discord app')
        except:
            logger.exception('Failed to send activity to discord app')

    def get_settings_widget(self):
        return DRPSettingsTabWidget()

    @plugins.bind_signal(signals.exiting)
    def on_exit(self):
        """Close rpc client on application exit"""
        try:
            self._rpc_client.close()
        except:
            logger.warning('Error closing client', exc_info=True)
