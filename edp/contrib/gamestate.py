import logging
from typing import List, NamedTuple, Optional

import inject

from edp import signals
from edp.journal import JournalReader, Event
from edp.plugin import BasePlugin, callback, PluginManager
from edp.utils import catch_errors

logger = logging.getLogger(__name__)


class SIGNALS:
    GAME_STATE_CHANGED = 'game state changed'


class GameStateData(NamedTuple):
    system_id: Optional[str]
    system: Optional[str]
    coordinates: Optional[str]
    station_id: Optional[str]
    station: Optional[str]
    ship_id: Optional[str]
    cmdr: Optional[str]


class GameState(BasePlugin):
    journal_reader: JournalReader = inject.attr(JournalReader)
    plugin_manager: PluginManager = inject.attr(PluginManager)

    def __init__(self):
        self.state = GameStateData(None, None, None, None, None, None, None)

    @callback(signals.JOURNAL_EVENT)
    def on_journal_event(self, event: Event):
        changed = self.update_state(event)
        if changed:
            self.plugin_manager.emit(SIGNALS.GAME_STATE_CHANGED, state=self.state)

    @callback(signals.INIT_COMPLETE)
    def set_initial_state(self):
        events: List[Event] = self.journal_reader.get_latest_file_events()

        for event in events:
            self.update_state(event)

        logger.debug('Initial state: %s', self.state)

    @catch_errors
    def update_state(self, event: Event) -> bool:
        old_state = self.state._asdict()
        new_state = old_state.copy()

        if event.name == 'SetUserShipName':
            new_state['ship_id'] = event.data['ShipID']

        if event.name == 'ShipyardBuy':
            new_state['ship_id'] = None

        if event.name == 'ShipyardSwap':
            new_state['ship_id'] = event.data['ShipID']

        if event.name == 'Loadout':
            new_state['ship_id'] = event.data['ShipID']

        if event.name == 'Undocked':
            new_state['station_id'] = None
            new_state['station'] = None

        if event.name in ('Location', 'FSDJump', 'Docked'):
            if event.data['StarSystem'] != new_state['system']:
                new_state['coordinates'] = None
            if event.data['StarSystem'] in ('ProvingGround', 'CQC'):
                new_state['system_id'] = None
                new_state['system'] = None
                new_state['coordinates'] = None
            else:
                if event.data['SystemAddress'] is not None:
                    new_state['system_id'] = event.data['SystemAddress']

                new_state['system'] = event.data['StarSystem']

                if event.data['StarPos'] is not None:
                    new_state['coordinates'] = event.data['StarPos']

            if event.data['MarketID'] is not None:
                new_state['station_id'] = event.data['MarketID']

            if event.data['StationName'] is not None:
                new_state['station'] = event.data['StationName']

        self.state = GameStateData(**new_state)
        return new_state != old_state
