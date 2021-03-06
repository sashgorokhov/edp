import datetime
import json
from unittest import mock

import pytest
import requests

from edp import plugins, journal, utils
from edp.contrib import edsm, gamestate
from edp.utils import hypothesis_strategies


def test_edsm_settings_fields_defaults():
    s = edsm.EDSMSettings.get_insance()

    assert s.api_key is None
    assert s.commander_name is None


@pytest.fixture()
def edsm_api():
    with mock.patch('requests.Session'):
        yield edsm.EDSMApi('test_api_key', 'test_commander_name')


def test_api_discarded_events(edsm_api):
    edsm_api.discarded_events()
    args, kwargs = edsm_api._session.get.call_args
    assert len(args[0])
    assert 'timeout' in kwargs and kwargs['timeout'] == edsm_api.timeout


@pytest.mark.parametrize('events', [
    [],
    ['foo'],
    ['foo', 'bar']
])
@pytest.mark.parametrize('status_code', [200, 300, 400, 500])
def test_journal_event(edsm_api, events, status_code):
    response_mock = mock.MagicMock()
    response_mock.status_code = status_code
    edsm_api._session.post.return_value = response_mock
    edsm_api.journal_event(*events)
    args, kwargs = edsm_api._session.post.call_args

    assert 'json' in kwargs
    data = kwargs['json']
    assert data['commanderName'] == edsm_api._commander_name
    assert data['apiKey'] == edsm_api._api_key
    assert data['message'] == tuple(events)


def test_get_system(edsm_api):
    edsm_api.get_system('test')
    assert 'timeout' in edsm_api._session.post.call_args[1]
    assert 'json' in edsm_api._session.post.call_args[1]
    assert edsm_api._session.post.call_args[1]['json']['systemName'] == 'test'
    assert edsm_api._session.post.call_args[1]['json']['showId'] == 1


@pytest.fixture()
def plugin(atexit_clear, tempdir):
    return edsm.EDSMPlugin()


@pytest.mark.parametrize(('api_key', 'commander_name', 'enabled'), [
    (None, None, False),
    (None, '1', False),
    ('1', None, False),
    ('1', '1', True),
])
def test_plugin_enabled(plugin, api_key, commander_name, enabled):
    plugin.settings.api_key = api_key
    plugin.settings.commander_name = commander_name

    assert plugin.is_enalbed() == enabled


def test_on_game_state_set_bind(plugin):
    marks = plugins.get_function_marks(plugin.on_game_state_set)
    assert len(marks) == 1
    assert marks[0].name == plugins.MARKS.SIGNAL
    assert marks[0].options['signals'] == (edsm.game_state_set_signal,)


def test_on_game_state_set_sets_commander_name_setting(plugin):
    state = gamestate.GameStateData.get_clear_data()
    state.commander.name = 'test'

    assert plugin.settings.commander_name is None
    plugin.on_game_state_set(state)
    assert plugin.settings.commander_name == 'test'


def test_on_game_state_set_sets_commander_name_setting_already_set(plugin):
    state = gamestate.GameStateData.get_clear_data()
    state.commander.name = 'test'
    plugin.settings.commander_name = 'foo'

    plugin.on_game_state_set(state)
    assert plugin.settings.commander_name == 'foo'


@pytest.fixture()
def mock_api():
    mock_object = mock.MagicMock()
    with mock.patch('edp.contrib.edsm.EDSMApi') as mock_class:
        mock_class.from_settings.return_value = mock_object
        yield mock_object


@pytest.mark.parametrize(('discarded_events', 'event_name', 'is_discarded'), [
    ([], 'foo', False),
    (['foo'], 'foo', True)
])
def test_journal_event_discarded(discarded_events, event_name, is_discarded, plugin, mock_api):
    event = journal.Event(datetime.datetime.now(), event_name, {}, '')
    mock_api.discarded_events.return_value = discarded_events
    plugin.on_journal_event(event)

    if is_discarded:
        assert len(plugin._events_buffer) == 0
    else:
        assert len(plugin._events_buffer) == 1


def test_push_events_empty_buffer(mock_api, plugin):
    plugin.process_buffered_events([])
    mock_api.journal_event.assert_not_called()


@pytest.mark.parametrize('event_str', [
    '{"timestamp": "2018-06-07T08:09:10Z", "event": "test"}',
    '{"timestamp": "2018-06-07T08:09:10Z"}',
    '{"event": "test"}',
    '{}',
    '{"foo": "bar"}',
])
def test_patch_event(plugin, event_str):
    state = gamestate.GameStateData.get_clear_data()
    state.location.address = 'test_address'
    state.location.system = 'test_system'
    state.location.pos = (0.0, 0.0, 0.0)
    state.location.station.market = 'test_market'
    state.location.station.name = 'test_name'
    state.ship.id = 1

    existed_event_data = json.loads(event_str)
    patched_event_data = plugin.patch_event(event_str, state)

    assert utils.is_dict_subset(patched_event_data, existed_event_data)
    assert {'_systemAddress', '_systemName', '_systemCoordinates', '_marketId', '_stationName', '_shipId'} \
        .issubset(set(patched_event_data.keys()))


@pytest.fixture()
def state():
    state = gamestate.GameStateData.get_clear_data()
    state.location.address = 'test_address'
    state.location.system = 'test_system'
    state.location.pos = (0.0, 0.0, 0.0)
    state.location.station.market = 'test_market'
    state.location.station.name = 'test_name'
    state.ship.id = 1

    return state


def test_push_events_event_patched_with_state(mock_api, plugin, state):
    events = [
        journal.Event(datetime.datetime.now(), 'test1', {}, '{}'),
        journal.Event(datetime.datetime.now(), 'test2', {'foo': 'bar'}, '{"foo": "bar"}'),
        journal.Event(datetime.datetime.now(), 'test3', {'event': 'test3'}, '{"event": "test3"}'),
    ]

    plugin.gamestate = mock.Mock()
    plugin.gamestate.state = state

    plugin.process_buffered_events(events)

    mock_api.journal_event.assert_called_once()
    patched_events = mock_api.journal_event.call_args[0]
    assert len(patched_events) == len(events)

    for patched_event in patched_events:
        assert {'_systemAddress', '_systemName', '_systemCoordinates', '_marketId', '_stationName', '_shipId'} \
            .issubset(set(patched_event.keys()))


def test_process_buffered_events_retry_on_connection_error(mock_api, plugin, state):
    events = [
        hypothesis_strategies.TestEvent().example()
    ]

    plugin.gamestate = mock.Mock()
    plugin.gamestate.state = state
    mock_api.journal_event.side_effect = requests.exceptions.ConnectionError

    plugin.process_buffered_events(events)

    assert mock_api.journal_event.call_count == 2


def test_process_buffered_events_chunked(mock_api, plugin, state):
    event_strategy = hypothesis_strategies.TestEvent()
    events = list(event_strategy.example() for i in range(50))
    plugin.gamestate = mock.Mock()
    plugin.gamestate.state = state

    plugin.process_buffered_events(events)

    assert mock_api.journal_event.call_count == 5
