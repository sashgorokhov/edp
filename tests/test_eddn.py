import datetime
from unittest import mock

import pytest
from hypothesis import given, strategies as st, example, settings

from edp import journal, utils
from edp.contrib import eddn, gamestate
from edp.utils.hypothesis_strategies import FSDJumpEvent, LocationEvent, random_keys_removed, hypothesis_parametrize


def test_eddn_schema_to_dict():
    schema = eddn.EDDNSchema(
        header=eddn.SchemaHeader(
            uploaderID='test'
        ),
        schemaRef='test schema ref',
        message=eddn.JournalMessageSchema(
            timestamp='test',
            event='test',
            StarSystem='test',
            StarPos=(1.0, 1.0, 1.0),
            SystemAddress=1,
            Factions=[],
            optional={
                'foo': 'bar'
            }
        )
    )

    d = schema.to_dict()

    assert 'schemaRef' not in d and '$schemaRef' in d
    assert 'optional' not in d['message']
    assert 'foo' in d['message']


@pytest.fixture()
def eddn_plugin():
    with mock.patch('requests.Session'):
        return eddn.EDDNPlugin()


def test_plugin_enabled(eddn_plugin):
    eddn_plugin.settings.enabled = False
    assert not eddn_plugin.is_enalbed()

    eddn_plugin.settings.enabled = True
    assert eddn_plugin.is_enalbed()


@pytest.mark.parametrize(('event_name', 'filtered'), [
    ('Docked', False),
    ('Scanned', True),
    ('FSDJump', False),
    ('Location', False),
])
def test_event_filtered(eddn_plugin, event_name, filtered):
    event = journal.Event(timestamp=datetime.datetime.now(), name=event_name, data={}, raw='{}')
    eddn_plugin.on_journal_event(event)
    if filtered:
        assert len(eddn_plugin._events_buffer) == 0
    else:
        assert len(eddn_plugin._events_buffer) == 1


@hypothesis_parametrize('event', FSDJumpEvent(), max_examples=5)
def test_process_buffered_events(eddn_plugin, event):
    with mock.patch('inject.instance'):
        eddn_plugin.process_buffered_events([event])

    eddn_plugin._session.post.assert_called()


@hypothesis_parametrize('event', st.one_of(
        random_keys_removed(FSDJumpEvent()) | FSDJumpEvent(),
        random_keys_removed(LocationEvent()) | LocationEvent()))
@pytest.mark.parametrize('commander_name', [None, 'foo'])
def test_process_event(eddn_plugin, event, commander_name):
    state = gamestate.GameStateData()
    state.commander.name = commander_name
    state.location.system = 'test'
    state.location.pos = [0.0, 0.0, 0.0]
    state.location.address = 1

    schema = eddn_plugin.process_event(event, state)
    assert schema.header.uploaderID is not None
    assert schema.schemaRef is not None
    assert isinstance(schema.message, eddn.JournalMessageSchema)
    assert schema.message.timestamp == utils.to_ed_timestamp(event.timestamp)
    assert schema.message.StarSystem
    assert schema.message.StarPos
    assert schema.message.SystemAddress
