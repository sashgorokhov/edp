import datetime
from unittest import mock

import pytest

from edp import journal
from edp.contrib import gamestate


@pytest.fixture()
def plugin() -> gamestate.GameState:
    return gamestate.GameState()


def test_update_state_mutation_not_registered(plugin):
    event = journal.Event(datetime.datetime.now(), 'test', {}, '{}')
    assert not plugin.update_state(event)


def test_update_state_mutation_run(plugin):
    event = journal.Event(datetime.datetime.now(), 'test', {}, '{}')

    mutation = mock.MagicMock()
    with mock.patch.dict(gamestate.mutation_registry._callbacks, {'test': [mutation]}):
        plugin.update_state(event)

    mutation.assert_called_once_with(event=event, state=plugin._state)


def test_update_state_mutation_run_error(plugin):
    event = journal.Event(datetime.datetime.now(), 'test', {}, '{}')

    mutation = mock.MagicMock()
    mutation.side_effect = ValueError

    with mock.patch.dict(gamestate.mutation_registry._callbacks, {'test': [mutation]}):
        plugin.update_state(event)

    mutation.assert_called_once_with(event=event, state=plugin._state)


def test_set_initial_state(plugin):
    dt = datetime.datetime.now()
    events = [
        journal.Event(dt, 'test1', {}, '{}'),
        journal.Event(dt, 'test2', {}, '{}'),
        journal.Event(dt, 'test3', {}, '{}'),
    ]
    reader_mock = mock.MagicMock()
    reader_mock.get_latest_file_events.return_value = events
    plugin.journal_reader = reader_mock

    mutation1 = mock.MagicMock()
    mutation2 = mock.MagicMock()
    mutation3 = mock.MagicMock()

    with mock.patch.dict(gamestate.mutation_registry._callbacks,
                         {'test1': [mutation1], 'test2': [mutation2], 'test3': [mutation3]}):
        with mock.patch('edp.contrib.gamestate.game_state_set_signal') as signal_mock:
            plugin.set_initial_state()

    signal_mock.emit.assert_called_once()

    mutation1.assert_called_once()
    mutation2.assert_called_once()
    mutation3.assert_called_once()


def test_on_journal_event_changed_state(plugin):
    event = journal.Event(datetime.datetime.now(), 'test', {}, '{}')

    def mutation(event, state: gamestate.GameStateData):
        state.commander.name = 'test'

    with mock.patch.dict(gamestate.mutation_registry._callbacks, {'test': [mutation]}):
        with mock.patch('edp.contrib.gamestate.game_state_changed_signal') as signal_mock:
            plugin.on_journal_event(event)

    signal_mock.emit.assert_called_once()


def test_on_journal_event_state_not_changed(plugin):
    event = journal.Event(datetime.datetime.now(), 'test', {}, '{}')

    with mock.patch('edp.contrib.gamestate.game_state_changed_signal') as signal_mock:
        plugin.on_journal_event(event)

    signal_mock.emit.assert_not_called()
