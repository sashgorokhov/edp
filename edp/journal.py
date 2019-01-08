import datetime
import json
import logging
import os
import pathlib
import queue
import threading
from typing import NamedTuple, Optional, List

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


class JournalReader:
    def __init__(self, base_dir: pathlib.Path):
        self._base_dir = base_dir
        self._latest_file_mtime = None
        self._latest_file_events: List['Event'] = []
        self._latest_file = None
        self._lock = threading.Lock()

    def get_latest_file(self) -> Optional[pathlib.Path]:
        files_list = sorted(self._base_dir.glob('Journal.*.log'), key=lambda path: os.path.getmtime(path))
        return files_list[-1] if len(files_list) else None

    def get_latest_file_events(self) -> List['Event']:
        latest_file = self.get_latest_file()
        latest_file_mtime = os.path.getmtime(latest_file)

        if latest_file is None:
            return []

        if latest_file != self._latest_file or latest_file_mtime != self._latest_file_mtime:
            with self._lock:
                self._latest_file = latest_file
                self._latest_file_mtime = latest_file_mtime
                self._latest_file_events = []

                with open(self._latest_file, 'r') as f:
                    for line in f.readlines():
                        try:
                            event = process_event(line)
                        except:
                            logger.exception('Failed to process event: %s', event)
                            continue

                        self._latest_file_events.append(event)

        return self._latest_file_events


class JournalLiveEventThread(StoppableThread):
    interval = 1

    def __init__(self, journal_reader: JournalReader, plugin_manager: PluginManager):
        super(JournalLiveEventThread, self).__init__()

        self._journal_reader = journal_reader
        self._plugin_manager = plugin_manager

    def run(self):
        current_file: pathlib.Path = None
        last_pos = 0

        while not self.is_stopped:
            latest_file = self._journal_reader.get_latest_file()

            if not latest_file:
                logger.debug('No journal files found')
                self.sleep(self.interval)
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

            self.sleep(self.interval)

    def read_file(self, filename: pathlib.Path, pos: int = 0) -> int:
        num_events = 0

        with open(filename, 'r') as f:
            f.seek(pos, os.SEEK_SET)

            for num_events, line in enumerate(f.readlines()):
                self.process_line(line)

            logger.debug('Read %s events', num_events)

            return f.tell()

    def process_line(self, line: str):
        try:
            processed_event = process_event(line)
        except:
            logger.exception('Failed to process event: %s', line)
            return

        self._plugin_manager.emit(signals.JOURNAL_EVENT, event=processed_event)


class Event(NamedTuple):
    timestamp: datetime.datetime
    name: str
    data: dict
    raw: str


def process_event(event_line: str) -> Event:
    event = json.loads(event_line)

    if 'timestamp' not in event:
        raise ValueError('Invalid event dict: missing timestamp field')
    if 'event' not in event:
        raise ValueError('Invalid event dict: missing event field')

    timestamp_str = event.pop('timestamp').rstrip('Z')
    timestamp = datetime.datetime.fromisoformat(timestamp_str)

    name = event.pop('event')

    return Event(timestamp, name, event, event_line)
