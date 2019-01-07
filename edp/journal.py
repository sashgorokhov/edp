import logging
import os
import pathlib
import queue
import threading
import time
import json
from typing import NamedTuple, IO, Optional, Iterator

logger = logging.getLogger(__name__)


class ReaderThreadArgs(NamedTuple):
    base_dir: pathlib.Path
    event_queue: queue.Queue


def get_file_end_pos(filename) -> int:
    with open(filename, 'r') as f:
        f.seek(0, os.SEEK_END)
        return f.tell()


class ReaderThread(threading.Thread):
    _args: ReaderThreadArgs = None

    interval = 1
    stop = False

    def get_latest_file(self) -> Optional[pathlib.Path]:
        files_list = sorted(self._args.base_dir.glob('Journal.*.log'), key=lambda path: os.path.getmtime(path))
        return files_list[-1] if len(files_list) else None

    def run(self):
        current_file: pathlib.Path = None
        last_pos = 0

        while not self.stop:
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

                self._args.event_queue.put_nowait(event)

            logger.debug('Read %s events', num_events)

            return f.tell()

    def start(self):
        self.stop = False
        super(ReaderThread, self).start()


class Journal:
    def __init__(self, dir: pathlib.Path):
        self._base_dir = dir
        self._event_queue = queue.Queue()

        self._reader_thread = ReaderThread(args=ReaderThreadArgs(self._base_dir, self._event_queue))

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self):
        self._reader_thread.stop = False
        self._reader_thread.start()

    def stop(self):
        self._reader_thread.stop = True

    def __iter__(self) -> Iterator[dict]:
        while True:
            yield self.get_last_event()

    def get_last_event(self, block=True, timeout=None) -> dict:
        return self._event_queue.get(block=block, timeout=timeout)


if __name__ == '__main__':
    from utils import winpaths
    logging.basicConfig(level=logging.DEBUG)

    ed_journal_path = winpaths.get_known_folder_path(winpaths.KNOWN_FOLDERS.SavedGames, user_handle=winpaths.UserHandle.current) / 'Frontier Developments' / 'Elite Dangerous'

    with Journal(ed_journal_path) as journal:
        for event in journal:
            print(event)
