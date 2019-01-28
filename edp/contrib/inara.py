import functools
import itertools
import logging
from typing import List, Any, Optional, Callable, Union, Dict

import dataclasses
import inject
import requests
from PyQt5 import QtWebEngineWidgets, QtCore, QtWebEngineCore, QtNetwork

from edp import journal, config, plugins
from edp.contrib import gamestate
from edp.gui.forms.settings_window import VLayoutTab
from edp.settings import BaseSettings
from edp.utils import subset, has_keys
from edp.utils.plugins_helpers import BufferedEventsMixin, RoutingSwitchRegistry

logger = logging.getLogger(__name__)

# Define registry for event processors.
_RT = Union['InaraEvent', List['InaraEvent']]  # callback return type
processor_registry: RoutingSwitchRegistry[Callable[[journal.Event], _RT], _RT] = RoutingSwitchRegistry()


class InaraSettings(BaseSettings):
    enabled: bool = True
    api_key: Optional[str] = None
    cookies: Dict[str, Any] = {}


@dataclasses.dataclass()
class InaraEvent:
    eventName: str
    eventTimestamp: str
    eventData: Any


def _qbytearray_to_str(value: QtCore.QByteArray) -> str:
    s = QtCore.QTextStream(value)
    return s.readAll()


class InaraWebLoginWindow(QtWebEngineWidgets.QWebEngineView):
    LOGIN_URL = 'https://inara.cz/login/'
    SUCCESS_URL = 'https://inara.cz/intro/'

    login_successful = QtCore.pyqtSignal(dict)

    def __init__(self):
        super(InaraWebLoginWindow, self).__init__()
        self.setWindowTitle('Inara login window')

        self.urlChanged.connect(self.on_url_changed)
        page: QtWebEngineWidgets.QWebEnginePage = self.page()
        profile: QtWebEngineWidgets.QWebEngineProfile = page.profile()
        cookie_store: QtWebEngineCore.QWebEngineCookieStore = profile.cookieStore()
        cookie_store.cookieAdded.connect(self.on_cookie_added)
        self._cookies = {}

    def show(self):
        self.load(QtCore.QUrl(self.LOGIN_URL))
        super(InaraWebLoginWindow, self).show()

    def on_cookie_added(self, cookie: QtNetwork.QNetworkCookie):
        try:
            self._cookies[_qbytearray_to_str(cookie.name())] = _qbytearray_to_str(cookie.value())
        except:
            logger.exception(f'Failed to set cookie: {cookie.name()}={cookie.value()}')

    def on_url_changed(self, url: QtCore.QUrl):
        if url.toString() == self.SUCCESS_URL:
            self.login_successful.emit(self._cookies)
            self._cookies = {}
            self.close()


class InaraSettingsTabWidget(VLayoutTab):
    friendly_name = 'Inara'

    def __init__(self):
        self.settings = InaraSettings.get_insance()
        super(InaraSettingsTabWidget, self).__init__()
        self.login_window = InaraWebLoginWindow()
        self.login_window.login_successful.connect(self.on_login_cookies_set)

    def get_settings_links(self):
        yield self.link_checkbox(self.settings, 'enabled', 'Enabled')
        yield self.link_line_edit(self.settings, 'api_key', 'Api key')

        # layout = QtWidgets.QHBoxLayout()
        # button = QtWidgets.QPushButton('Login' if not self.settings.cookies else 'Login [already logged in]')
        # button.clicked.connect(lambda: self.login_window.show())
        # layout.addWidget(button)
        # layout.addStretch(1)
        # yield layout

    def on_login_cookies_set(self, cookies: dict):
        self.settings.cookies.update(cookies)


class InaraApi:
    def __init__(self, api_key):
        self._session = requests.Session()
        self._api_key = api_key

    def send(self, *events: InaraEvent, commander_name: str, frontier_id: str):
        events_dicts = list(map(dataclasses.asdict, events))

        response = self._session.post('https://inara.cz/inapi/v1/', timeout=15, json={
            'header': {
                'appName': config.APPNAME_LONG,
                'appVersion': config.VERSION,
                'isDeveloped': True,
                'APIkey': self._api_key,
                'commanderName': commander_name,
                'commanderFrontierID': frontier_id,
            },
            'events': events_dicts
        })
        return response.json()


class InaraWebApi:
    def __init__(self):
        settings = InaraSettings.get_insance()

        self._session = requests.Session()
        self._session.cookies.update(settings.cookies)


class InaraPlugin(BufferedEventsMixin, plugins.BasePlugin):
    friendly_name = 'Inara'
    journal_reader: journal.JournalReader = inject.attr(journal.JournalReader)

    def __init__(self):
        super(InaraPlugin, self).__init__()

        self.settings = InaraSettings.get_insance()

    def get_settings_widget(self):
        return InaraSettingsTabWidget()

    def is_enalbed(self):
        return bool(self.settings.api_key and self.settings.enabled)

    @functools.lru_cache()
    def api(self):
        return InaraApi(self.settings.api_key)

    @plugins.bind_signal(gamestate.game_state_set_signal)
    def gamestate_data_set(self, state: gamestate.GameStateData):
        latest_file_events = self.journal_reader.get_latest_file_events()
        filtered_events: List[journal.Event] = []
        for event in latest_file_events:
            if event.name in {'Commander', 'Materials', 'LoadGame', 'Rank', 'Progress', 'Reputation',
                              'EngineerProgress', 'Loadout', 'Location'}:
                filtered_events.append(event)
        self.process_buffered_events(filtered_events)

    def process_buffered_events(self, events: List[journal.Event]):
        inara_events: List[InaraEvent] = []
        state = gamestate.get_gamestate()

        for event in events:
            try:
                inara_events.extend(self.process_event(event) or [])
            except:
                logger.exception(f'Error processing event: {event.raw}')

        if not inara_events:
            return

        try:
            response = self.api().send(
                *inara_events,
                commander_name=state.commander.name or 'unknown',
                frontier_id=state.commander.frontier_id or 'unknown'
            )
        except:
            logger.exception('Error sending events to inara')
            logger.error(inara_events)
            return

        logger.debug('Sent %s events to inara', len(inara_events))
        for jevent, resp in zip(inara_events, response['events']):
            if resp['eventStatus'] == 400:
                logger.error(f'Error {resp} for {jevent}')
            elif resp['eventStatus'] == 204:
                logger.warning(f'Soft error {resp} for {jevent}')

    def process_event(self, event: journal.Event) -> List[InaraEvent]:
        result = processor_registry.execute_silently(event.name, event=event)
        if result is None:
            return []
        if isinstance(result, list):
            return result
        if isinstance(result, InaraEvent):
            return [result]


@processor_registry.register('Docked')
def on_docked_event(event: journal.Event) -> InaraEvent:
    return InaraEvent(
        eventName='addCommanderTravelDock',
        eventTimestamp=event.data['timestamp'],
        eventData={
            'starsystemName': event.data['StarSystem'],
            'stationName': event.data['StationName'],
            'marketID': event.data['MarketID']
        }
    )


@processor_registry.register('FSDJump')
def on_fsdjump_event(event: journal.Event) -> InaraEvent:
    return InaraEvent(
        eventName='addCommanderTravelFSDJump',
        eventTimestamp=event.data['timestamp'],
        eventData={
            'starsystemName': event.data['StarSystem'],
            'jumpDistance': event.data['JumpDist']
        }
    )


@processor_registry.register('Statistics')
def on_statistict_event(event: journal.Event) -> InaraEvent:
    return InaraEvent(
        eventName='setCommanderGameStatistics',
        eventTimestamp=event.data['timestamp'],
        eventData=subset(event.data, 'Combat', 'Bank_Account', 'Crime', 'Smuggling', 'Trading',
                         'Mining', 'Exploration', 'Passengers', 'Search_And_Rescue', 'Crafting',
                         'Crew', 'Multicrew')
    )


@processor_registry.register('Location')
def on_location_event(event: journal.Event) -> InaraEvent:
    data = {'starsystemName': event.data['StarSystem']}
    if 'StationName' in event.data:
        data['stationName'] = event.data['StationName']
        data['marketID'] = event.data['MarketID']
    return InaraEvent(
        eventName='setCommanderTravelLocation',
        eventTimestamp=event.data['timestamp'],
        eventData=data
    )


@processor_registry.register('EngineerProgress')
def on_engineer_progress_event(event: journal.Event) -> InaraEvent:
    return InaraEvent(
        eventName='setCommanderRankEngineer',
        eventTimestamp=event.data['timestamp'],
        eventData=[
            {'engineerName': e['Engineer'], 'rankStage': e['Progress'], 'rankValue': e.get('Rank', 0)}
            for e in event.data.get('Engineers', [])]
    )


@processor_registry.register('Reputation')
def on_reputation_event(event: journal.Event) -> InaraEvent:
    return InaraEvent(
        eventName='setCommanderReputationMajorFaction',
        eventTimestamp=event.data['timestamp'],
        eventData=[{'majorfactionName': k, 'majorfactionReputation': v / 100}
                   for k, v in subset(event.data, 'Empire', 'Federation', 'Alliance').items()]
    )


@processor_registry.register('Progress')
def on_progress_event(event: journal.Event) -> InaraEvent:
    rank_keys = ('Combat', 'Trade', 'Explore', 'Empire', 'Federation', 'CQC')

    return InaraEvent(
        eventName='setCommanderRankPilot',
        eventTimestamp=event.data['timestamp'],
        eventData=[{'rankName': k, 'rankProgress': v / 100}
                   for k, v in subset(event.data, *rank_keys).items()]
    )


@processor_registry.register('Rank')
def on_rank_event(event: journal.Event) -> InaraEvent:
    rank_keys = ('Combat', 'Trade', 'Explore', 'Empire', 'Federation', 'CQC')

    return InaraEvent(
        eventName='setCommanderRankPilot',
        eventTimestamp=event.data['timestamp'],
        eventData=[{'rankName': k, 'rankValue': v}
                   for k, v in subset(event.data, *rank_keys).items()]
    )


@processor_registry.register('Materials')
def on_materials_event(event: journal.Event) -> InaraEvent:
    materials = [{'itemName': m['Name'], 'itemCount': m['Count']}
                 for m in itertools.chain(*(event.data.get(cat, [])
                                            for cat in ['Raw', 'Encoded', 'Manufactured']))
                 if 'Name' in m and 'Count' in m]
    return InaraEvent(
        eventName='setCommanderInventoryMaterials',
        eventTimestamp=event.data['timestamp'],
        eventData=materials
    )


@processor_registry.register('LoadGame')
def on_loadgame_event(event: journal.Event) -> List[InaraEvent]:
    return [
        InaraEvent(
            eventName='setCommanderShip',
            eventTimestamp=event.data['timestamp'],
            eventData={
                'shipType': event.data['Ship'],
                'shipGameID': event.data['ShipID'],
                'shipName': event.data['ShipName'],
                'shipIdent': event.data['ShipIdent'],
                'isCurrentShip': True,
            }
        ),
        InaraEvent(
            eventName='setCommanderCredits',
            eventTimestamp=event.data['timestamp'],
            eventData={
                'commanderCredits': event.data['Credits']
            }
        )
    ]


@processor_registry.register('Loadout')
def on_loadout_event(event: journal.Event) -> List[InaraEvent]:
    modules = []

    for m in event.data.get('Modules', []):
        d = {
            "slotName": m['Slot'],
            "itemName": m['Item'],
            "itemValue": m['Value'],
            "itemHealth": m['Health'],
            "isOn": m['On'],
            "itemPriority": m['Priority'],
            "itemAmmoClip": m.get('AmmoInClip', 0),
            "itemAmmoHopper": m.get('AmmoInHopper', 0),
        }
        if 'AmmoInClip' in m:
            d['itemAmmoClip'] = m['AmmoInClip']
            d['itemAmmoHopper'] = m['AmmoInHopper']
        if 'Engineering' in m:
            e = m['Engineering']
            d['engineering'] = {
                "blueprintName": e['BlueprintName'],
                "blueprintLevel": e['Level'],
                "blueprintQuality": e['Quality'],
                "modifiers": [
                    {
                        "name": mod['Label'],
                        "value": mod['Value'],
                        "originalValue": mod['OriginalValue'],
                        "lessIsGood": bool(mod['LessIsGood'])
                    }
                    for mod in e.get('Modifiers', [])
                    if {'Label', 'Value', 'OriginalValue', 'LessIsGood'}.issubset(set(mod.keys()))
                ]
            }
            if 'ExperimentalEffect' in e:
                d['engineering']['experimentalEffect'] = e['ExperimentalEffect']
        modules.append(d)

    return [
        InaraEvent(
            eventName='setCommanderShip',
            eventTimestamp=event.data['timestamp'],
            eventData={
                'shipType': event.data['Ship'],
                'shipGameID': event.data['ShipID'],
                'shipName': event.data['ShipName'],
                'shipIdent': event.data['ShipIdent'],
                'isCurrentShip': True,
                'shipHullValue': event.data['HullValue'],
                'shipModulesValue': event.data['ModulesValue'],
                'shipRebuyCost': event.data['Rebuy'],
            }
        ),
        InaraEvent(
            eventName='setCommanderShipLoadout',
            eventTimestamp=event.data['timestamp'],
            eventData={
                'shipType': event.data['Ship'],
                'shipGameID': event.data['ShipID'],
                'shipLoadout': modules
            }
        )
    ]


@processor_registry.register('MaterialCollected')
def on_material_collected_event(event: journal.Event) -> InaraEvent:
    return InaraEvent(
        eventName='addCommanderInventoryMaterialsItem',
        eventTimestamp=event.data['timestamp'],
        eventData={
            'itemName': event.data['Name'],
            'itemCount': event.data['Count']
        }
    )


@processor_registry.register('MaterialDiscarded')
def on_material_discarded_event(event: journal.Event) -> InaraEvent:
    return InaraEvent(
        eventName='delCommanderInventoryMaterialsItem',
        eventTimestamp=event.data['timestamp'],
        eventData={
            'itemName': event.data['Name'],
            'itemCount': event.data['Count']
        }
    )


@processor_registry.register('EngineerCraft')
def on_engineer_craft_event(event: journal.Event) -> List[InaraEvent]:
    return [
        InaraEvent(
            eventName='delCommanderInventoryMaterialsItem',
            eventTimestamp=event.data['timestamp'],
            eventData={
                'itemName': material['Name'],
                'itemCount': material['Count']
            }
        )
        for material in event.data.get('Ingredients', [])
        if has_keys(material, 'Name', 'Count')
    ]


@processor_registry.register('MaterialTrade')
def on_material_trade_event(event: journal.Event) -> List[InaraEvent]:
    return [
        InaraEvent(
            eventName='delCommanderInventoryMaterialsItem',
            eventTimestamp=event.data['timestamp'],
            eventData={
                'itemName': event.data['Paid']['Material'],
                'itemCount': event.data['Paid']['Quantity']
            }
        ),
        InaraEvent(
            eventName='addCommanderInventoryMaterialsItem',
            eventTimestamp=event.data['timestamp'],
            eventData={
                'itemName': event.data['Received']['Material'],
                'itemCount': event.data['Received']['Quantity']
            }
        )
    ]


@processor_registry.register('MissionCompleted')
def on_mission_complete_event(event: journal.Event) -> List[InaraEvent]:
    return [
        InaraEvent(
            eventName='addCommanderInventoryMaterialsItem',
            eventTimestamp=event.data['timestamp'],
            eventData={
                'itemName': material['Name'],
                'itemCount': material['Count']
            }
        )
        for material in event.data.get('MaterialsReward', [])
        if has_keys(material, 'Name', 'Count')
    ]


@processor_registry.register('Synthesis')
def on_synthesis_event(event: journal.Event) -> List[InaraEvent]:
    return [
        InaraEvent(
            eventName='delCommanderInventoryMaterialsItem',
            eventTimestamp=event.data['timestamp'],
            eventData={
                'itemName': material['Name'],
                'itemCount': material['Count']
            }
        )
        for material in event.data.get('Materials', [])
        if has_keys(material, 'Name', 'Count')
    ]
