import datetime
import json
import logging
import os
import threading
from pathlib import Path
from typing import NamedTuple, Optional, List, Dict, Any, Iterator

from edp.signalslib import Signal
from edp.thread import StoppableThread

logger = logging.getLogger(__name__)


class Event(NamedTuple):
    # TODO: Add generic way to convert to/from datetime and timestamp str
    timestamp: datetime.datetime
    name: str
    data: Dict[str, Any]  # TODO: Make immutable
    raw: str


journal_event_signal = Signal('journal event', event=Event)


def get_file_end_pos(filename) -> int:
    with open(filename, 'r') as f:
        f.seek(0, os.SEEK_END)
        return f.tell()


def process_event(event_line: str) -> Event:
    event = json.loads(event_line)

    if 'timestamp' not in event:
        raise ValueError('Invalid event dict: missing timestamp field')
    if 'event' not in event:
        raise ValueError('Invalid event dict: missing event field')

    timestamp_str = event['timestamp'].rstrip('Z')
    timestamp = datetime.datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')

    name: str = event['event']

    return Event(timestamp, name, event, event_line)


class JournalReader:
    def __init__(self, base_dir: Path):
        self._base_dir = base_dir
        self._latest_file_mtime: Optional[float] = None
        self._latest_file_events: List['Event'] = []
        self._latest_file: Optional[Path] = None
        self._lock = threading.Lock()

    def get_latest_file(self) -> Optional[Path]:
        files_list = sorted(self._base_dir.glob('Journal.*.log'), key=lambda path: os.path.getmtime(path))
        return files_list[-1] if len(files_list) else None

    @staticmethod
    def read_all_file_events(path: Path) -> Iterator['Event']:
        try:
            # noinspection PyTypeChecker
            with open(path, 'r', encoding='utf-8') as f:
                for line in f.readlines():
                    try:
                        yield process_event(line)
                    except:
                        logger.exception('Failed to process event: %s', line)
                        continue
        except:
            logger.exception('Failed to read events from file %s', path)

    def get_latest_file_events(self) -> List['Event']:
        latest_file = self.get_latest_file()

        if latest_file is None:
            return []

        with self._lock:
            latest_file_mtime = os.path.getmtime(latest_file)

            if latest_file != self._latest_file or latest_file_mtime != self._latest_file_mtime:
                self._latest_file = latest_file
                self._latest_file_mtime = latest_file_mtime
                self._latest_file_events = list(self.read_all_file_events(self._latest_file))

        return self._latest_file_events


class JournalLiveEventThread(StoppableThread):
    interval = 1

    def __init__(self, journal_reader: JournalReader):
        super(JournalLiveEventThread, self).__init__()

        self._journal_reader = journal_reader

    def run(self):
        current_file: Path = None
        last_file: Path = self._journal_reader.get_latest_file()
        last_pos = 0

        while not self.is_stopped:
            latest_file = self._journal_reader.get_latest_file()

            if not latest_file:
                logger.debug('No journal files found')
                self.sleep(self.interval)
                continue

            if latest_file != current_file:
                logger.debug('Changing current journal to %s', latest_file.name)

                if current_file is None and last_file is not None:
                    logger.debug('Startup skipping existing journal content')
                    last_pos = get_file_end_pos(latest_file)
                else:
                    last_pos = 0

                current_file = latest_file

            last_pos = self.read_file(current_file, last_pos)
            last_file = latest_file

            self.sleep(self.interval)

    def read_file(self, filename: Path, pos: int = 0) -> int:
        num_events = 0

        # noinspection PyTypeChecker
        with open(filename, 'r', encoding='utf-8') as f:
            f.seek(pos, os.SEEK_SET)

            for num_events, line in enumerate(f.readlines()):
                self.process_line(line)

            if num_events:
                logger.debug('Read %s events', num_events)

            return f.tell()

    def process_line(self, line: str):
        try:
            processed_event = process_event(line)
        except:
            logger.exception('Failed to process event: %s', line)
            return

        journal_event_signal.emit(event=processed_event)
