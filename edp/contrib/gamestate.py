import collections
import dataclasses
import logging
import threading
from typing import List, Dict, Callable

import inject

from edp import signals, domains
from edp.journal import JournalReader, Event
from edp.plugin import BasePlugin, callback, PluginManager
from edp.utils import catch_errors, dataclass_as_namedtuple

logger = logging.getLogger(__name__)


class SIGNALS:
    GAME_STATE_CHANGED = 'game state changed'
    GAME_STATE_SET = 'game state set'


@dataclasses.dataclass
class GameStateData(domains._BaseDomain):
    commander: domains.Commander = domains.Commander()
    material_storage: domains.MaterialStorage = domains.MaterialStorage()
    ship: domains.Ship = domains.Ship()
    rank: domains.Rank = domains.Rank()
    reputation: domains.Reputation = domains.Reputation()
    engineers: Dict[int, domains.Engineer] = dataclasses.field(default_factory=dict)
    location: domains.Location = domains.Location()
    credits: int = 0

    def frozen(self) -> 'GameStateData':
        return dataclass_as_namedtuple(self)


_GAME_STATE_MUTATIONS: Dict[str, Callable[[Event, GameStateData], None]] = {}


def mutation(event: str):
    def decor(func: Callable[[Event, GameStateData], GameStateData]):
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
        events: List[Event] = self.journal_reader.get_latest_file_events()

        for event in events:
            self.update_state(event)

        self.plugin_manager.emit(SIGNALS.GAME_STATE_SET, state=self.state)
        logger.debug('Initial state: %s', self._state)

    @catch_errors
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

        # if event.name == 'SetUserShipName':
        #    new_state['ship_id'] = event.data['ShipID']
        #
        # if event.name == 'ShipyardBuy':
        #    new_state['ship_id'] = None
        #
        # if event.name == 'ShipyardSwap':
        #    new_state['ship_id'] = event.data['ShipID']
        #
        # if event.name == 'Loadout':
        #    new_state['ship_id'] = event.data['ShipID']
        #
        # if event.name == 'Undocked':
        #    new_state['station_id'] = None
        #    new_state['station'] = None
        #
        # if event.name in ('Location', 'FSDJump', 'Docked'):
        #    if event.data['StarSystem'] != new_state['system']:
        #        new_state['coordinates'] = None
        #    if event.data['StarSystem'] in ('ProvingGround', 'CQC'):
        #        new_state['system_id'] = None
        #        new_state['system'] = None
        #        new_state['coordinates'] = None
        #    else:
        #        if event.data['SystemAddress'] is not None:
        #            new_state['system_id'] = event.data['SystemAddress']
        #
        #        new_state['system'] = event.data['StarSystem']
        #
        #        if event.data['StarPos'] is not None:
        #            new_state['coordinates'] = event.data['StarPos']
        #
        #    if event.data['MarketID'] is not None:
        #        new_state['station_id'] = event.data['MarketID']
        #
        #    if event.data['StationName'] is not None:
        #        new_state['station'] = event.data['StationName']
        #
        # self.state = GameStateData(**new_state)
        # return new_state != old_state


@mutation('Commander')
def commander_event(event: Event, state: GameStateData):
    data: dict = collections.defaultdict(lambda: state.__sentinel__)
    data.update(event.data)

    state.commander.name = data['Name']
    state.commander.frontier_id = data['FID']


@mutation('Materials')
def materials_event(event: Event, state: GameStateData):
    get_materials = lambda t: {m['Name']: domains.Material(m['Name'], m['Count'])
                               for m in event.data.get(t, [])
                               if 'Name' in m and 'Count' in m}

    state.material_storage.raw: Dict[str, domains.Material] = get_materials('Raw')
    state.material_storage.encoded: Dict[str, domains.Material] = get_materials('Encoded')
    state.material_storage.manufactured: Dict[str, domains.Material] = get_materials('Manufactured')


@mutation('LoadGame')
def load_game_event(event: Event, state: GameStateData):
    data: dict = collections.defaultdict(lambda: state.__sentinel__)
    data.update(event.data)

    state.commander.name = data['Commander']
    state.commander.frontier_id = data['FID']

    state.ship.model = data['Ship']
    state.ship.id = data['ShipID']
    state.ship.name = data['ShipName']
    state.ship.ident = data['ShipIdent']

    state.credits = data['Credits']


@mutation('Rank')
def rank_event(event: Event, state: GameStateData):
    data: dict = collections.defaultdict(lambda: state.__sentinel__)
    data.update(event.data)

    state.rank.combat = data['Combat']
    state.rank.trade = data['Trade']
    state.rank.explore = data['Explore']
    state.rank.empire = data['Empire']
    state.rank.federation = data['Federation']
    state.rank.cqc = data['CQC']


@mutation('Progress')
def progress_event(event: Event, state: GameStateData):
    data: dict = collections.defaultdict(lambda: state.__sentinel__)
    data.update(event.data)

    state.rank.combat_progres = data['Combat']
    state.rank.trade_progres = data['Trade']
    state.rank.explore_progres = data['Explore']
    state.rank.empire_progres = data['Empire']
    state.rank.federation_progres = data['Federation']
    state.rank.cqc_progres = data['CQC']


@mutation('Reputation')
def reputation_event(event: Event, state: GameStateData):
    data: dict = collections.defaultdict(lambda: state.__sentinel__)
    data.update(event.data)

    state.reputation.federation = data['Federation']
    state.reputation.empire = data['Empire']
    state.reputation.alliance = data['Alliance']


@mutation('EngineerProgress')
def engineer_progress_event(event: Event, state: GameStateData):
    create_engineer = lambda e: domains.Engineer(
        name=e['Name'],
        id=e['EngineerID'],
        progress=e['Progress'],
        rank=e.get('Rank', None),
        rank_progress=e.get('RankProgress', None)
    )

    state.engineers = {e['EngineerID']: create_engineer(e) for e in event.data.get('Engineers', [])
                       if 'EngineerID' in e and 'Name' in e and 'Progress' in e}


@mutation('Loadout')
def loadout_event(event: Event, state: GameStateData):
    data: dict = collections.defaultdict(lambda: state.__sentinel__)
    data.update(event.data)

    state.ship.model = data['Ship']
    state.ship.id = data['ShipID']
    state.ship.name = data['ShipName']
    state.ship.ident = data['ShipIdent']

    # TODO: Store hull value, modules, rebuy


@mutation('Location')
def location_event(event: Event, state: GameStateData):
    data: dict = collections.defaultdict(lambda: state.__sentinel__)
    data.update(event.data)

    state.location.docked = data['Docked']
    state.location.system = data['StarSystem']
    state.location.address = data['SystemAddress']
    state.location.pos = data['StarPos']
    state.location.allegiance = data['SystemAllegiance']
    state.location.economy = data['SystemEconomy']
    state.location.economy_second = data['SystemSecondEconomy']
    state.location.government = data['SystemGovernment']
    state.location.security = data['SystemSecurity']
    state.location.population = data['Population']
    state.location.faction = data['SystemFaction']

    # TODO: factions
