"""
Plugin for recording current game state

Defines GameStateData which holds actual state.

http://hosting.zaonce.net/community/journal/v18/Journal_Manual_v18.pdf
"""
import collections
import copy
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
class GameStateData(entities.BaseEntity):
    """Game state data container"""
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
        """Return clear container instance"""
        return cls()


game_state_changed_signal = Signal('game state changed', state=GameStateData)
game_state_set_signal = Signal('game state set', state=GameStateData)

mutation_registry: plugins_helpers.RoutingSwitchRegistry[
    Callable[[Event, GameStateData], None],
    None
] = plugins_helpers.RoutingSwitchRegistry()


class GameStatePlugin(BasePlugin):
    """Gamestate plugin. Changes gamestate with journal events"""
    journal_reader: JournalReader = inject.attr(JournalReader)

    def __init__(self):
        self._state = GameStateData.get_clear_data()
        self._state_lock = threading.Lock()

        journal_event_signal.bind(self.on_journal_event)
        signals.init_complete.bind(self.set_initial_state)

    def get_settings_widget(self):
        return None

    @property
    def state(self) -> GameStateData:
        """Return puglic GameStateData instance"""
        return copy.deepcopy(self._state)

    def on_journal_event(self, event: Event):
        """
        Update state with journal event

        Emits game_state_changed_signal is state is changed
        """
        changed = self.update_state(event)
        if changed:
            game_state_changed_signal.emit(state=self.state)

    def set_initial_state(self):
        """
        Load last journal file events and process them to set initial state

        Emits game_state_set_signal with initial state
        """
        events: List[Event] = self.journal_reader.get_latest_file_events()

        for event in events:
            self.update_state(event)

        game_state_set_signal.emit(state=self.state)
        logger.debug('Initial state: %s', self._state)

    def update_state(self, event: Event) -> bool:
        """Update current state with journal event"""
        with self._state_lock:
            list(mutation_registry.execute_silently(event.name, event=event, state=self._state))
            changed = self._state.is_changed
            self._state.reset_changed()

        return changed


def get_gamestate() -> GameStateData:
    """Quick shortcut function to receive GameStateData"""
    gamestate = inject.instance(GameStatePlugin)
    return gamestate.state


@mutation_registry.register('Commander')
def commander_event(event: Event, state: GameStateData):
    """
    Handle Commander journal event

    Sets commander name and frontier id
    """
    data: dict = collections.defaultdict(lambda: state.__sentinel__, event.data)

    state.commander.name = data['Name']
    state.commander.frontier_id = data['FID']


@mutation_registry.register('Materials')
def materials_event(event: Event, state: GameStateData):
    """
    Handle Materials journal event

    Populates material storage
    """
    for category in ['Raw', 'Encoded', 'Manufactured']:
        for material_data in event.data.get(category, []):  # type: ignore
            if {'Name', 'Count'}.issubset(set(material_data.keys())):
                state.material_storage += entities.Material(material_data['Name'], material_data['Count'], category)


@mutation_registry.register('LoadGame')
def load_game_event(event: Event, state: GameStateData):
    """
    Handle LoadGame journal event

    Sets commander info, ship info, credits, horizons and game mode status
    """
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
    """
    Handle Rank journal event

    Sets player rank info
    """
    data: dict = collections.defaultdict(lambda: state.__sentinel__, event.data)

    state.rank.combat = data['Combat']
    state.rank.trade = data['Trade']
    state.rank.explore = data['Explore']
    state.rank.empire = data['Empire']
    state.rank.federation = data['Federation']
    state.rank.cqc = data['CQC']


@mutation_registry.register('Progress')
def progress_event(event: Event, state: GameStateData):
    """
    Handle Progress journal event

    Sets player rank progess
    """
    data: dict = collections.defaultdict(lambda: state.__sentinel__, event.data)

    state.rank.combat_progres = data['Combat']
    state.rank.trade_progres = data['Trade']
    state.rank.explore_progres = data['Explore']
    state.rank.empire_progres = data['Empire']
    state.rank.federation_progres = data['Federation']
    state.rank.cqc_progres = data['CQC']


@mutation_registry.register('Reputation')
def reputation_event(event: Event, state: GameStateData):
    """
    Handle Reputation journal event

    Sets player reputation in general powers
    """
    data: dict = collections.defaultdict(lambda: state.__sentinel__, event.data)

    state.reputation.federation = data['Federation']
    state.reputation.empire = data['Empire']
    state.reputation.alliance = data['Alliance']


@mutation_registry.register('EngineerProgress')
def engineer_progress_event(event: Event, state: GameStateData):
    """
    Handle Reputation journal event

    Sets player engineer progress information
    """
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
    """
    Handle Loadout journal event

    Sets ship information
    """
    data: dict = collections.defaultdict(lambda: state.__sentinel__, event.data)

    state.ship.model = data['Ship']
    state.ship.id = data['ShipID']
    state.ship.name = data['ShipName']
    state.ship.ident = data['ShipIdent']

    # Store hull value, modules, rebuy


@mutation_registry.register('Location', 'FSDJump')
def location_event(event: Event, state: GameStateData):
    """
    Handle Location and FSDJump journal events

    Sets current player location and updates supercruise status
    """
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

    # Store location factions


@mutation_registry.register('Docked')
def docked_event(event: Event, state: GameStateData):
    """
    Handle Docked journal event

    Sets current player location station and updates docked status
    """
    data: dict = collections.defaultdict(lambda: state.__sentinel__, event.data)

    state.location.docked = True
    state.location.station.name = data['StationName']
    state.location.station.type = data['StationType']
    state.location.station.market = data['MarketID']
    state.location.station.faction = data['StationFaction']
    state.location.station.government = data['StationGovernment']
    state.location.station.services = data['StationServices']
    state.location.station.economy = data['StationEconomy']


# pylint: disable=unused-argument
@mutation_registry.register('Undocked')
def undocked_event(event: Event, state: GameStateData):
    """
    Handle Undocked journal event

    Sets clears station info and updates docked status
    """
    state.location.docked = False
    state.location.station.clear()


@mutation_registry.register('MaterialCollected')
def material_collected_event(event: Event, state: GameStateData):
    """
    Handle MaterialCollected journal event

    Updates material count in material storage
    """
    if not {'Category', 'Name', 'Count'}.issubset(event.data.keys()):
        return

    category: str = str(event.data['Category'])
    name: str = str(event.data['Name'])
    count = int(event.data['Count'])  # type: ignore

    state.material_storage += entities.Material(name, count, category)


# pylint: disable=unused-argument
@mutation_registry.register('SupercruiseEntry')
def supercruise_entry_event(event: Event, state: GameStateData):
    """
    Handle SupercruiseEntry journal event

    Updates supercruise status
    """
    state.location.supercruise = True


# pylint: disable=unused-argument
@mutation_registry.register('SupercruiseExit')
def supercruise_exit_event(event: Event, state: GameStateData):
    """
    Handle SupercruiseExit journal event

    Updates supercruise status
    """
    state.location.supercruise = False


@mutation_registry.register('MaterialDiscarded')
def material_discarded_event(event: Event, state: GameStateData):
    """
    Handle MaterialDiscarded journal event

    Removes material from material storage
    """
    if not {'Category', 'Name', 'Count'}.issubset(event.data.keys()):
        return

    category: str = str(event.data['Category'])
    name: str = str(event.data['Name'])
    count = int(event.data['Count'])  # type: ignore

    state.material_storage -= entities.Material(name, count, category)


@mutation_registry.register('Synthesis')
def synthesis_event(event: Event, state: GameStateData):
    """
    Handle Synthesis journal event

    Removes materials from material storage
    """
    for material in event.data.get('Materials', []):
        for category in ['Raw', 'Encoded', 'Manufactured']:
            if material['Name'] in state.material_storage[category]:
                state.material_storage -= entities.Material(material['Name'], material['Count'], category)


@mutation_registry.register('MissionCompleted')
def on_mission_completed_event(event: Event, state: GameStateData):
    """
    Handle MissionCompleted journal event

    Adds materials to material storage if mission has materials rewards
    """
    for material in event.data.get('MaterialsReward', []):
        state.material_storage += entities.Material(material['Name'], material['Count'], material['Category'])


@mutation_registry.register('MaterialTrade')
def on_material_trade_event(event: Event, state: GameStateData):
    """
    Handle MaterialTrade journal event

    Removes paid materials and adds received materials to material storage
    """
    paid = event.data['Paid']
    received = event.data['Received']
    state.material_storage -= entities.Material(paid['Material'], paid['Quantity'], paid['Category'])
    state.material_storage += entities.Material(received['Material'], received['Quantity'], received['Category'])


@mutation_registry.register('MaterialDiscarded')
def on_material_discarded_event(event: Event, state: GameStateData):
    """
    Handle MaterialDiscarded journal event

    Removes material from material storage
    """
    state.material_storage -= entities.Material(event.data['Name'], event.data['Count'], event.data['Category'])


@mutation_registry.register('EngineerCraft')
def on_engineer_craft_event(event: Event, state: GameStateData):
    """
    Handle EngineerCraft journal event

    Removes materials from material storage
    """
    for material in event.data.get('Ingredients', []):
        for category in ['Raw', 'Encoded', 'Manufactured']:
            if material['Name'] in state.material_storage[category]:
                state.material_storage -= entities.Material(material['Name'], material['Count'], category)


@mutation_registry.register('FileHeader')
def on_fileheader_event(event: Event, state: GameStateData):
    """
    Handle FileHeader journal event

    Updates running status and sets game version information
    """
    state.running = True

    gameversion = event.data.get('gameversion', 'unknown')
    build = event.data.get('build', 'unknown')
    state.version = VersionInfo(gameversion, build)


# pylint: disable=unused-argument
@mutation_registry.register('Shutdown')
def on_shutdown_event(event: Event, state: GameStateData):
    """
    Handle Shutdown journal event

    Updates running status
    """
    state.running = False
