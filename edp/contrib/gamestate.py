import collections
import dataclasses
import logging
import threading
from typing import List, Dict, Callable

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


@mutation('Commander')
def commander_event(event: Event, state: GameStateData):
    data: dict = collections.defaultdict(lambda: state.__sentinel__, event.data)

    state.commander.name = data['Name']
    state.commander.frontier_id = data['FID']


@mutation('Materials')
def materials_event(event: Event, state: GameStateData):
    get_materials = lambda t: {m['Name']: entities.Material(m['Name'], m['Count'])
                               for m in event.data.get(t, [])
                               if 'Name' in m and 'Count' in m}

    state.material_storage.raw: Dict[str, entities.Material] = get_materials('Raw')
    state.material_storage.encoded: Dict[str, entities.Material] = get_materials('Encoded')
    state.material_storage.manufactured: Dict[str, entities.Material] = get_materials('Manufactured')


@mutation('LoadGame')
def load_game_event(event: Event, state: GameStateData):
    data: dict = collections.defaultdict(lambda: state.__sentinel__, event.data)

    state.commander.name = data['Commander']
    state.commander.frontier_id = data['FID']

    state.ship.model = data['Ship']
    state.ship.id = data['ShipID']
    state.ship.name = data['ShipName']
    state.ship.ident = data['ShipIdent']

    state.credits = data['Credits']


@mutation('Rank')
def rank_event(event: Event, state: GameStateData):
    data: dict = collections.defaultdict(lambda: state.__sentinel__, event.data)

    state.rank.combat = data['Combat']
    state.rank.trade = data['Trade']
    state.rank.explore = data['Explore']
    state.rank.empire = data['Empire']
    state.rank.federation = data['Federation']
    state.rank.cqc = data['CQC']


@mutation('Progress')
def progress_event(event: Event, state: GameStateData):
    data: dict = collections.defaultdict(lambda: state.__sentinel__, event.data)

    state.rank.combat_progres = data['Combat']
    state.rank.trade_progres = data['Trade']
    state.rank.explore_progres = data['Explore']
    state.rank.empire_progres = data['Empire']
    state.rank.federation_progres = data['Federation']
    state.rank.cqc_progres = data['CQC']


@mutation('Reputation')
def reputation_event(event: Event, state: GameStateData):
    data: dict = collections.defaultdict(lambda: state.__sentinel__, event.data)

    state.reputation.federation = data['Federation']
    state.reputation.empire = data['Empire']
    state.reputation.alliance = data['Alliance']


@mutation('EngineerProgress')
def engineer_progress_event(event: Event, state: GameStateData):
    create_engineer = lambda e: entities.Engineer(
        name=e['Engineer'],
        id=e['EngineerID'],
        progress=e['Progress'],
        rank=e.get('Rank', None),
        rank_progress=e.get('RankProgress', None)
    )

    state.engineers = {e['EngineerID']: create_engineer(e) for e in event.data.get('Engineers', [])
                       if 'EngineerID' in e and 'Engineer' in e and 'Progress' in e}


@mutation('Loadout')
def loadout_event(event: Event, state: GameStateData):
    data: dict = collections.defaultdict(lambda: state.__sentinel__, event.data)

    state.ship.model = data['Ship']
    state.ship.id = data['ShipID']
    state.ship.name = data['ShipName']
    state.ship.ident = data['ShipIdent']

    # TODO: Store hull value, modules, rebuy


@mutation('Location', 'FSDJump')
def location_event(event: Event, state: GameStateData):
    data: dict = collections.defaultdict(lambda: state.__sentinel__, event.data)

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

    if event.name == 'FSDJump':
        state.location.supercruise = True

    # TODO: factions


@mutation('Docked')
def docked_event(event: Event, state: GameStateData):
    data: dict = collections.defaultdict(lambda: state.__sentinel__, event.data)

    state.location.docked = True
    state.location.station.name = data['StationName']
    state.location.station.type = data['StationType']
    state.location.station.market = data['MarketID']
    state.location.station.faction = data['StationFaction']
    state.location.station.government = data['StationGovernment']
    state.location.station.services = data['StationServices']
    state.location.station.economy = data['StationEconomy']


@mutation('Undocked')
def undocked_event(event: Event, state: GameStateData):
    state.location.docked = False
    state.location.station.clear()


@mutation('Cargo')
def cargo_event(event: Event, state: GameStateData):
    pass
    # TODO: Cargo


@mutation('MaterialCollected')
def material_collected_event(event: Event, state: GameStateData):
    if not {'Category', 'Name', 'Count'}.issubset(event.data.keys()):
        return

    category = event.data['Category']
    name = event.data['Name']
    count = event.data['Count']

    material_category = state.material_storage[category]
    if name in material_category:
        material_category[name].count += count
    else:
        material_category[name] = entities.Material(name, count)


@mutation('SupercruiseEntry')
def supercruise_entry_event(event: Event, state: GameStateData):
    state.location.supercruise = True


@mutation('SupercruiseExit')
def supercruise_entry_event(event: Event, state: GameStateData):
    state.location.supercruise = False
