"""
EDDN integration plugin

Supported schemas:

- outfitting-v2.0
- shipyard-v2.0
- commodity-v3.0
- journal-v1.0


Connects to CAPI signals to receive its information.
"""
import datetime
import itertools
import logging
import re
from typing import List, Dict, Tuple, Any, Union

import dataclasses
import requests

from edp import config, journal, utils, plugins
from edp.contrib import capi
from edp.contrib.gamestate import get_gamestate, GameStateData, game_state_set_signal
from edp.gui.forms.settings_window import VLayoutTab
from edp.plugins import BasePlugin
from edp.settings import BaseSettings
from edp.utils.plugins_helpers import BufferedEventsMixin

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class SchemaHeader:
    """Schema header container"""
    uploaderID: str
    softwareName: str = config.APPNAME_LONG
    softwareVersion: str = config.VERSION


class _SchemaMessage:
    """Base schema message. For typing."""


@dataclasses.dataclass
class EDDNSchema:
    """Root eddn schema container"""
    header: SchemaHeader
    message: _SchemaMessage
    schemaRef: str

    def to_dict(self) -> Dict:
        """Convert dataclass schema to dictionary suitable for eddn api"""
        payload_dict = dataclasses.asdict(self)
        payload_dict['$schemaRef'] = payload_dict.pop('schemaRef')
        message_dict = payload_dict.pop('message')
        optional = message_dict.pop('optional', {})
        payload_dict['message'] = optional
        payload_dict['message'].update(message_dict)
        return payload_dict


# https://github.com/EDSM-NET/EDDN/blob/master/schemas/blackmarket-v1.0.json
@dataclasses.dataclass
class BlackmarketMessageSchema(_SchemaMessage):
    """Blackmarket schema container"""
    systemName: str
    stationName: str
    marketId: int
    timestamp: str
    name: str
    sellPrice: int
    prohibited: bool


# https://github.com/EDSM-NET/EDDN/blob/master/schemas/outfitting-v2.0.json
@dataclasses.dataclass
class OutfittingMessageSchema(_SchemaMessage):
    """Outfitting schema container"""
    systemName: str
    stationName: str
    marketId: int
    horizons: bool
    timestamp: str
    modules: List[str]


# https://github.com/EDSM-NET/EDDN/blob/master/schemas/shipyard-v2.0.json
@dataclasses.dataclass
class ShipyardMessageSchema(_SchemaMessage):
    """Shipyard schema container"""
    systemName: str
    stationName: str
    marketId: int
    horizons: bool
    timestamp: str
    ships: List[str]


# https://github.com/EDSM-NET/EDDN/blob/master/schemas/commodity-v3.0.json
@dataclasses.dataclass
class CommodityMessageSchema(_SchemaMessage):
    """Commodity schema container"""
    systemName: str
    stationName: str
    marketId: int
    horizons: bool
    timestamp: str
    commodities: List[Dict[str, Any]]
    economies: List[Dict[str, Any]]
    optional: Dict


# https://github.com/EDSM-NET/EDDN/blob/master/schemas/journal-v1.0.json
@dataclasses.dataclass
class JournalMessageSchema(_SchemaMessage):
    """Journal schema container"""
    timestamp: str
    event: str
    StarSystem: str
    StarPos: Tuple[float, float, float]
    SystemAddress: int
    Factions: List[Dict]
    optional: Dict


class EDDNSettings(BaseSettings):
    """EDDN plugin settings"""
    enabled: bool = True


class EDDNSettingsTabWidget(VLayoutTab):  # pragma: no cover
    """Eddn plugin settings widget"""
    friendly_name = 'EDDN'

    def get_settings_links(self):
        settings = EDDNSettings.get_insance()

        yield self.link_checkbox(settings, 'enabled', 'Enabled')


class EDDNPlugin(BufferedEventsMixin, BasePlugin):
    """EDDN plugin"""

    def __init__(self):
        super(EDDNPlugin, self).__init__()

        self.settings = EDDNSettings.get_insance()
        self._session = requests.Session()
        self._session.headers['User-Agent'] = config.USERAGENT
        self._starpos_db: Dict[int, Tuple[float, float, float]] = {}  # SystemAddress to StarPos

    def is_enalbed(self):
        return self.settings.enabled

    def filter_event(self, event: journal.Event) -> bool:
        return event.name in {'Docked', 'FSDJump', 'Scan', 'Location'}

    @plugins.bind_signal(game_state_set_signal)
    def bootstrap_starpos_db(self, state: GameStateData):
        if state.location.pos:
            self._starpos_db[state.location.address] = state.location.pos

    def process_buffered_events(self, events: List[journal.Event]):
        gamestate = get_gamestate()
        for event in events:
            try:
                eddn_payload = self.process_event(event, gamestate)
                eddn_payload_dict = eddn_payload.to_dict()
                self.send_payload(eddn_payload_dict)
            except:
                logger.exception(f'Failed to process event: {event.raw}')

    # pylint: disable=no-self-use
    def process_event(self, event: journal.Event, state: GameStateData) -> EDDNSchema:
        """
        Process journal events into journal message
        """
        strip_localized = lambda d: utils.dict_subset(d, *(k for k in d.keys() if not k.endswith('_Localised')))
        filter_faction = lambda d: strip_localized(utils.drop_keys(
            d, 'HappiestSystem', 'HomeSystem', 'MyReputation', 'SquadronFaction'
        ))

        optional = utils.drop_keys(event.data, "ActiveFine", "CockpitBreach", "BoostUsed",
                                   "FuelLevel", "FuelUsed", "JumpDist", "Latitude", "Longitude", "Wanted")
        optional = strip_localized(optional)
        if 'StationEconomies' in optional:
            optional['StationEconomies'] = [strip_localized(d) for d in optional['StationEconomies']]

        if utils.has_keys(event.data, 'StarPos', 'SystemAddress'):
            self._starpos_db[event.data['SystemAddress']] = event.data['StarPos']

        star_system = event.data.get('StarSystem', None) or state.location.system
        system_address = event.data.get('SystemAddress', None) or state.location.address
        star_pos = event.data.get('StarPos', None) or self._starpos_db.get(system_address or 0, None) \
                   or state.location.pos

        if not star_system or not star_pos or not system_address:
            raise ValueError('Got falsy StarPos or StarSystem or SystemAddress')

        message = JournalMessageSchema(
            timestamp=utils.to_ed_timestamp(event.timestamp),
            event=event.name,
            StarSystem=star_system,
            StarPos=star_pos,
            SystemAddress=system_address,
            Factions=[filter_faction(f) for f in event.data.get('Factions', [])],
            optional=optional
        )

        payload_dataclass = EDDNSchema(
            header=SchemaHeader(
                uploaderID=state.commander.name or 'unknown',
            ),
            schemaRef='https://eddn.edcd.io/schemas/journal/1',
            message=message
        )

        return payload_dataclass

    def send_payload(self, payload: Dict):
        """Send data to eddn"""
        logger.debug(f'Sending message to EDDN: {payload["$schemaRef"]}')
        response = self._session.post('https://eddn.edcd.io:4430/upload/', json=payload)
        if response.status_code >= 400:
            logger.error(f'Error sending message to EDDN, status code is {response.status_code}: '
                         f'{response.text} :: {payload}')
        return response

    @plugins.bind_signal(capi.shipyard_info_signal)
    def on_capi_shipyard_info_outfitting(self, data: dict):
        """Send outfitting eddn message from CAPI shipyard information"""
        gamestate = get_gamestate()

        if not gamestate.location.system or not gamestate.location.station.name \
                or not gamestate.location.station.market:
            logger.warning('System and station info not set in gamestate')
            return

        modules: List[str] = []

        for module in data.get('modules', {}).values():
            name = module.get('name', None)
            sku = module.get('sku', None)
            if name and (not sku or sku == 'ELITE_HORIZONS_V_PLANETARY_LANDINGS'):
                if re.match('(^Hpt_|^Int_|_Armour_)', name) and name != 'Int_PlanetApproachSuite':
                    modules.append(name)

        message = OutfittingMessageSchema(
            systemName=gamestate.location.system,
            stationName=gamestate.location.station.name,
            marketId=gamestate.location.station.market,
            horizons=gamestate.horizons,
            timestamp=datetime.datetime.utcnow().isoformat(timespec='seconds') + 'Z',
            modules=modules,
        )

        payload_dataclass = EDDNSchema(
            header=SchemaHeader(
                uploaderID=gamestate.commander.name or 'unknown',
            ),
            schemaRef='https://eddn.edcd.io/schemas/outfitting/2',
            message=message
        )

        response = self.send_payload(payload_dataclass.to_dict())
        if 400 <= response.status_code < 500:
            logger.error(data)

    @plugins.bind_signal(capi.shipyard_info_signal)
    def on_capi_shipyard_info_shipyard(self, data: dict):
        """Send shipyard eddn message from CAPI shipyard information"""
        gamestate = get_gamestate()

        if not gamestate.location.system or not gamestate.location.station.name \
                or not gamestate.location.station.market:
            logger.warning('System and station info not set in gamestate')
            return

        ships: List[str] = []

        shipyard_list: Dict[str, Dict[str, Any]] = data.get('ships', {}).get('shipyard_list', {})
        unavailable_list: List[Dict[str, Any]] = data.get('ships', {}).get('unavailable_list', [])

        for ship in itertools.chain(shipyard_list.values(), unavailable_list):
            name = ship.get('name', None)
            if name:
                ships.append(name)

        if not ships:
            logger.error('No ships were parsed from cApi data for shipyard v2 EDDN schema')
            logger.debug(data)
            return

        message = ShipyardMessageSchema(
            systemName=gamestate.location.system,
            stationName=gamestate.location.station.name,
            marketId=gamestate.location.station.market,
            horizons=gamestate.horizons,
            timestamp=datetime.datetime.utcnow().isoformat(timespec='seconds') + 'Z',
            ships=ships,
        )

        payload_dataclass = EDDNSchema(
            header=SchemaHeader(
                uploaderID=gamestate.commander.name or 'unknown',
            ),
            schemaRef='https://eddn.edcd.io/schemas/shipyard/2',
            message=message
        )

        response = self.send_payload(payload_dataclass.to_dict())
        if 400 <= response.status_code < 500:
            logger.error(data)

    # pylint: disable=too-many-locals
    @plugins.bind_signal(capi.market_info_signal)
    def on_capi_market_info_commodities(self, data: dict):
        """Send commodities eddn message from CAPI market information"""
        gamestate = get_gamestate()

        if not gamestate.location.system or not gamestate.location.station.name \
                or not gamestate.location.station.market:
            logger.warning('System and station info not set in gamestate')
            return

        commodities: List[Dict[str, Any]] = []
        economies: List[Dict[str, Any]] = []

        required_fields = ['name', 'meanPrice', 'buyPrice', 'stock', 'stockBracket', 'sellPrice', 'demand',
                           'demandBracket']

        for commodity in data.get('commodities', []):
            if not utils.has_keys(commodity, *required_fields) or not commodity.get('name') \
                    or commodity.get('legality') or commodity.get('categoryname') == 'NonMarketable':
                continue

            commodity_data = utils.dict_subset(commodity, *required_fields)

            status_flags: List[Union[int, str]] = list(set(filter(None, commodity.get('statusFlags', []))))
            if status_flags:
                commodity_data['statusFlags'] = status_flags

            commodities.append(commodity_data)

        for economy in data.get('economies', {}).values():
            name = economy.get('name')
            proportion = economy.get('proportion')
            if name and proportion is not None:
                economies.append({'name': name, 'proportion': proportion})

        prohibited = {p for p in data.get('prohibited', {}).values() if p}

        optional = {}
        if prohibited:
            optional['prohibited'] = list(prohibited)

        message = CommodityMessageSchema(
            systemName=gamestate.location.system,
            stationName=gamestate.location.station.name,
            marketId=gamestate.location.station.market,
            horizons=gamestate.horizons,
            timestamp=datetime.datetime.utcnow().isoformat(timespec='seconds') + 'Z',
            commodities=commodities,
            economies=economies,
            optional=optional
        )

        payload_dataclass = EDDNSchema(
            header=SchemaHeader(
                uploaderID=gamestate.commander.name or 'unknown',
            ),
            schemaRef='https://eddn.edcd.io/schemas/commodity/3',
            message=message
        )

        response = self.send_payload(payload_dataclass.to_dict())
        if 400 <= response.status_code < 500:
            logger.error(data)

    def get_settings_widget(self):
        return EDDNSettingsTabWidget()
