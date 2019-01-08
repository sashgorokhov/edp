import datetime
import logging
import os
import pathlib
import queue
import time
import json
from typing import NamedTuple, IO, Optional, Iterator

from edp import signals
from edp.plugin import PluginManager
from edp.utils import StoppableThread

logger = logging.getLogger(__name__)


class ReaderThreadArgs(NamedTuple):
    base_dir: pathlib.Path
    event_queue: queue.Queue


def get_file_end_pos(filename) -> int:
    with open(filename, 'r') as f:
        f.seek(0, os.SEEK_END)
        return f.tell()


class Journal(StoppableThread):
    interval = 1

    def __init__(self, base_dir: pathlib.Path):
        self._base_dir = base_dir
        self._event_queue = queue.Queue()
        super(Journal, self).__init__()

    def get_latest_file(self) -> Optional[pathlib.Path]:
        files_list = sorted(self._base_dir.glob('Journal.*.log'), key=lambda path: os.path.getmtime(path))
        return files_list[-1] if len(files_list) else None

    def run(self):
        current_file: pathlib.Path = None
        last_pos = 0

        while not self.is_stopped:
            latest_file = self.get_latest_file()

            if not latest_file:
                logger.debug('No journal files found')
                time.sleep(self.interval)
                continue

            if latest_file != current_file:
                logger.debug('Changing current journal to %s', latest_file.name)

                if current_file is None:  # we starting up, need to skip old entries
                    logger.debug('Startup skipping existing journal content')
                    last_pos = get_file_end_pos(latest_file)
                else:
                    last_pos = 0

                current_file = latest_file

            last_pos = self.read_file(current_file, last_pos)

            time.sleep(self.interval)

    def read_file(self, filename: pathlib.Path, pos: int = 0) -> int:
        num_events = 0

        with open(filename, 'r') as f:
            f.seek(pos, os.SEEK_SET)
            for num_events, line in enumerate(f.readlines()):
                try:
                    event = json.loads(line)
                except:
                    logger.exception('Failed to parse journal line from file %s: %s', filename.name, line)
                    continue

                self._event_queue.put_nowait(event)

            logger.debug('Read %s events', num_events)

            return f.tell()

    def __iter__(self) -> Iterator[dict]:
        while True:
            yield self.get_last_event()

    def get_last_event(self, block=True, timeout=None) -> dict:
        return self._event_queue.get(block=block, timeout=timeout)


class Event(NamedTuple):
    timestamp: datetime.datetime
    name: str
    data: dict


def process_event(event: dict) -> Event:
    if 'timestamp' not in event:
        raise ValueError('Invalid event dict: missing timestamp field')
    if 'event' not in event:
        raise ValueError('Invalid event dict: missing event field')

    timestamp_str = event.pop('timestamp').rstrip('Z')
    timestamp = datetime.datetime.fromisoformat(timestamp_str)

    name = event.pop('event')

    return Event(timestamp, name, event)


class JournalEventProcessor(StoppableThread):
    def __init__(self, journal: Journal, plugin_manager: PluginManager):
        self._journal = journal
        self._plugin_manager = plugin_manager
        super(JournalEventProcessor, self).__init__()

    def run(self):
        while not self._journal.is_stopped and not self.is_stopped:
            try:
                event = self._journal.get_last_event(block=True, timeout=1)
                try:
                    processed_event = process_event(event)
                except:
                    logger.exception('Failed to process event: %s', event)
                    continue
                self._plugin_manager.emit(signals.JOURNAL_EVENT, event=processed_event)
            except queue.Empty:
                continue


if __name__ == '__main__':
    from utils import winpaths
    logging.basicConfig(level=logging.DEBUG)

    ed_journal_path = winpaths.get_known_folder_path(winpaths.KNOWN_FOLDERS.SavedGames, user_handle=winpaths.UserHandle.current) / 'Frontier Developments' / 'Elite Dangerous'

    with Journal(ed_journal_path) as journal:
        for event in journal:
            print(event)
