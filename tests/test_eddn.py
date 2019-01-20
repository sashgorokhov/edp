import datetime
from unittest import mock

import pytest

from edp import journal
from edp.contrib import eddn


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


def test_process_buffered_events(eddn_plugin):
    event = journal.Event(datetime.datetime.now(), 'FSDJump', {
        'event': 'FSDJump',
        'StarSystem': 'test',
        'SystemAddress': 1,
        'StarPos': [0.0, 0.0, 0.0],
        'Body': 'test',
        'FuelUsed': 1.0,
        'JumpDist': 124.0,
        'SystemFaction': 'test',
        'SystemAllegiance': 'test',
        'SystemEconomy': 'test',
        'Factions': [
            {'Name': 'test'},
            {'Name': 'test2', 'FactionState': 'None', 'Government': 'test', 'Influence': 'test'},
            {'Name': 'test3', 'FactionState': 'None', 'Government': 'test', 'Influence': 'test', 'Allegiance': 'test'}
        ]
    }, '{}')

    with mock.patch('inject.instance'):
        eddn_plugin.process_buffered_events([event])

    eddn_plugin._session.post.assert_called_once()
    payload = eddn_plugin._session.post.call_args[1]['json']

    assert 'FuelUsed' not in payload['message']
    assert 'JumpDist' not in payload['message']
    assert 'SystemAllegiance' in payload['message']
    assert 'Factions' in payload['message']
    assert len(payload['message']['Factions']) == 3
