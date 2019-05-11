import datetime
from unittest import mock

import pytest

from edp import journal
from edp.contrib import inara, gamestate


@pytest.fixture()
def inara_plugin():
    return inara.InaraPlugin()


@pytest.mark.parametrize(('api_key', 'enabled', 'result'), [
    ('', False, False),
    ('1', False, False),
    ('1', True, True),
    ('', True, False),
])
def test_is_enabled(api_key, enabled, result, inara_plugin):
    settings = inara.InaraSettings.get_insance()
    settings.api_key = api_key
    settings.enabled = enabled

    assert inara_plugin.is_enalbed() == result


@pytest.fixture(autouse=True)
def mock_callback(inara_plugin):
    callback = mock.MagicMock()

    with mock.patch.dict(inara.processor_registry._callbacks, {'test': [callback]}):
        yield callback


@pytest.fixture(autouse=True)
def mock_api():
    with mock.patch('edp.contrib.inara.InaraApi.send') as m:
        yield m


@pytest.fixture(autouse=True)
def mock_gamestate():
    state = gamestate.GameStateData()
    with mock.patch('edp.contrib.gamestate.get_gamestate', return_value=state):
        yield state


@pytest.fixture()
def event():
    return journal.Event(datetime.datetime.now(), 'test', {}, '{}')


def test_process_event_returns_none(inara_plugin, mock_callback, event):
    mock_callback.return_value = None
    assert list(inara_plugin.process_event(event)) == []


def test_process_event_returns_single_event(inara_plugin, mock_callback, event):
    inara_event = inara.InaraEvent('test', 'test', {})
    mock_callback.return_value = inara_event
    assert list(inara_plugin.process_event(event)) == [inara_event]
    mock_callback.assert_called_once_with(event=event)


def test_process_event_returns_multiple_evets(inara_plugin, mock_callback, event):
    inara_event = inara.InaraEvent('test', 'test', {})
    inara_event2 = inara.InaraEvent('test2', 'test2', {})
    mock_callback.return_value = [inara_event, inara_event2]
    assert list(inara_plugin.process_event(event)) == [inara_event, inara_event2]
    mock_callback.assert_called_once_with(event=event)


def test_process_buffered_events(inara_plugin, mock_api, mock_callback, event, mock_gamestate):
    inara_event = inara.InaraEvent('test', 'test', {})
    mock_callback.return_value = inara_event

    inara_plugin.process_buffered_events([event])
    mock_callback.assert_called_once_with(event=event)
    mock_api.assert_called_once_with(inara_event, commander_name=mock_gamestate.commander.name or 'unknown',
                                     frontier_id=mock_gamestate.commander.frontier_id or 'unknown')


def test_process_buffered_events_error_while_processing(inara_plugin, mock_api, mock_callback, event, mock_gamestate):
    mock_callback.side_effect = ValueError

    inara_plugin.process_buffered_events([event])
    mock_callback.assert_called_once_with(event=event)
    mock_api.assert_not_called()


def test_process_buffered_events_error_sending_api(inara_plugin, mock_api, mock_callback, event, mock_gamestate):
    inara_event = inara.InaraEvent('test', 'test', {})
    mock_callback.return_value = inara_event
    mock_api.side_effect = ValueError

    inara_plugin.process_buffered_events([event])

    mock_callback.assert_called_once_with(event=event)
    mock_api.assert_called_once()


@pytest.mark.parametrize(('delta', 'result'), [
    (datetime.timedelta(days=5), True),
    (datetime.timedelta(days=10), True),
    (datetime.timedelta(days=30), False),
    (datetime.timedelta(days=31), False),
])
def test_old_event_not_processed(delta, result, inara_plugin, event):
    event = event._replace(timestamp=datetime.datetime.now() - delta)
    assert inara_plugin.filter_event(event) == result
