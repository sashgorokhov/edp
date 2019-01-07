import json
import logging
import pathlib
import queue
import tempfile
import time
from typing import List

import pytest

from edp import journal


logger = logging.getLogger(__name__)


@pytest.fixture()
def journal_dir():
    with tempfile.TemporaryDirectory() as dirname:
        yield pathlib.Path(dirname)


def write_journal_file(events: List[dict], journal_dir: pathlib.Path, filename = None) -> pathlib.Path:
    timestamp = int(time.time())
    filename = filename or journal_dir / ('Journal.%s.log' % timestamp)
    with open(filename, 'a') as f:
        f.write('\n'.join(map(json.dumps, events)))
    logger.info('File written %s: %s', filename, events)
    return filename


@pytest.mark.xfail(reason='FIXME: if no files existed upon reader start and one is created, its content skipped')
def test_no_file_new_created(journal_dir):
    with journal.Journal(journal_dir) as j:
        j._reader_thread.interval = 0.1

        with pytest.raises(queue.Empty):
            j.get_last_event(block=False)

        events = [{'foo': 'bar'}]
        write_journal_file(events, journal_dir)
        time.sleep(1)
        assert j.get_last_event(block=True, timeout=1) == events[0]


def test_olny_new_event_read(journal_dir):
    filename = write_journal_file([{'foo': 'bar'}], journal_dir)

    with journal.Journal(journal_dir) as j:
        j._reader_thread.interval = 0.1
        time.sleep(1)

        events = [{'bar': 'foo'}]
        write_journal_file(events, journal_dir, filename)
        assert j.get_last_event(block=True, timeout=1) == events[0]


def test_new_file_switched(journal_dir):
    with journal.Journal(journal_dir) as j:
        j._reader_thread.interval = 0.1
        time.sleep(1)

        filename = write_journal_file([{'foo': 'bar'}], journal_dir)
        time.sleep(0.2)
        write_journal_file([{'foo': 'bar 2'}], journal_dir, filename)

        assert j.get_last_event(block=True, timeout=1) == {'foo': 'bar 2'}

        write_journal_file([{'foo': 'bar 3'}], journal_dir)

        assert j.get_last_event(block=True, timeout=1) == {'foo': 'bar 3'}
