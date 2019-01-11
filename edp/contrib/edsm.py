import functools
import json
import logging
import threading
from typing import List

import inject
import requests

from edp import signals
from edp.contrib.gamestate import GameState, GameStateData
from edp.journal import Event
from edp.plugin import BasePlugin, callback, scheduled, PluginManager
from edp.settings import Settings

logger = logging.getLogger(__name__)


class EDSMApi:
    software = 'edp'
    software_version = '0.1'
    timeout = 10

    def __init__(self, api_key: str, commander_name: str):
        self._api_key = api_key
        self._commander_name = commander_name
        self._session = requests.Session()

    @classmethod
    def from_settings(cls, settings: Settings) -> 'EDSMApi':
        return cls(settings.edsm_api_key, settings.edsm_commander_name)

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


class EDSMPlugin(BasePlugin):
    settings: Settings = inject.attr(Settings)

    def __init__(self, *args, **kwargs):
        super(EDSMPlugin, self).__init__(*args, **kwargs)
        self._event_buffer: List[Event] = []
        self._event_buffer_lock = threading.Lock()
        self.api = EDSMApi.from_settings(self.settings)
        self._gamestate: GameState = None

    @callback(signals.INIT_COMPLETE)
    def on_init_complete(self):
        plugin_manager = inject.instance(PluginManager)
        self._gamestate: GameState = plugin_manager[GameState]

    @property
    def enabled(self) -> bool:
        return bool(self.settings.edsm_api_key and self.settings.edsm_commander_name)

    @property
    @functools.lru_cache()
    def discarded_events(self) -> List[str]:
        return self.api.discarded_events()

    @callback(signals.JOURNAL_EVENT)
    def journal_event(self, event: Event):
        if event.name in self.discarded_events:
            return
        with self._event_buffer_lock:
            self._event_buffer.append(event)

    @scheduled(60)
    def push_events(self):
        if not self._event_buffer:
            return

        with self._event_buffer_lock:
            events = self._event_buffer.copy()
            self._event_buffer.clear()

        state = self._gamestate.state
        patched_events = [self.patch_event(event.raw, state) for event in events]

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
