# https://www.edsm.net/en/api-journal-v1#collapse-events
import collections
import logging
from typing import Callable, Any, Dict, List

from edp import entities
from edp.contrib.gamestate import GameStateData
from edp.journal import Event

GAME_STATE_MUTATIONS: Dict[str, List[Callable[[Event, GameStateData], None]]] = collections.defaultdict(list)

logger = logging.getLogger(__name__)


def mutation(*events: str):
    def decor(func: Callable[[Event, GameStateData], Any]):
        # TODO: Verify signature
        for event in events:
            mutation_list = GAME_STATE_MUTATIONS[event]
            if func in mutation_list:
                logger.warning('Mutation for event %s already registered: %s', event, func)
            mutation_list.append(func)
        return func

    return decor


def mutate(event: Event, state: GameStateData):
    if event.name not in GAME_STATE_MUTATIONS:
        return

    for func in GAME_STATE_MUTATIONS[event.name]:
        try:
            print(event.name, func)
            func(event, state)
        except:
            logger.exception('Failed to apply mutation for event %s: %s', event.name, func)
            logger.debug('Event: %s', event.raw)
            logger.debug('GameStateData: %s', state)


@mutation('Commander')
def commander_event(event: Event, state: GameStateData):
    data: dict = collections.defaultdict(lambda: state.__sentinel__, event.data)

    state.commander.name = data['Name']
    state.commander.frontier_id = data['FID']


@mutation('Materials')
def materials_event(event: Event, state: GameStateData):
    get_materials = lambda t: {m['Name']: entities.Material(m['Name'], m['Count'])
                               for m in event.data.get(t, [])  # type: ignore
                               if 'Name' in m and 'Count' in m}

    state.material_storage.raw = get_materials('Raw')
    state.material_storage.encoded = get_materials('Encoded')
    state.material_storage.manufactured = get_materials('Manufactured')


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

    state.engineers = {e['EngineerID']: create_engineer(e)
                       for e in event.data.get('Engineers', [])  # type: ignore
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
    elif name and count is not None:
        material_category[name] = entities.Material(name, count)


@mutation('SupercruiseEntry')
def supercruise_entry_event(event: Event, state: GameStateData):
    state.location.supercruise = True


@mutation('SupercruiseExit')
def supercruise_exit_event(event: Event, state: GameStateData):
    state.location.supercruise = False
