import functools
import json
import logging
import threading
from typing import List, Optional, Callable, TypeVar

import requests

from edp import plugins
from edp.contrib.gamestate import GameState, GameStateData, game_state_set_signal
from edp.gui.forms.settings_window import VLayoutTab
from edp.journal import Event, journal_event_signal
from edp.plugins import BasePlugin
from edp.settings import BaseSettings

logger = logging.getLogger(__name__)


class EDSMSettings(BaseSettings):
    api_key: Optional[str] = None
    commander_name: Optional[str] = None


class EDSMSettingsTabWidget(VLayoutTab):
    friendly_name = 'EDSM'

    def get_settings_links(self):
        settings = EDSMSettings.get_insance()

        yield self.link_line_edit(settings, 'api_key', 'Api key')
        yield self.link_line_edit(settings, 'commander_name', 'Commander name')


class EDSMApi:
    software = 'edp'
    software_version = '0.1'
    timeout = 10

    def __init__(self, api_key: str, commander_name: str):
        self._api_key = api_key
        self._commander_name = commander_name
        self._session = requests.Session()

    @classmethod
    def from_settings(cls, settings: EDSMSettings) -> 'EDSMApi':
        if settings.api_key and settings.commander_name:
            return cls(settings.api_key, settings.commander_name)
        raise ValueError(f'Settings not set: api_key={settings.api_key} commander_name={settings.commander_name}')

    def discarded_events(self) -> List[str]:
        response = self._session.get('https://www.edsm.net/api-journal-v1/discard', timeout=self.timeout)
        return response.json()

    def journal_event(self, *events: str):
        data = {
            'commanderName': self._commander_name,
            'apiKey': self._api_key,
            'fromSoftware': self.software,
            'fromSoftwareVersion': self.software_version,
            'message': events
        }
        response = self._session.post('https://www.edsm.net/api-journal-v1', json=data, timeout=15)
        logger.debug('Journal events sent: %s', response.status_code)


T = TypeVar('T')


def cache(func: Callable[..., T]) -> T:
    return functools.lru_cache()(func)  # type: ignore


class EDSMPlugin(BasePlugin):
    gamestate: GameState

    def __init__(self, *args, **kwargs):
        super(EDSMPlugin, self).__init__(*args, **kwargs)
        self._event_buffer: List[Event] = []
        self._event_buffer_lock = threading.Lock()

        self.settings = EDSMSettings.get_insance()

    def is_enalbed(self):
        return self.settings.api_key and self.settings.commander_name

    @plugins.bind_signal(game_state_set_signal, plugin_enabled=False)
    def on_game_state_set(self, state: GameStateData):
        if not self.settings.commander_name and state.commander.name:
            self.settings.commander_name = state.commander.name

    @property  # type: ignore
    @cache
    def api(self) -> EDSMApi:
        return EDSMApi.from_settings(self.settings)

    @property  # type: ignore
    @cache
    def discarded_events(self) -> List[str]:
        return self.api.discarded_events()

    @plugins.bind_signal(journal_event_signal)
    def journal_event(self, event: Event):
        if event.name in self.discarded_events:
            return
        with self._event_buffer_lock:
            self._event_buffer.append(event)

    @plugins.scheduled(60)
    def push_events(self):
        if not self._event_buffer:
            return

        with self._event_buffer_lock:
            events = self._event_buffer.copy()
            self._event_buffer.clear()

        patched_events = [self.patch_event(event.raw, self.gamestate.state) for event in events]

        self.api.journal_event(*patched_events)

    def patch_event(self, event_line: str, state: GameStateData) -> str:
        event: dict = json.loads(event_line)

        event['_systemAddress'] = state.location.address
        event['_systemName'] = state.location.system
        event['_systemCoordinates'] = state.location.pos
        event['_marketId'] = state.location.station.market
        event['_stationName'] = state.location.station.name
        event['_shipId'] = state.ship.id

        return json.dumps(event)

    def get_settings_widget(self):
        return EDSMSettingsTabWidget()
