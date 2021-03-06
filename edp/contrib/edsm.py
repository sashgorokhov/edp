"""
EDSM integration plugin

Sends commander journal events to EDSM
"""
import functools
import json
import logging
from typing import List, Optional, Callable, TypeVar

import inject
import requests

from edp import plugins, config, utils, journal
from edp.contrib.gamestate import GameStatePlugin, GameStateData, game_state_set_signal
from edp.gui.forms.settings_window import VLayoutTab
from edp.plugins import BasePlugin
from edp.settings import BaseSettings
from edp.utils.plugins_helpers import BufferedEventsMixin

logger = logging.getLogger(__name__)


class EDSMSettings(BaseSettings):
    """EDSM plugin settings"""
    enabled: bool = True
    api_key: Optional[str] = None
    commander_name: Optional[str] = None


class EDSMSettingsTabWidget(VLayoutTab):
    """EDSM plugin settings widget"""
    friendly_name = 'EDSM'

    def get_settings_links(self):
        settings = EDSMSettings.get_insance()

        yield self.link_checkbox(settings, 'enabled', 'Enabled')
        yield self.link_line_edit(settings, 'api_key', 'Api key')
        yield self.link_line_edit(settings, 'commander_name', 'Commander name')


class EDSMApi:
    """EDSM api interface"""
    timeout = 10

    def __init__(self, api_key: Optional[str] = None, commander_name: Optional[str] = None):
        self._api_key = api_key
        self._commander_name = commander_name
        self._session = requests.Session()
        self._session.headers['User-Agent'] = config.USERAGENT

    @classmethod
    def from_settings(cls, settings: EDSMSettings) -> 'EDSMApi':
        """Create instance from settings"""
        return cls(settings.api_key, settings.commander_name)

    @classmethod
    def from_edsm_settings(cls) -> 'EDSMApi':
        """Create instance from edsm settings"""
        settings = EDSMSettings.get_insance()
        return cls.from_settings(settings)

    @functools.lru_cache()
    def discarded_events(self) -> List[str]:
        """Return list of edsm discarded events names"""
        response = self._session.get('https://www.edsm.net/api-journal-v1/discard', timeout=self.timeout)
        return response.json()

    def journal_event(self, *events: dict):
        """Send journal events to edsm"""
        if not self._api_key or not self._commander_name:
            raise ValueError('api key or commander name not set')

        data = {
            'commanderName': self._commander_name,
            'apiKey': self._api_key,
            'fromSoftware': config.APPNAME_LONG,
            'fromSoftwareVersion': config.VERSION,
            'message': events
        }
        response = self._session.post('https://www.edsm.net/api-journal-v1', json=data, timeout=15)
        logger.debug(f'Sent {len(events)} events, status code is {response.status_code}')
        if response.status_code < 300:
            response_data = response.json()
            for event_status, event_data in zip(response_data['events'], events):
                if event_status['msgnum'] >= 200:
                    logger.warning(f'EDSM error: {event_status["msgnum"]} {event_status["msg"]}: {event_data}')

        if response.status_code >= 400:
            logger.error(response.text)
            logger.error(events)

    @functools.lru_cache(120)
    def get_system(self, name: str) -> dict:
        """Return edsm system id by its name"""
        response = self._session.post('https://www.edsm.net/api-v1/system',
                                      json={'systemName': name, 'showId': 1},
                                      timeout=self.timeout)
        return response.json()


T = TypeVar('T')


def cache(func: Callable[..., T]) -> T:  # noqa
    """Stub to make lru_cache on property recognized by mypy"""
    return functools.lru_cache()(func)  # type: ignore


class EDSMPlugin(BufferedEventsMixin, BasePlugin):
    """EDSM plugin"""
    gamestate: GameStatePlugin = inject.attr(GameStatePlugin)

    def __init__(self, *args, **kwargs):
        super(EDSMPlugin, self).__init__(*args, **kwargs)

        self.settings = EDSMSettings.get_insance()

    def is_enalbed(self):
        return bool(self.settings.enabled and self.settings.api_key and self.settings.commander_name)

    @plugins.bind_signal(game_state_set_signal, plugin_enabled=False)
    def on_game_state_set(self, state: GameStateData):
        """Set commander name from game state"""
        if not self.settings.commander_name and state.commander.name:
            self.settings.commander_name = state.commander.name

    @property  # type: ignore
    @cache
    def api(self) -> EDSMApi:
        """Return EDSMApi instance configured from settings"""
        return EDSMApi.from_settings(self.settings)

    @property  # type: ignore
    @cache
    def discarded_events(self) -> List[str]:
        """Return list of discareded events names"""
        return self.api.discarded_events()

    def filter_event(self, event: journal.Event):
        """Filter out edsm discarded events before putting them into buffer"""
        return event.name not in self.discarded_events

    def process_buffered_events(self, events: List[journal.Event]):
        """
        Process buffered events

        Patches every event with recorded transient state and sends events in chunks
        """
        patched_events = [self.patch_event(event.raw, self.gamestate.state) for event in events]

        # Sometimes EDSM has ConnectionError so need to send events in chunks and try to retry.
        for chunk in utils.chunked(patched_events, size=10):
            try:
                self.api.journal_event(*chunk)
            except requests.exceptions.ConnectionError:
                logger.warning(f'ConnectionError while sending {len(chunk)} events to EDSM')
                logger.warning('Trying one more time...')

                try:
                    self.api.journal_event(*chunk)
                except requests.exceptions.ConnectionError:
                    logger.error('ConnectionError second time, give up')
                    logger.error(chunk)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code >= 500:
                    logger.warning('EDSM returned ServerError')
                    return
                logger.exception(f'HTTPError from edsm while sending: {chunk}')

    # pylint: disable=no-self-use
    def patch_event(self, event_line: str, state: GameStateData) -> dict:
        """Patch event with transient state"""
        event: dict = json.loads(event_line)

        event['_systemAddress'] = state.location.address
        event['_systemName'] = state.location.system
        event['_systemCoordinates'] = state.location.pos
        event['_marketId'] = state.location.station.market
        event['_stationName'] = state.location.station.name
        event['_shipId'] = state.ship.id

        return event

    def get_settings_widget(self):
        return EDSMSettingsTabWidget()
