import datetime
import json
import pathlib
import tempfile
import time
from typing import List, Union, Dict
from unittest import mock

import pytest

from edp import journal, signalslib
from edp.journal import Event

TEST_EVENT_1 = ('{"timestamp": "2018-06-07T08:09:10Z", "event": "test 1", "foo": "bar"}',
                Event(datetime.datetime(2018, 6, 7, 8, 9, 10), 'test 1',
                      {"timestamp": "2018-06-07T08:09:10Z", "event": 'test 1', 'foo': 'bar'},
                      '{"timestamp": "2018-06-07T08:09:10Z", "event": "test 1", "foo": "bar"}'
                      )
                )

TEST_EVENT_2 = ('{"timestamp": "2018-06-07T08:09:10Z", "event": "test 2", "foo": "bar"}',
                Event(datetime.datetime(2018, 6, 7, 8, 9, 10), 'test 2',
                      {"timestamp": "2018-06-07T08:09:10Z", "event": 'test 2', 'foo': 'bar'},
                      '{"timestamp": "2018-06-07T08:09:10Z", "event": "test 2", "foo": "bar"}'
                      )
                )

TEST_EVENT_3 = ('{"timestamp": "2018-06-07T08:09:10Z", "event": "test 3", "foo": "bar"}',
                Event(datetime.datetime(2018, 6, 7, 8, 9, 10), 'test 3',
                      {"timestamp": "2018-06-07T08:09:10Z", "event": 'test 3', 'foo': 'bar'},
                      '{"timestamp": "2018-06-07T08:09:10Z", "event": "test 3", "foo": "bar"}'
                      )
                )


def format_dt(dt: datetime.datetime) -> str:
    return datetime.datetime.now().isoformat(timespec='seconds') + 'Z'


def serialize_event(event: Union[Dict, str]) -> str:
    if isinstance(event, str):
        return event
    return json.dumps(event)


def serialize_events(events: List[dict]) -> str:
    return '\n'.join(map(serialize_event, events))


def append_line(path: pathlib.Path, line: str):
    with path.open('a') as f:
        f.write(line)


@pytest.fixture()
def journal_reader(tempdir):
    return journal.JournalReader(tempdir)


@pytest.fixture()
def journal_live_event_thread(journal_reader):
    thread = journal.JournalLiveEventThread(journal_reader)
    thread.interval = 0.1
    return thread


@pytest.fixture()
def journal_event_signal_mock():
    with mock.patch('edp.journal.journal_event_signal') as m:
        yield m


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


def test_get_latest_file_events_no_files(tempdir, journal_reader):
    events_list = journal_reader.get_latest_file_events()

    assert len(events_list) == 0


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


def test_process_event():
    event_line = '{"timestamp": "2018-06-07T08:09:10Z", "event": "test", "foo": "bar"}'
    event = journal.process_event(event_line)

    assert event.name == 'test'
    assert event.timestamp == datetime.datetime(2018, 6, 7, 8, 9, 10)

    assert event.raw == event_line
    assert 'foo' in event.data
    assert event.data['foo'] == 'bar'

    assert 'timestamp' in event.data
    assert 'event' in event.data


def test_process_event_bad_timestamp():
    event_line = '{"timestamp": "2018-06-07T25:09", "event": "test", "foo": "bar"}'

    with pytest.raises(ValueError):
        journal.process_event(event_line)


def test_process_event_no_timestamp():
    event_line = '{"event": "test", "foo": "bar"}'

    with pytest.raises(ValueError):
        journal.process_event(event_line)


def test_process_event_no_event():
    event_line = '{"timestamp": "2018-06-07T25:09", "foo": "bar"}'

    with pytest.raises(ValueError):
        journal.process_event(event_line)


def test_process_event_malformed_line():
    event_line = 'what is it?'

    with pytest.raises(ValueError):
        journal.process_event(event_line)


def test_journal_live_event_thread_no_files(journal_live_event_thread, journal_event_signal_mock):
    with journal_live_event_thread:
        time.sleep(0.5)

    journal_event_signal_mock.assert_not_called()


def test_journal_live_event_thread_file_appeared(journal_live_event_thread, tempdir, journal_event_signal_mock):
    event_line, event = TEST_EVENT_1

    with journal_live_event_thread:
        time.sleep(0.5)
        (tempdir / 'Journal.test.log').write_text(event_line)
        time.sleep(0.5)

    journal_event_signal_mock.emit.assert_called_once_with(event=event)


def test_journal_live_event_skip_existing_file_content(journal_live_event_thread, tempdir, journal_event_signal_mock):
    (tempdir / 'Journal.test.log').write_text(TEST_EVENT_1[0])

    with journal_live_event_thread:
        time.sleep(0.5)
        append_line(tempdir / 'Journal.test.log', TEST_EVENT_2[0])
        time.sleep(0.5)

    journal_event_signal_mock.emit.assert_called_once_with(event=TEST_EVENT_2[1])
