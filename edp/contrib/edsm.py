import functools
import logging
import threading
from typing import List

import inject
import requests

from edp import signals
from edp.journal import Event
from edp.plugin import BasePlugin, callback, scheduled
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
    settings = inject.attr(Settings)

    def __init__(self, *args, **kwargs):
        super(EDSMPlugin, self).__init__(*args, **kwargs)
        self._event_buffer: List[Event] = []
        self._event_buffer_lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self.settings.edsm_api_key and self.settings.edsm_commander_name

    @property
    @functools.lru_cache()
    def api(self):
        return EDSMApi.from_settings(self.settings)

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

        self.api.journal_event(*[event.raw for event in events])
