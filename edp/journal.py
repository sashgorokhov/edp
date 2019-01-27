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


class VersionInfo(NamedTuple):
    version: str
    build: str


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
        self._file_event_timestamp: Dict[str, datetime.datetime] = {}

    def get_latest_file(self) -> Optional[Path]:
        files_list = sorted(self._base_dir.glob('Journal.*.log'), key=lambda path: os.path.getmtime(path))
        return files_list[-1] if len(files_list) else None

    @staticmethod
    def read_all_file_events(path: Path) -> Iterator['Event']:
        try:
            # noinspection PyTypeChecker
            with path.open('r', encoding='utf-8') as f:
                for line in f.readlines():
                    try:
                        yield process_event(line)
                    except:
                        logger.exception('Failed to process event: %s', line)
                        continue
        except:
            logger.exception('Failed to read events from file %s', path)

    def get_latest_file_events(self) -> List[Event]:
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

    def _get_file_event(self, path: Path) -> Optional[Event]:
        if not path.exists():
            return None

        with path.open('r', encoding='utf-8') as f:
            try:
                event_line = f.read().strip()
                return process_event(event_line)
            except json.decoder.JSONDecodeError:
                logger.debug(f'JSONDecodeError while reading {path.name}')
            except:
                logger.exception(f'Failed to read status from {path}')

        return None

    def _filter_file_event(self, event: Event) -> Optional[Event]:
        if event.name not in self._file_event_timestamp:
            self._file_event_timestamp[event.name] = event.timestamp
            return None

        if event.timestamp > self._file_event_timestamp[event.name]:
            self._file_event_timestamp[event.name] = event.timestamp
            return event

        return None

    def _get_file_event_filtered(self, path: Path) -> Optional[Event]:
        event = self._get_file_event(path)
        if event:
            event = self._filter_file_event(event)
        return event

    def get_status_file_event(self) -> Optional[Event]:
        return self._get_file_event_filtered(self._base_dir / 'Status.json')

    def get_cargo_file_event(self) -> Optional[Event]:
        return self._get_file_event_filtered(self._base_dir / 'Cargo.json')

    def get_market_file_event(self) -> Optional[Event]:
        return self._get_file_event_filtered(self._base_dir / 'Market.json')

    def get_modules_info_file_event(self) -> Optional[Event]:
        return self._get_file_event_filtered(self._base_dir / 'ModulesInfo.json')

    def get_outfitting_file_event(self) -> Optional[Event]:
        return self._get_file_event_filtered(self._base_dir / 'Outfitting.json')

    def get_game_version_info(self) -> Optional[VersionInfo]:
        events = self.get_latest_file_events()
        for event in events:
            if event.name == 'Fileheader':
                gameversion = event.data.get('gameversion', 'unknown')
                build = event.data.get('build', 'unkown')
                return VersionInfo(gameversion, build)
        return None


class JournalLiveEventThread(StoppableThread):
    interval = 1

    def __init__(self, journal_reader: JournalReader):
        super(JournalLiveEventThread, self).__init__()

        self._journal_reader = journal_reader

        self._current_file: Optional[Path] = None
        self._last_file: Optional[Path] = None
        self._last_pos = 0

    def run(self):
        self._last_file = self._journal_reader.get_latest_file()

        while not self.is_stopped:
            try:
                self.read_journal()
                self.read_status_files()
            except:
                logger.exception('Error reading journal')
            finally:
                self.sleep(self.interval)

    def read_status_files(self):
        events: List[Optional[Event]] = [
            self._journal_reader.get_status_file_event(),
            self._journal_reader.get_cargo_file_event(),
            self._journal_reader.get_market_file_event(),
            self._journal_reader.get_modules_info_file_event(),
            self._journal_reader.get_outfitting_file_event()
        ]
        for event in filter(None, events):
            journal_event_signal.emit(event=event)

    def read_journal(self):
        latest_file = self._journal_reader.get_latest_file()

        if not latest_file:
            logger.debug('No journal files found')
            return

        if latest_file != self._current_file:
            logger.debug('Changing current journal to %s', latest_file.name)

            if self._current_file is None and self._last_file is not None:
                logger.debug('Startup skipping existing journal content')
                self._last_pos = get_file_end_pos(latest_file)
            else:
                self._last_pos = 0

            self._current_file = latest_file

        self._last_pos = self.read_file(self._current_file, self._last_pos)
        self._last_file = latest_file

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
