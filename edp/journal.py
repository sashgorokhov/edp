"""
Logic to work with ED journal files.

This defines core element of journal processing: Event.

Defined signals:
- journal_event_signal: Sent when new journal event is read and parsed
"""
import datetime
import json
import logging
import os
import threading
from pathlib import Path
from typing import NamedTuple, Optional, List, Dict, Any, Iterator

from edp.signalslib import Signal
from edp.thread import StoppableThread
from edp.utils import from_ed_timestamp

logger = logging.getLogger(__name__)


class Event(NamedTuple):
    """
    Defines an event that was read from journal
    """
    timestamp: datetime.datetime
    name: str
    data: Dict[str, Any]
    raw: str


class VersionInfo(NamedTuple):
    """Game version information"""
    version: str = 'unknown'
    build: str = 'unknown'


journal_event_signal = Signal('journal event', event=Event)


def get_file_end_pos(filename: str) -> int:
    """
    Get EOF offset
    """
    with open(filename, 'r') as f:
        f.seek(0, os.SEEK_END)
        return f.tell()


def process_event(event_line: str) -> Event:
    """
    Parse given event string into Event object

    :raise ValueError: if either timestamp or event fields are not present in event
    :raise json.JSONDecodeError: if unable to parse event string with json
    """
    event = json.loads(event_line)

    if 'timestamp' not in event:
        raise ValueError('Invalid event dict: missing timestamp field')
    if 'event' not in event:
        raise ValueError('Invalid event dict: missing event field')

    timestamp = from_ed_timestamp(event['timestamp'])

    name: str = event['event']

    return Event(timestamp, name, event, event_line)


class JournalReader:
    """
    Holds the logic to work with journal files.
    """
    def __init__(self, base_dir: Path):
        self._base_dir = base_dir
        self._latest_file_mtime: Optional[float] = None
        self._latest_file_events: List['Event'] = []
        self._latest_file: Optional[Path] = None
        self._lock = threading.Lock()
        self._file_event_timestamp: Dict[str, datetime.datetime] = {}

    def get_latest_file(self) -> Optional[Path]:
        """
        Return latest journal file path, by its modification time.

        Return None if nothing found.
        """
        files_list = sorted(self._base_dir.glob('Journal.*.log'), key=os.path.getmtime)
        return files_list[-1] if files_list else None

    @staticmethod
    def read_all_file_events(path: Path) -> Iterator['Event']:
        """
        Iterate over all events in a given journal file path.
        """
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
        """
        Return all events from latest journal file.

        Does some simple caching so it wont read and parse same unmodified file twice.
        """
        latest_file = self.get_latest_file()

        if latest_file is None:
            return []

        with self._lock:
            latest_file_mtime = os.path.getmtime(latest_file)

            if latest_file != self._latest_file or latest_file_mtime != self._latest_file_mtime:
                self._latest_file = latest_file
                self._latest_file_mtime = latest_file_mtime
                self._latest_file_events = list(self.read_all_file_events(self._latest_file))

        return self._latest_file_events.copy()

    def _get_file_event(self, path: Path) -> Optional[Event]:  # pylint: disable=no-self-use
        """
        Return single event from a single-event file like Status.json

        If path not exist, return None. If error happens, return None.
        All errors are suppressed and logged.
        Sometimes path may be empty, so JSONDecodeError just logged at DEBUG level.
        """
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
        """
        Filter event and return it only if it newer that previous.

        Used for single-event files like Status.json
        """
        if event.name not in self._file_event_timestamp:
            self._file_event_timestamp[event.name] = event.timestamp
            return None

        if event.timestamp > self._file_event_timestamp[event.name]:
            self._file_event_timestamp[event.name] = event.timestamp
            return event

        return None

    def _get_file_event_filtered(self, path: Path) -> Optional[Event]:
        """
        Return Event from single-event file, only if it newer than prevous.
        """
        event = self._get_file_event(path)
        if event:
            event = self._filter_file_event(event)
        return event

    def get_status_file_event(self) -> Optional[Event]:
        """
        Return Status.json file event
        """
        return self._get_file_event_filtered(self._base_dir / 'Status.json')

    def get_cargo_file_event(self) -> Optional[Event]:
        """
        Return Cargo.json file event
        """
        return self._get_file_event_filtered(self._base_dir / 'Cargo.json')

    def get_market_file_event(self) -> Optional[Event]:
        """
        Return Market.json file event
        """
        return self._get_file_event_filtered(self._base_dir / 'Market.json')

    def get_modules_info_file_event(self) -> Optional[Event]:
        """
        Return ModulesInfo.json file event
        """
        return self._get_file_event_filtered(self._base_dir / 'ModulesInfo.json')

    def get_outfitting_file_event(self) -> Optional[Event]:
        """
        Return Outfitting.json file event
        """
        return self._get_file_event_filtered(self._base_dir / 'Outfitting.json')

    def get_game_version_info(self) -> Optional[VersionInfo]:
        """
        Return VersionInfo from latest journal file.
        """
        events = self.get_latest_file_events()
        for event in events:
            if event.name == 'Fileheader':
                gameversion = event.data.get('gameversion', None) or 'unknown'
                build = event.data.get('build', None) or 'unknown'
                return VersionInfo(gameversion, build)
        return None


class JournalLiveEventThread(StoppableThread):
    """
    Read journal events in a thread
    """
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
        """
        Read all single-event files like Status.json and emit journal_event_signal on their events.
        """
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
        """
        Read journal.

        This will process only new events added to journal.
        Also handles new journal file creation.
        """
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
        """
        Read given journal file from position.

        Returns EOF offest.
        """
        num_events = 0

        # noinspection PyTypeChecker
        with open(filename, 'r', encoding='utf-8') as f:
            f.seek(pos, os.SEEK_SET)

            for num_events, line in enumerate(f.readlines()):
                self.process_line(line)

            if num_events:
                logger.debug('Read %s events', num_events)

            return f.tell()

    def process_line(self, line: str):  # pylint: disable=no-self-use
        """
        Parse journal line and emit journal_event_signal with its Event
        """
        try:
            processed_event = process_event(line)
        except:
            logger.exception('Failed to process event: %s', line)
            return

        journal_event_signal.emit(event=processed_event)
