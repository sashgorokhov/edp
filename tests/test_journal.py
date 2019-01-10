import datetime
import json
import pathlib
import tempfile
import time
from typing import List, Union, Dict

import pytest

from edp import journal


def format_dt(dt: datetime.datetime) -> str:
    return datetime.datetime.now().isoformat(timespec='seconds') + 'Z'


def serialize_event(event: Union[Dict, str]) -> str:
    if isinstance(event, str):
        return event
    return json.dumps(event)


def serialize_events(events: List[dict]) -> str:
    return '\n'.join(map(serialize_event, events))


@pytest.fixture()
def tempdir():
    with tempfile.TemporaryDirectory() as tempdir:
        yield pathlib.Path(tempdir)


@pytest.fixture()
def journal_reader(tempdir):
    return journal.JournalReader(tempdir)


def test_get_latest_file(tempdir, journal_reader):
    filename1 = 'Journal.foo.log'

    (tempdir / filename1).write_text('foo')

    assert journal_reader.get_latest_file().name == filename1


def test_get_latest_file_no_files(journal_reader):
    assert journal_reader.get_latest_file() is None


def test_get_latest_file_two_files(tempdir, journal_reader):
    filename1 = 'Journal.foo.log'
    filename2 = 'Journal.foo.log'

    (tempdir / filename1).write_text('foo')
    (tempdir / filename2).write_text('bar')

    assert journal_reader.get_latest_file().name == filename2


def test_get_latest_file_two_files_not_journal(tempdir, journal_reader):
    filename1 = 'Journal.foo.log'
    filename2 = 'foo.log'

    (tempdir / filename1).write_text('foo')
    (tempdir / filename2).write_text('bar')

    assert journal_reader.get_latest_file().name == filename1


def test_get_latest_file_events(tempdir, journal_reader):
    dt = datetime.datetime.now().replace(microsecond=0)

    events = [
        {'timestamp': format_dt(dt), 'event': 'test'}
    ]

    (tempdir / 'Journal.test.log').write_text(serialize_events(events))

    events_list = journal_reader.get_latest_file_events()

    assert len(events_list) == len(events)

    assert events_list[0].name == 'test'
    assert events_list[0].timestamp == dt


def test_get_latest_file_events_bad_event(tempdir, journal_reader):
    dt = datetime.datetime.now().replace(microsecond=0)

    events = [
        {'timestamp': format_dt(dt), 'event': 'test'},
        'invalid event here',
        {'timestamp': format_dt(dt)},
        {'event': 'test'},
    ]

    (tempdir / 'Journal.test.log').write_text(serialize_events(events))

    events_list = journal_reader.get_latest_file_events()

    assert len(events_list) == 1

    assert events_list[0].name == 'test'
    assert events_list[0].timestamp == dt


def test_get_latest_file_events_append(tempdir, journal_reader):
    events = [
        {'timestamp': format_dt(datetime.datetime.now()), 'event': 'test 1'}
    ]

    (tempdir / 'Journal.test.log').write_text(serialize_events(events))

    events_list = journal_reader.get_latest_file_events()

    assert len(events_list) == 1
    assert events_list[0].name == 'test 1'

    time.sleep(0.5)

    with (tempdir / 'Journal.test.log').open(mode='a') as f:
        f.write('\n' + serialize_event({'timestamp': format_dt(datetime.datetime.now()), 'event': 'test 2'}))

    events_list = journal_reader.get_latest_file_events()

    assert len(events_list) == 2
    assert events_list[0].name == 'test 1'
    assert events_list[1].name == 'test 2'
