import logging
import threading
from typing import List, Dict

import dataclasses
import inject

from edp import entities, signals
from edp.journal import JournalReader, Event, journal_event_signal
from edp.plugins import BasePlugin
from edp.signalslib import Signal

logger = logging.getLogger(__name__)


@dataclasses.dataclass(init=False)
class GameStateData(entities._BaseEntity):
    commander: entities.Commander = entities.Commander()
    material_storage: entities.MaterialStorage = entities.MaterialStorage()
    ship: entities.Ship = entities.Ship()
    rank: entities.Rank = entities.Rank()
    reputation: entities.Reputation = entities.Reputation()
    engineers: Dict[int, entities.Engineer] = dataclasses.field(default_factory=dict)
    location: entities.Location = entities.Location()
    credits: int = 0

    # TODO: game mode: solo or open

    @classmethod
    def get_clear_data(cls) -> 'GameStateData':
        return cls()

    def frozen(self) -> 'GameStateData':
        # TODO: Return immutable game state data
        return self


game_state_changed_signal = Signal('game state changed', state=GameStateData)
game_state_set_signal = Signal('game state set', state=GameStateData)


class GameState(BasePlugin):
    journal_reader: JournalReader = inject.attr(JournalReader)

    def __init__(self):
        self._state = GameStateData.get_clear_data()
        self._state_lock = threading.Lock()

        journal_event_signal.bind(self.on_journal_event)
        signals.init_complete.bind(self.set_initial_state)

    @property
    def state(self) -> GameStateData:
        return self._state.frozen()

    def on_journal_event(self, event: Event):
        changed = self.update_state(event)
        if changed:
            game_state_changed_signal.emit(state=self.state)

    def set_initial_state(self):
        events: List[Event] = self.journal_reader.get_latest_file_events()

        for event in events:
            self.update_state(event)

        game_state_set_signal.emit(state=self.state)
        logger.debug('Initial state: %s', self._state)

    def update_state(self, event: Event) -> bool:
        from edp.contrib.gamestate_mutations import mutate

        with self._state_lock:
            mutate(event, self._state)
            changed = self._state.is_changed
            self._state.reset_changed()

        return changed


def get_gamestate() -> GameStateData:
    gamestate = inject.instance(GameState)
    return gamestate.state
