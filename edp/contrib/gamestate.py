"""
http://hosting.zaonce.net/community/journal/v18/Journal_Manual_v18.pdf
"""
import collections
import logging
import threading
from typing import List, Dict, Callable

import dataclasses
import inject

from edp import entities, signals
from edp.journal import JournalReader, Event, journal_event_signal, VersionInfo
from edp.plugins import BasePlugin
from edp.signalslib import Signal
from edp.utils import plugins_helpers

logger = logging.getLogger(__name__)


@dataclasses.dataclass(repr=False)
class GameStateData(entities._BaseEntity):
    commander: entities.Commander = entities.Commander()
    material_storage: entities.MaterialStorage = entities.MaterialStorage()
    ship: entities.Ship = entities.Ship()
    rank: entities.Rank = entities.Rank()
    reputation: entities.Reputation = entities.Reputation()
    engineers: Dict[int, entities.Engineer] = dataclasses.field(default_factory=dict)
    location: entities.Location = entities.Location()
    credits: int = 0
    running: bool = False
    version: VersionInfo = dataclasses.field(default_factory=VersionInfo)
    horizons: bool = False
    solo: bool = False

    def __init__(self):
        self.engineers = {}
        self.version = VersionInfo()
        super(GameStateData, self).__init__()

    @classmethod
    def get_clear_data(cls) -> 'GameStateData':
        return cls()

    def frozen(self) -> 'GameStateData':
        # TODO: make immutable
        return self


game_state_changed_signal = Signal('game state changed', state=GameStateData)
game_state_set_signal = Signal('game state set', state=GameStateData)
mutation_registry: plugins_helpers.RoutingSwitchRegistry[
    Callable[[Event, GameStateData], None],
    None
] = plugins_helpers.RoutingSwitchRegistry()


class GameStatePlugin(BasePlugin):
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
        with self._state_lock:
            list(mutation_registry.execute_silently(event.name, event=event, state=self._state))
            changed = self._state.is_changed
            self._state.reset_changed()

        return changed


def get_gamestate() -> GameStateData:
    gamestate = inject.instance(GameStatePlugin)
    return gamestate.state


@mutation_registry.register('Commander')
def commander_event(event: Event, state: GameStateData):
    data: dict = collections.defaultdict(lambda: state.__sentinel__, event.data)

    state.commander.name = data['Name']
    state.commander.frontier_id = data['FID']


@mutation_registry.register('Materials')
def materials_event(event: Event, state: GameStateData):
    for category in ['Raw', 'Encoded', 'Manufactured']:
        for material_data in event.data.get(category, []):  # type: ignore
            if {'Name', 'Count'}.issubset(set(material_data.keys())):
                state.material_storage += entities.Material(material_data['Name'], material_data['Count'], category)


@mutation_registry.register('LoadGame')
def load_game_event(event: Event, state: GameStateData):
    data: dict = collections.defaultdict(lambda: state.__sentinel__, event.data)

    state.commander.name = data['Commander']
    state.commander.frontier_id = data['FID']

    state.ship.model = data['Ship']
    state.ship.id = data['ShipID']
    state.ship.name = data['ShipName']
    state.ship.ident = data['ShipIdent']

    state.credits = data['Credits']

    state.horizons = data['Horizons']

    state.solo = data.get('GameMode', 'Solo') == 'Solo'


@mutation_registry.register('Rank')
def rank_event(event: Event, state: GameStateData):
    data: dict = collections.defaultdict(lambda: state.__sentinel__, event.data)

    state.rank.combat = data['Combat']
    state.rank.trade = data['Trade']
    state.rank.explore = data['Explore']
    state.rank.empire = data['Empire']
    state.rank.federation = data['Federation']
    state.rank.cqc = data['CQC']


@mutation_registry.register('Progress')
def progress_event(event: Event, state: GameStateData):
    data: dict = collections.defaultdict(lambda: state.__sentinel__, event.data)

    state.rank.combat_progres = data['Combat']
    state.rank.trade_progres = data['Trade']
    state.rank.explore_progres = data['Explore']
    state.rank.empire_progres = data['Empire']
    state.rank.federation_progres = data['Federation']
    state.rank.cqc_progres = data['CQC']


@mutation_registry.register('Reputation')
def reputation_event(event: Event, state: GameStateData):
    data: dict = collections.defaultdict(lambda: state.__sentinel__, event.data)

    state.reputation.federation = data['Federation']
    state.reputation.empire = data['Empire']
    state.reputation.alliance = data['Alliance']


@mutation_registry.register('EngineerProgress')
def engineer_progress_event(event: Event, state: GameStateData):
    create_engineer = lambda e: entities.Engineer(
        name=e['Engineer'],
        id=e['EngineerID'],
        progress=e['Progress'],
        rank=e.get('Rank', None),
        rank_progress=e.get('RankProgress', None)
    )

    state.engineers = {e['EngineerID']: create_engineer(e)
                       for e in event.data.get('Engineers', [])  # type: ignore
                       if 'EngineerID' in e and 'Engineer' in e and 'Progress' in e}


@mutation_registry.register('Loadout')
def loadout_event(event: Event, state: GameStateData):
    data: dict = collections.defaultdict(lambda: state.__sentinel__, event.data)

    state.ship.model = data['Ship']
    state.ship.id = data['ShipID']
    state.ship.name = data['ShipName']
    state.ship.ident = data['ShipIdent']

    # TODO: Store hull value, modules, rebuy


@mutation_registry.register('Location', 'FSDJump')
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


@mutation_registry.register('Docked')
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


@mutation_registry.register('Undocked')
def undocked_event(event: Event, state: GameStateData):
    state.location.docked = False
    state.location.station.clear()


@mutation_registry.register('Cargo')
def cargo_event(event: Event, state: GameStateData):
    pass
    # TODO: Cargo


@mutation_registry.register('MaterialCollected')
def material_collected_event(event: Event, state: GameStateData):
    if not {'Category', 'Name', 'Count'}.issubset(event.data.keys()):
        return

    category: str = str(event.data['Category'])
    name: str = str(event.data['Name'])
    count = int(event.data['Count'])  # type: ignore

    state.material_storage += entities.Material(name, count, category)


@mutation_registry.register('SupercruiseEntry')
def supercruise_entry_event(event: Event, state: GameStateData):
    state.location.supercruise = True


@mutation_registry.register('SupercruiseExit')
def supercruise_exit_event(event: Event, state: GameStateData):
    state.location.supercruise = False


@mutation_registry.register('MaterialDiscarded')
def material_discarded_event(event: Event, state: GameStateData):
    if not {'Category', 'Name', 'Count'}.issubset(event.data.keys()):
        return

    category: str = str(event.data['Category'])
    name: str = str(event.data['Name'])
    count = int(event.data['Count'])  # type: ignore

    state.material_storage -= entities.Material(name, count, category)


@mutation_registry.register('Synthesis')
def synthesis_event(event: Event, state: GameStateData):
    for material in event.data.get('Materials', []):
        for category in ['Raw', 'Encoded', 'Manufactured']:
            if material['Name'] in state.material_storage[category]:
                state.material_storage -= entities.Material(material['Name'], material['Count'], category)


@mutation_registry.register('MissionCompleted')
def on_mission_completed_event(event: Event, state: GameStateData):
    for material in event.data.get('MaterialsReward', []):
        state.material_storage += entities.Material(material['Name'], material['Count'], material['Category'])


@mutation_registry.register('MaterialTrade')
def on_material_trade_event(event: Event, state: GameStateData):
    paid = event.data['Paid']
    received = event.data['Received']
    state.material_storage -= entities.Material(paid['Material'], paid['Quantity'], paid['Category'])
    state.material_storage += entities.Material(received['Material'], received['Quantity'], received['Category'])


@mutation_registry.register('MaterialDiscarded')
def on_material_discarded_event(event: Event, state: GameStateData):
    state.material_storage -= entities.Material(event.data['Name'], event.data['Count'], event.data['Category'])


@mutation_registry.register('EngineerCraft')
def on_engineer_craft_event(event: Event, state: GameStateData):
    for material in event.data.get('Ingredients', []):
        for category in ['Raw', 'Encoded', 'Manufactured']:
            if material['Name'] in state.material_storage[category]:
                state.material_storage -= entities.Material(material['Name'], material['Count'], category)


@mutation_registry.register('FileHeader')
def on_fileheader_event(event: Event, state: GameStateData):
    state.running = True

    gameversion = event.data.get('gameversion', 'unknown')
    build = event.data.get('build', 'unknown')
    state.version = VersionInfo(gameversion, build)


@mutation_registry.register('Shutdown')
def on_shutdown_event(event: Event, state: GameStateData):
    state.running = False
