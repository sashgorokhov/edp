import logging
from typing import List, Dict, Tuple

import dataclasses
import requests
from PyQt5 import QtWidgets, QtCore

from edp import config, journal, utils
from edp.contrib.gamestate import get_gamestate, GameStateData
from edp.gui.forms.settings_window import VLayoutTab
from edp.plugins import BasePlugin
from edp.settings import BaseSettings
from edp.utils.plugins_helpers import BufferedEventsMixin

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class SchemaHeader:
    uploaderID: str
    softwareName: str = config.APPNAME_LONG
    softwareVersion: str = config.VERSION


class _SchemaMessage:
    pass


@dataclasses.dataclass
class EDDNSchema:
    header: SchemaHeader
    message: _SchemaMessage
    schemaRef: str

    def to_dict(self) -> Dict:
        payload_dict = dataclasses.asdict(self)
        payload_dict['$schemaRef'] = payload_dict.pop('schemaRef')
        message_dict = payload_dict.pop('message')
        optional = message_dict.pop('optional', {})
        payload_dict['message'] = {**message_dict, **optional}
        return payload_dict


# https://github.com/EDSM-NET/EDDN/blob/master/schemas/blackmarket-v1.0.json
@dataclasses.dataclass
class BlackmarketMessageSchema(_SchemaMessage):
    systemName: str
    stationName: str
    marketId: int
    timestamp: str
    name: str
    sellPrice: int
    prohibited: bool


# https://github.com/EDSM-NET/EDDN/blob/master/schemas/journal-v1.0.json
@dataclasses.dataclass
class JournalMessageSchema(_SchemaMessage):
    timestamp: str
    event: str
    StarSystem: str
    StarPos: Tuple[float, float, float]
    SystemAddress: int
    Factions: List[Dict]
    optional: Dict


class EDDNSettings(BaseSettings):
    enabled: bool = True


class EDDNSettingsTabWidget(VLayoutTab):  # pragma: no cover
    friendly_name = 'EDDN'

    def get_settings_links(self):
        settings = EDDNSettings.get_insance()

        layout = QtWidgets.QHBoxLayout()
        checkbox = QtWidgets.QCheckBox()
        checkbox.setText('Enabled')
        checkbox.stateChanged.connect(lambda state: settings.__setattr__('enabled', QtCore.Qt.Checked == state))
        checkbox.setChecked(settings.enabled)
        layout.addWidget(checkbox)
        layout.addStretch(1)
        yield layout


class EDDNPlugin(BufferedEventsMixin, BasePlugin):
    def __init__(self):
        super(EDDNPlugin, self).__init__()

        self.settings = EDDNSettings.get_insance()
        self._session = requests.Session()
        self._session.headers['User-Agent'] = config.USERAGENT

    def is_enalbed(self):
        return self.settings.enabled

    def filter_event(self, event: journal.Event) -> bool:
        return event.name in {'Docked', 'FSDJump', 'Scan', 'Location'}

    def process_buffered_events(self, events: List[journal.Event]):
        gamestate = get_gamestate()
        for event in events:
            try:
                eddn_payload = self.process_event(event, gamestate)
                eddn_payload_dict = eddn_payload.to_dict()
                self.send_payload(eddn_payload_dict)
            except:
                logger.exception(f'Failed to process event: {event.raw}')

    def process_event(self, event: journal.Event, state: GameStateData) -> EDDNSchema:
        strip_localized = lambda d: utils.subset(d, *(k for k in d.keys() if not k.endswith('_Localised')))
        drop_keys = lambda d, *keys: {k: v for k, v in d.items() if k not in keys}

        optional = drop_keys(event.data, "ActiveFine", "CockpitBreach", "BoostUsed",
                             "FuelLevel", "FuelUsed", "JumpDist", "Latitude", "Longitude", "Wanted")
        optional = strip_localized(optional)
        if 'StationEconomies' in optional:
            optional['StationEconomies'] = [strip_localized(d) for d in optional['StationEconomies']]

        message = JournalMessageSchema(
            timestamp=event.timestamp.isoformat(timespec='seconds') + 'Z',
            event=event.name,
            StarSystem=event.data.get('StarSystem', state.location.system),
            StarPos=event.data.get('StarPos', state.location.pos),
            SystemAddress=event.data.get('SystemAddress', state.location.address),
            Factions=[strip_localized(f) for f in event.data.get('Factions', [])],
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
        logger.debug(f'Sending message to EDDN: {payload["$schemaRef"]}')
        response = self._session.post('https://eddn.edcd.io:4430/upload/', json=payload)
        if response.status_code >= 400:
            logger.error(f'Error sending message to EDDN, status code is: {response.status_code}')
            logger.error(f'Response text: {response.text}')
            logger.error(f'Payload: {payload}')

    def get_settings_widget(self):
        return EDDNSettingsTabWidget()
