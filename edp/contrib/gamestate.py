import logging
import threading
from typing import List, Dict, Callable

import dataclasses
import inject

from edp import signals, entities
from edp.journal import JournalReader, Event
from edp.plugin import BasePlugin, callback, PluginManager

logger = logging.getLogger(__name__)


class SIGNALS:
    GAME_STATE_CHANGED = 'game state changed'
    GAME_STATE_SET = 'game state set'


@dataclasses.dataclass
class GameStateData(entities._BaseEntity):
    commander: entities.Commander = entities.Commander()
    material_storage: entities.MaterialStorage = entities.MaterialStorage()
    ship: entities.Ship = entities.Ship()
    rank: entities.Rank = entities.Rank()
    reputation: entities.Reputation = entities.Reputation()
    engineers: Dict[int, entities.Engineer] = dataclasses.field(default_factory=dict)
    location: entities.Location = entities.Location()
    credits: int = 0

    def frozen(self) -> 'GameStateData':
        # TODO: Return immutable game state data
        return self


_GAME_STATE_MUTATIONS: Dict[str, Callable[[Event, GameStateData], None]] = {}


def mutation(*events: str):
    def decor(func: Callable[[Event, GameStateData], GameStateData]):
        for event in events:
            if event in _GAME_STATE_MUTATIONS:
                logger.warning('Mutation for event %s already registered: %s', event, _GAME_STATE_MUTATIONS[event])
            _GAME_STATE_MUTATIONS[event] = func
        return func

    return decor


class GameState(BasePlugin):
    journal_reader: JournalReader = inject.attr(JournalReader)
    plugin_manager: PluginManager = inject.attr(PluginManager)

    def __init__(self):
        self._state = GameStateData()
        self._state_lock = threading.Lock()

    @property
    def state(self) -> GameStateData:
        return self._state.frozen()

    @callback(signals.JOURNAL_EVENT)
    def on_journal_event(self, event: Event):
        changed = self.update_state(event)
        if changed:
            self.plugin_manager.emit(SIGNALS.GAME_STATE_CHANGED, state=self.state)

    @callback(signals.INIT_COMPLETE)
    def set_initial_state(self):
        # noinspection PyUnresolvedReferences
        from edp.contrib import gamestate_mutations  # noqa

        events: List[Event] = self.journal_reader.get_latest_file_events()

        for event in events:
            self.update_state(event)

        self.plugin_manager.emit(SIGNALS.GAME_STATE_SET, state=self.state)
        logger.debug('Initial state: %s', self._state)

    def update_state(self, event: Event) -> bool:
        changed = False

        with self._state_lock:
            if event.name in _GAME_STATE_MUTATIONS:
                try:
                    _GAME_STATE_MUTATIONS[event.name](event, self._state)

                    changed = self._state.is_changed
                    self._state.reset_changed()
                except:
                    logger.exception('Failed to apply mutation: %s', _GAME_STATE_MUTATIONS[event.name])
                    logger.debug('Event: %s', event.raw)
                    logger.debug('GameStateData: %s', self._state)

        return changed
